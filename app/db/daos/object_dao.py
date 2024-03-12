from datetime import datetime
from io import BytesIO
from math import ceil

from PIL import Image
from bson.errors import InvalidId
from bson.objectid import ObjectId
from flask import abort
from pymongo import ASCENDING

from app import application
from app.db.daos.annotation_dao import AnnotationDAO
from app.db.daos.base import JoinableDAO, dao_update
from app.db.daos.label_dao import LabelDAO
from app.db.daos.user_dao import UserDAO
from app.db.models.object import DetectedObject
from app.db.models.payloads.object import ObjectPayload
from app.db.stats.daos.image_prios import PrioStatsDAO
from app.db.stats.daos.image_stats import ImageStatsDAO
from app.db.util import encode_as_base64


class ObjectDAO(JoinableDAO):
    __slots__ = '_feature_check_anno_id', '_feature_check_agg'
    bbox_alias_mapping = {"bboxTlx": "tlx", "bboxTly": "tly", "bboxBrx": "brx", "bboxBry": "bry"}

    def __init__(self):
        super().__init__("images", DetectedObject, ObjectPayload, "objects")
        self.references = {
            'annotations': AnnotationDAO,
            'labelId': ('label', LabelDAO, False),
            'createdBy': ('creator', UserDAO, False)
        }
        self.stat_references = ((ImageStatsDAO, PrioStatsDAO), None)

        self.create_index('obj_id_index', ('_id', ASCENDING))
        self.create_index('obj_label_index', ('labelId', ASCENDING))
        self.create_index('obj_creator_index', ('createdBy', ASCENDING))

        self._feature_check_anno_id = {'objects.annotations._id': None}
        self._feature_check_agg = [
            {"$unwind": "$objects"},
            {"$unwind": "$objects.annotations"},
            {'$match': self._feature_check_anno_id},
            {'$project':
                {
                    'objects.tlx': 1, 'objects.tly': 1, 'objects.brx': 1, 'objects.bry': 1,
                    'objects.annotations.conceptIds': 1, 'objects._id': 1,
                }
            },
        ]

    @staticmethod
    def retrieve_insert_args(json_args, label_projection=None):
        if label_projection is None:
            label_projection = '_id'
        if "docId" in json_args:
            try:
                doc_id = ObjectId(json_args["docId"])
            except InvalidId:
                err_msg = "The Image Document ID you provided is not a valid ID!"
                application.logger.error(err_msg)
                abort(404, err_msg)
        else:
            err_msg = 'You must provide a key-value pair with key "docId"!'
            application.logger.error(err_msg)
            abort(400, err_msg)
        if "label" in json_args:
            label = LabelDAO().find_dynamic(json_args["label"], projection=label_projection)
            if not label:
                raise ValueError(f'Label with the given information "{label}" could not be found!')
        elif "labelId" in json_args:
            try:
                label = LabelDAO().find_by_id(ObjectId(json_args["labelId"]), projection=label_projection)
                if label is None:
                    err_msg = "No label with the given ID could be found!"
                    application.logger.error(err_msg)
                    abort(404, err_msg)
            except InvalidId:
                err_msg = "The label ID you provided is not a valid ID!"
                application.logger.error(err_msg)
                abort(404, err_msg)
        elif "labelName" in json_args and (('category' in json_args) != ('categories' in json_args)):
            categories = json_args.get('category', json_args['categories'])
            label = LabelDAO().add(json_args["labelName"], categories)[1]
            if label is None:
                err_msg = 'Provide at least one basic category for the new label.'
                application.logger.error(err_msg)
                abort(400, err_msg)
        else:
            err_msg = ('You must provide a key-value pair with key "label" or "labelId" or'
                       ' add a new label by providing the "labelName" and "category" / "categories"!')
            application.logger.error(err_msg)
            abort(400, err_msg)
        if not ObjectDAO.bbox_alias_mapping.keys() <= json_args.keys():
            err_msg = ('Your request body must contain all key-value pairs for the bounding box definition with '
                       'keys "bboxTlx", "bboxTly", "bboxBrx" and "bboxBry"!')
            application.logger.error(err_msg)
            abort(400, err_msg)
        bbox = (ceil(json_args["bboxTlx"]), ceil(json_args["bboxTly"]),
                int(json_args["bboxBrx"]), int(json_args["bboxBry"]))
        if isinstance(label_projection, str):
            label = label[label_projection]
        elif len(label_projection) == 1:
            label = label[label_projection[0]]
        return doc_id, label, bbox

    @staticmethod
    def validate_object(obj, user_id=None, db_session=None):
        annos = obj.get("annotations", None)
        label_dao = LabelDAO()
        if 'label' in obj:
            label = label_dao.find_dynamic(obj['label'], projection='_id', db_session=db_session)
            if label is None:
                err_msg = f'Object data refers to a label with info "{obj["label"]}" that could not be found!'
                application.logger.error(err_msg)
                abort(404, err_msg)
            label_id = label['_id']
            del obj['label']
            obj['labelId'] = label_id
        else:
            label_id = obj['labelId'] = ObjectId(obj['labelId'])
        if annos:
            AnnotationDAO().prepare_annotations(annos, label_id, user_id, db_session=db_session)
        if user_id:
            obj['createdBy'] = user_id
        for key, new_key in ObjectDAO.bbox_alias_mapping.items():
            if key in obj:
                obj[new_key] = obj.pop(key)
        if '_id' not in obj:
            obj['_id'] = ObjectId()
        obj = DetectedObject(**obj)
        return obj

    @staticmethod
    def validate_objects(objs, user_id=None, db_session=None):
        for i, obj in enumerate(objs):
            objs[i] = ObjectDAO.validate_object(obj, user_id, db_session)
        return objs

    def prepare_feature_check(self, annotation_id):
        self._feature_check_anno_id['objects.annotations._id'] = annotation_id
        try:
            return next(self.collection.aggregate(self._feature_check_agg))['objects']
        except StopIteration:
            return None

    def _new_bbox_for_doc_is_unique(self, doc_id, bbox):
        # TODO: maybe even test whether both points of the bbox are more than x% away + same label
        new_bboxs = self.find_many(doc_id, projection=('tlx', "tly", "brx", "bry"))
        for new in new_bboxs:
            print(bbox)  # TODO: test (happens only when a second bbox is added)
            print(tuple(new.values()))
            if bbox == tuple(new.values()):
                raise ValueError(f'Duplicate Insert: A Bbox with the same coordinates {bbox} already exists!')

    @staticmethod
    def crop_img_to_obj(img, bbox, as_bytes=False):
        crop = Image.open(BytesIO(img)).crop(bbox)
        img_io = BytesIO()
        crop.save(img_io, format='JPEG')
        return img_io.getvalue() if as_bytes else img_io

    def find_all_object_imgs(self, doc_id, db_session=None):
        """
        Get all image crop of the `DetectedObject` with the given ID
        :param doc_id: Id of the image that we want all its object images of
        :param db_session:
        :return: The bytes of the cropped image
        """
        # TODO: Use base64 if not using file transfer? Or zip all images and transfer as 1 file (client needs to
        #  be able to decompress: possible in JS? Or multiplex multiple image requests, how?
        self._projection_dict['image'] = 1
        for coord in self.bbox_alias_mapping.values():
            self._projection_dict[self._loc_prefix + coord] = 1
        self._query_matcher["_id"] = doc_id
        result = self.collection.find_one(self._query_matcher, self._projection_dict, session=db_session)
        self._query_matcher.clear()
        self._projection_dict.clear()
        if result is None:
            return None
        img = result['image']
        bboxs = result[self.location]
        for i, bbox in enumerate(bboxs):
            bbox = tuple(bbox[coord] for coord in self.bbox_alias_mapping.values())
            bboxs[i] = encode_as_base64(self.crop_img_to_obj(img, bbox, as_bytes=True))
        return bboxs

    def find_object_img(self, obj_id, db_session=None):
        """
        Get the image crop of the `DetectedObject` with the given ID
        :param obj_id: Id of the object that we want the image of
        :param db_session:
        :return: The bytes of the cropped image
        """
        self._projection_dict['image'] = 1
        for coord in self.bbox_alias_mapping.values():
            self._projection_dict[self._loc_prefix + coord] = 1
        result = self.find_by_nested_id(obj_id, True, self._projection_dict, db_session=db_session)
        if result is None:
            return None
        img = result['image']
        bbox = result[self.location]
        bbox = tuple(bbox[coord] for coord in self.bbox_alias_mapping.values())
        return self.crop_img_to_obj(img, bbox)

    def find_by_creator(self, user_id, projection=None, generate_response=False, db_session=None):
        """
        Find `DetectedObject`s that were created by user with given Id
        :param user_id: Id of the annotator user
        :param projection:
        :param generate_response:
        :param db_session:
        :return: List of objects if found
        """
        return self.simple_match("createdBy", user_id, projection, generate_response, db_session)

    def find_by_annotator(self, user_id, projection=None, generate_response=False, db_session=None):
        """
        Find `DetectedObject`s that were annotated by the user with the given user Id
        :param user_id: Id of the annotator user
        :param projection:
        :param generate_response:
        :param db_session:
        :return: List of objects if found
        """
        return self.simple_match("annotations.createdBy", user_id, projection, generate_response, db_session)

    def find_by_label(self, label_id, projection=None, generate_response=False, db_session=None):
        """
        Find `DetectedObject`s with the given ground-truth label
        :param label_id: Id of the label
        :param projection:
        :param generate_response:
        :param db_session:
        :return: List of objects if found
        """
        return self.simple_match("labelId", label_id, projection, generate_response, db_session)

    def find_bbox_by_id(self, obj_id, db_session=None):
        """
        Find `DetectedObject`s bounding box by the `DetectedObject`'s ID.
        :param obj_id: Id of the object
        :param db_session:
        :return: List of object bounding boxes if found
        """
        return self.find_by_id(obj_id, ('tlx', 'tly', 'brx', 'bry'), False, db_session)

    def find_bbox_by_annotation(self, anno_id, generate_response=False, db_session=None):
        """
        Find `DetectedObject`s bounding box where the `DetectedObject` contains the annotation with the given ID.
        :param anno_id: Id of the annotation
        :param generate_response:
        :param db_session:
        :return: List of object bounding boxes if found
        """
        return self.simple_match("annotations._id", anno_id, ('tlx', 'tly', 'brx', 'bry'),
                                 generate_response, db_session, False)

    def find_all_annotation_ids(self, obj_id, db_session=None):
        """
        Find `DetectedObject`s Annotations by their parent object.
        :param obj_id: Id of the object
        :param db_session:
        :return: List of annotation IDs if found
        """
        result = self.find_by_nested_id(obj_id, projection='annotations._id', db_session=db_session)
        if result is None:
            return None
        result = result['annotations']
        for i, annotation in enumerate(result):
            result[i] = annotation['_id']
        return result

    def delete_all_by_creator(self, user_id, generate_response=False, db_session=None):
        return self.delete_nested_doc_by_match('createdBy', user_id, generate_response, db_session)

    # @transaction
    def add(self, doc_id, label, bbox, annotations=None, generate_response=False, db_session=None):
        user_id = UserDAO().get_current_user_id()
        if annotations is None:
            if isinstance(label, ObjectId):
                label_id = label
            elif isinstance(label, dict):
                label_id = ObjectId(label['_id'])
            else:
                label_id = LabelDAO().find_dynamic(label, projection='_id', db_session=db_session)['_id']
            annotations = self._helper_list
        else:
            if isinstance(label, ObjectId):
                label_id = label
            elif isinstance(label, dict):
                label_id = ObjectId(label['_id'])
            else:
                label = LabelDAO().find_dynamic(label, projection='_id', db_session=db_session)
                label_id = label['_id']
            if isinstance(annotations, str):
                self._helper_list.append(
                    AnnotationDAO().prepare_annotation(annotations, label_id, user_id, db_session))
                annotations = self._helper_list
            else:
                annotations = AnnotationDAO().prepare_annotations(annotations, label_id, user_id,
                                                                  db_session=db_session)
        obj = DetectedObject(id=ObjectId(), labelId=label_id, annotations=annotations, tlx=bbox[0],
                             tly=bbox[1], brx=bbox[2], bry=bbox[3], created_by=user_id)
        # pushes new object into image document
        response = self.insert_doc(obj, (doc_id,), generate_response=generate_response, db_session=db_session)
        self._helper_list.clear()
        from app.db.daos.work_history_dao import WorkHistoryDAO
        WorkHistoryDAO().update_or_add(doc_id, user_id, True, bool(annotations), db_session)
        return response

    # @transaction
    def add_many(self, doc_id, objects, generate_response=False, db_session=None):
        # creates new objects for the given document
        user_id = UserDAO().get_current_user_id()
        objects = self.validate_objects(objects, user_id, db_session)
        response = self.insert_docs(objects, (doc_id,), generate_response=generate_response, db_session=db_session)
        from app.db.daos.work_history_dao import WorkHistoryDAO
        WorkHistoryDAO().update_or_add(doc_id, user_id, True, all(obj['annotations'] for obj in objects), db_session)
        return response

    @dao_update(update_many=False)
    def update_bbox(self, obj_id, bbox):
        self.add_query("_id", obj_id)
        now = datetime.now()
        upd_prefix = "objects.$[]."
        for coord, val in zip(self.bbox_alias_mapping.values(), bbox):
            self._set_field_op[upd_prefix + coord] = val
        self._set_field_op['updatedAt'] = now
        self._set_field_op[upd_prefix + 'updatedAt'] = now
        self._update_commands['$set'] = self._set_field_op

    @dao_update(update_many=False)
    def update_label(self, obj_id, label_id):
        self.add_query("_id", obj_id)
        self.add_update('labelId', label_id)
        now = datetime.now()
        self._set_field_op['updatedAt'] = now
        self.add_update('updatedAt', now)

    def delete_all(self, generate_response=False, db_session=None):
        raise NotImplementedError

    def delete_by_id(self, entity_id, generate_response=False, db_session=None):
        from app.db.daos.image_doc_dao import ImgDocDAO
        return ImgDocDAO().delete_by_id(entity_id, generate_response, db_session)

    def delete_many(self, ids, generate_response=False, db_session=None):
        from app.db.daos.image_doc_dao import ImgDocDAO
        return ImgDocDAO().delete_many(ids, generate_response, db_session)

    def simple_delete(self, key, value, generate_response=False, db_session=None, delete_many=True):
        # Attention: this deletes the entire image matching the query
        from app.db.daos.image_doc_dao import ImgDocDAO
        return ImgDocDAO().simple_delete(self._loc_prefix + key, value, generate_response, db_session, delete_many)
