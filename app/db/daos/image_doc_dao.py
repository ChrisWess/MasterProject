import json
from base64 import b64decode
from copy import deepcopy
from io import BytesIO
from json import loads
from math import ceil

from PIL import Image, ImageOps
from bson import ObjectId
from pymongo import ASCENDING, DESCENDING, TEXT

from app import config, fs
from app.db.daos.annotation_dao import AnnotationDAO
from app.db.daos.base import JoinableDAO, dao_query, dao_update, BaseDAO
from app.db.daos.label_dao import LabelDAO
from app.db.daos.object_dao import ObjectDAO
from app.db.daos.user_dao import UserDAO
from app.db.daos.vis_feature_dao import VisualFeatureDAO
from app.db.models.image_doc import ImgDoc
from app.db.models.object import DetectedObject
from app.db.models.payloads.image_doc import ImagePayload
from app.db.models.payloads.object import ObjectPayload
from app.db.stats.daos.image_prios import PrioStatsDAO
from app.db.stats.daos.image_stats import ImageStatsDAO
from app.db.stats.daos.project_progress import ProjectProgressDAO
from app.db.stats.daos.work_stats import WorkHistoryStatsDAO
from app.db.util import encode_as_base64
from app.preproc.object import detect_objects


def resize_with_padding(img, exp_width, exp_height):
    img.thumbnail((exp_width, exp_height))
    delta_width = exp_width - img.size[0]
    delta_height = exp_height - img.size[1]
    pad_width = delta_width // 2
    pad_height = delta_height // 2
    padding = (pad_width, pad_height, delta_width - pad_width, delta_height - pad_height)
    return ImageOps.expand(img, padding)


class ImgDocDAO(JoinableDAO):
    __slots__ = "_meta_score", "_thumb_page_limit"

    def __init__(self):
        # Initialize mongodb collection of image documents
        super().__init__("images", ImgDoc, ImagePayload)
        self.references = {
            'objects': ObjectDAO,
            'createdBy': ('creator', UserDAO, False)
        }
        self.stat_references = (ImageStatsDAO, PrioStatsDAO, WorkHistoryStatsDAO)
        self._num_docs_per_export_file = 50
        self.create_index('idoc_name_index', ('name', TEXT), default_language='english')

        self._meta_score = {'$meta': "textScore"}
        self._thumb_page_limit = config.NUM_THUMBNAILS_PER_PAGE

    def build_projection(self, projection, exclude_bytes=True):
        try:
            if isinstance(projection, dict):
                do_b64trafo = int(projection.get('base64img', 0))
            else:
                do_b64trafo = False
        except ValueError:
            do_b64trafo = False
        projection = super().build_projection(projection)
        if exclude_bytes:
            if projection:
                is_inclusion = bool(next(iter(projection.values())))
                if do_b64trafo:
                    if is_inclusion:
                        if 'image' not in projection and 'thumbnail' not in projection:
                            projection['image'] = 1
                            projection['thumbnail'] = 1
                    return projection
            elif do_b64trafo:
                return None
            else:
                projection = self._projection_dict
                is_inclusion = False
            if is_inclusion:
                has_img = 'image' in projection
                has_thumb = 'thumbnail' in projection
                if (len(projection) == 1 and (has_img or has_thumb)) or (
                        len(projection) == 2 and has_img and has_thumb):
                    projection['image'] = 0
                    projection['thumbnail'] = 0
                else:
                    if has_img:
                        del projection['image']
                    if has_thumb:
                        del projection['thumbnail']
            else:
                projection['image'] = 0
                projection['thumbnail'] = 0
        return projection

    def load_image(self, doc_id, db_session=None):
        try:
            self._query_matcher["_id"] = doc_id
            self._projection_dict["image"] = 1
            result = self.collection.find_one(self._query_matcher, self._projection_dict, session=db_session)
            if result is not None:
                result = fs.get(result['image'], session=db_session).read()
        finally:
            self._query_matcher.clear()
            self._projection_dict.clear()
        return result

    def load_thumbnail_data(self, doc_id, db_session=None):
        """ Returns Byte data of the thumbnail image """
        try:
            query = self.add_query("_id", doc_id)
            self._projection_dict['thumbnail'] = 1
            result = self.collection.find_one(query, self._projection_dict, session=db_session)
            if result is not None:
                result = result['thumbnail']
        finally:
            self.clear_query()
            self._projection_dict.clear()
        return result

    def load_thumbnails(self, doc_ids=None, sort_by=None, generate_response=False, db_session=None):
        """
        Returns base64 encoded byte data of the thumbnail images, because
        multiple images are quite difficult to transfer over a REST API.
        """
        try:
            self._projection_dict["thumbnail"] = 1
            if doc_ids:
                try:
                    query = self.add_query("_id", doc_ids)
                    result = self.collection.find(query, self._projection_dict, session=db_session)
                finally:
                    self.clear_query()
            else:
                result = self.collection.find(self._query_matcher, self._projection_dict, session=db_session)
            if sort_by and 'sort_by' in sort_by:
                sorter = sort_by['sort_by']
                if sorter in self.example_schema:
                    desc = DESCENDING if sort_by.get('desc', True) else ASCENDING
                    result = result.sort(sorter, desc)
            result = [encode_as_base64(fs.get(doc['thumbnail'], session=db_session).read()) for doc in result]
        finally:
            self._projection_dict.clear()
        if generate_response:
            return {"result": result, "numResults": len(result),
                    "status": 200, 'model': 'base64img', 'isComplete': True}
        else:
            return result

    def load_thumbnails_paginated(self, page_idx, proj_id=None, sort_by=None, generate_response=False, db_session=None):
        """ Returns a page of base64 encoded thumbnail images. """
        assert page_idx > 0
        # needs one unique field in sort, when using $skip (maybe using _id is faster?)
        try:
            self.sort_by('createdAt')
            if sort_by and 'sort_by' in sort_by:
                sorter = sort_by['sort_by']
                if sorter in self.example_schema:
                    self.sort_by(sorter, sort_by.get('desc', True))
            self._skip_results = (page_idx - 1) * self._thumb_page_limit
            self._projection_dict['thumbnail'] = 1
            self._projection_dict['name'] = 1
            if proj_id is None:
                result = self.collection.find(self._query_matcher, self._projection_dict, session=db_session)
                total_thumbs = self.collection.estimated_document_count()
            else:
                self._query_matcher['projectId'] = proj_id
                result = self.collection.find(self._query_matcher, self._projection_dict, session=db_session)
                total_thumbs = ProjectProgressDAO().update_and_get(proj_id, 'numDocs', db_session=db_session)
                total_thumbs = 0 if total_thumbs is None else total_thumbs['numDocs']
            if len(self._sort_list) == 1:
                result = result.sort(*self._sort_list[0]).skip(self._skip_results).limit(self._thumb_page_limit)
            else:
                result = result.sort(self._sort_list).skip(self._skip_results).limit(self._thumb_page_limit)
            result = [(str(doc['_id']), doc['name'],
                       encode_as_base64(fs.get(doc['thumbnail'], session=db_session).read())) for doc in result]
        finally:
            self.clear_query()
            self._projection_dict.clear()
        if generate_response:
            n_pages = ceil(total_thumbs / self._thumb_page_limit)
            return {"result": result, "numResults": len(result), "atPage": page_idx, "numPages": n_pages,
                    "status": 200, 'model': 'base64img', 'isComplete': True}
        else:
            return result

    def search_thumbnails(self, page_idx, search_phrase, proj_id, generate_response=False, db_session=None):
        assert page_idx > 0
        try:
            self.sort_by('score')
            self.sort_by('createdAt')
            self._skip_results = (page_idx - 1) * self._thumb_page_limit
            self._projection_dict['score'] = self._meta_score
            self._projection_dict['thumbnail'] = 1
            self._projection_dict['name'] = 1
            self._search_instructions['$search'] = search_phrase
            self._query_matcher['$text'] = self._search_instructions
            self._query_matcher['projectId'] = proj_id
            result = self.collection.find(self._query_matcher, self._projection_dict, session=db_session)
            result = result.sort(self._sort_list).skip(self._skip_results).limit(self._thumb_page_limit)
            result = [(str(doc['_id']), doc['name'],
                       encode_as_base64(fs.get(doc['thumbnail'], session=db_session).read())) for doc in result]
            if generate_response:
                total_thumbs = self.collection.count_documents(self._query_matcher)
                n_pages = ceil(total_thumbs / self._thumb_page_limit)
                return {"result": result, "numResults": len(result), "atPage": page_idx, "numPages": n_pages,
                        "status": 200, 'model': 'base64img', 'isComplete': True}
            else:
                return result
        finally:
            self.clear_query()
            self._projection_dict.clear()

    @dao_query()
    def unrolled(self, unroll_depth=2):
        self.join(unroll_depth=unroll_depth)

    def find_all(self, projection=None, generate_response=False, get_cursor=False, db_session=None):
        """
        Find all Image Documents in the collection (images are omitted for size reasons)
        :param projection:
        :param generate_response:
        :param get_cursor:
        :param db_session:
        :return: List of all `ImgDoc` objects
        """
        try:
            projection = self.build_projection(projection)
            if get_cursor:
                projection_copy = deepcopy(projection) if projection else projection
                result = self.collection.find(self._query_matcher, projection_copy, session=db_session)
                result = self._apply_sort_limit(result, True)
            else:
                result = self.collection.find(self._query_matcher, projection, session=db_session)
                result = list(self._apply_sort_limit(result))
        finally:
            if projection:
                projection.clear()
        return self.to_response(result) if generate_response else result

    def find_all_complete(self, projection=None, get_cursor=False, db_session=None):
        """
        Find all Image Documents in the collection including images and thumbnails!
        This should not be accessible directly from the outside!
        :param projection:
        :param get_cursor:
        :param db_session:
        :return: List of all complete `ImgDoc` objects
        """
        try:
            if projection:
                projection = self.build_projection(projection, False)
                if get_cursor:
                    projection_copy = deepcopy(projection) if projection else projection
                    result = self.collection.find(self._query_matcher, projection_copy, session=db_session)
                else:
                    result = self.collection.find(self._query_matcher, projection, session=db_session)
            else:
                result = self.collection.find(session=db_session)
            if get_cursor:
                result = self._apply_sort_limit(result, True)
            else:
                result = list(self._apply_sort_limit(result))
        finally:
            if projection:
                projection.clear()
        return result

    def find_many(self, doc_ids, projection=None, generate_response=False, get_cursor=False, db_session=None):
        """
        Find all Image Documents that match an id in given list of ids.
        :param projection:
        :param generate_response:
        :param get_cursor:
        :param db_session:
        :param doc_ids: Ids of the documents to find
        :return: List of `ImgDoc` objects that match the provided IDs without image and thumbnail data
        """
        try:
            projection = self.build_projection(projection)
            if type(doc_ids) is not list:
                for i in doc_ids:
                    self._helper_list.append(i)
                doc_ids = self._helper_list
            self._in_query['$in'] = doc_ids
            self._query_matcher["_id"] = self._in_query
            if get_cursor:
                projection_copy = deepcopy(projection) if projection else projection
                result = self.collection.find(deepcopy(self._query_matcher), projection_copy, session=db_session)
                result = self._apply_sort_limit(result, True)
            else:
                result = self.collection.find(self._query_matcher, projection, session=db_session)
                result = list(self._apply_sort_limit(result))
                if doc_ids == self._helper_list:
                    self._helper_list.clear()
        except Exception as e:
            self._helper_list.clear()
            raise e
        finally:
            self._in_query.clear()
            self._query_matcher.clear()
            if projection:
                projection.clear()
        return self.to_response(result) if generate_response else result

    def find_by_id(self, doc_id, projection=None, generate_response=False, db_session=None):
        """
        Find the Image Document with given id
        :param projection:
        :param generate_response:
        :param db_session:
        :param doc_id: Id of Image Document to find
        :return: `ImgDoc` without image and thumbnail data if found, None otherwise
        """
        try:
            projection = self.build_projection(projection)
            self._query_matcher["_id"] = doc_id
            result = self.collection.find_one(self._query_matcher, projection, session=db_session)
        finally:
            self._query_matcher.clear()
            if projection:
                projection.clear()
        return self.to_response(result) if generate_response and result is not None else result

    def find_by_id_complete(self, doc_id, projection=None, db_session=None):
        """
        Find the Image Document with the given ID in the collection including images and thumbnails!
        This should not be accessible directly from the outside!
        :param doc_id: the ID of the Image Document
        :param projection:
        :param db_session:
        :return: List of the complete Image Document object
        """
        try:
            projection = self.build_projection(projection, False)
            self._query_matcher["_id"] = doc_id
            result = self.collection.find_one(self._query_matcher, projection, session=db_session)
        finally:
            self._query_matcher.clear()
            if projection:
                projection.clear()
        return result

    def get_img_sample(self, sample_size, projection=None, generate_response=False, db_session=None):
        projection = super().build_projection(projection)
        self._agg_pipeline.append({'$sample': {'size': sample_size}})
        if projection:
            if 'image' in projection and projection['image'] == 0:
                del projection['image']
            elif any(p for p in projection):
                projection['image'] = 1
            self._agg_pipeline.append(self._agg_projection)
        agg = self.collection.aggregate(self._agg_pipeline, session=db_session)
        result = []
        for res in agg:
            res['image'] = fs.get(res['image'], session=db_session).read()
            result.append(res)
        return self.to_response(result) if generate_response and result is not None else result

    def find_by_name(self, name, projection=None, generate_response=False, db_session=None):
        """
        Find the image document with the given image name
        :param name: name of the image (document)
        :param projection:
        :param generate_response:
        :param db_session:
        :return: ImgDoc objects with the given name
        """
        return self.simple_match("name", name, projection, generate_response, db_session)

    def find_by_object(self, obj_id, projection=None, generate_response=False, db_session=None):
        """
        Find the image document that contains the detected object with id obj_id
        :param obj_id: Id of the detected object
        :param projection:
        :param generate_response:
        :param db_session:
        :return: ImgDoc object
        """
        return self.simple_match("objects._id", obj_id, projection, generate_response, db_session, find_many=False)

    def find_by_annotation(self, anno_id, projection=None, generate_response=False, db_session=None):
        """
        Find the image document that contains the annotation with id anno_id
        :param anno_id: Id of the annotation
        :param projection:
        :param generate_response:
        :param db_session:
        :return: ImgDoc object
        """
        return self.simple_match("objects.annotations._id", anno_id, projection,
                                 generate_response, db_session, find_many=False)

    @dao_query()
    def search_in_annotations(self, search_str):
        """
        Find `ImgDoc`s that have annotations that match the given search string
        :param search_str: string that must be contained in any annotation of the image document
        :return: List of `ImgDoc`s that contain annotations that match the given search string
        """
        self.add_query('objects.annotations.text', {"$regex": search_str})

    def delete_by_name(self, name, generate_response=False, db_session=None):
        return self.simple_delete('name', name, generate_response, db_session)

    def detect_objects_for_image(self, doc_id, classes=None, save_objs=True, generate_response=False, db_session=None):
        user_id = UserDAO().get_current_user_id()
        img = self.load_image(doc_id, db_session=db_session)
        img = Image.open(BytesIO(img))
        objs = detect_objects(img, classes)
        obj_entities = []
        for bbox, cls_name in objs:
            label_name = 'generic ' + cls_name
            label_id = LabelDAO().find_or_add(label_name, cls_name, projection='_id')['_id']
            new_obj = DetectedObject(id=ObjectId(), labelId=label_id, tlx=bbox[0],
                                     tly=bbox[1], brx=bbox[2], bry=bbox[3], created_by=user_id)
            if not save_objs:
                new_obj = new_obj.to_dict()
            obj_entities.append(new_obj)
        object_dao = ObjectDAO()
        if save_objs:
            obj_entities = object_dao.add_many(doc_id, obj_entities, db_session=db_session)
        return object_dao.to_response(obj_entities) if generate_response else obj_entities

    @staticmethod
    def process_image_data(img_data, thumb_w=200, thumb_h=200):
        img = Image.open(BytesIO(img_data))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        thumb = resize_with_padding(img.copy(), thumb_w, thumb_h)
        img_io, thumb_io = BytesIO(), BytesIO()
        img.save(img_io, format='JPEG')
        thumb.save(thumb_io, format='JPEG')
        return img_io.getvalue(), thumb_io.getvalue(), img.width, img.height, img

    def insert_doc(self, doc, image, thumb, proj_id, has_annos=True, has_gaps=False,
                   generate_response=True, db_session=None):
        image = fs.put(image)
        doc.image = image
        thumb = fs.put(thumb)
        doc.thumbnail = thumb
        response = super().insert_doc(doc, generate_response=False, db_session=db_session)
        doc = response[1]
        if has_annos:
            from app.db.daos.work_history_dao import WorkHistoryDAO
            WorkHistoryDAO().add(doc['_id'], doc['createdBy'], proj_id, not has_gaps, db_session=db_session)
        if generate_response:
            doc = self.model.postprocess_insert_response(doc, doc['_id'])
            return self.to_response(doc, BaseDAO.CREATE, validate=False)
        else:
            return response

    # @transaction
    def add(self, name, fname, image, proj_id=None, objects=None, detect_objs=False,
            generate_response=False, db_session=None):
        # creates a new document in the docs collection
        try:
            user_id = UserDAO().get_current_user_id()
            has_annos = has_unanno_objs = False
            if objects is None:
                objects = self._helper_list
            else:
                if isinstance(objects, dict):
                    self._helper_list.append(ObjectDAO.validate_object(objects, user_id, db_session))
                    objects = self._helper_list
                else:
                    objects = ObjectDAO.validate_objects(objects, user_id, db_session)
                for obj in objects:
                    if obj.annotations:
                        has_annos = True
                    else:
                        has_unanno_objs = True
            image, thumb, width, height, pil_img = self.process_image_data(image)
            if detect_objs:
                for bbox, cls_name in detect_objects(pil_img):
                    label_name = 'generic ' + cls_name
                    label_id = LabelDAO().find_or_add(label_name, cls_name, projection='_id')['_id']
                    new_obj = DetectedObject(id=ObjectId(), labelId=label_id, tlx=bbox[0],
                                             tly=bbox[1], brx=bbox[2], bry=bbox[3], created_by=user_id)
                    objects.append(new_obj)
            doc = ImgDoc(project_id=proj_id, name=name, fname=fname, width=width,
                         height=height, created_by=user_id, objects=objects)
            # TODO: multi-document transactions with gridfs raise an error! Find workaround for ensuring files
            #  are not stored, if the transaction aborts. Otherwise, there will be unreferenced images
            #  stored in the gridfs collection that would take up disk space without any use.
            return self.insert_doc(doc, image, thumb, proj_id, has_annos, has_unanno_objs,
                                   generate_response=generate_response, db_session=db_session)
        finally:
            self._helper_list.clear()

    # @transaction
    def add_from_json(self, doc, user_id=None, as_bulk=False, generate_response=False, db_session=None):
        # creates a new document in the collection by extracting the insertion info from a JSON doc
        try:
            if user_id is None:
                user_id = UserDAO().get_current_user_id()
            has_annos = has_unanno_objs = False
            objects = doc['objects']
            for i, obj in enumerate(objects):
                annos = obj["annotations"]
                if annos:
                    has_annos = True
                    for j, anno in enumerate(annos):
                        self._helper_list.append(anno.get('_id', None))
                        annos[j] = anno['text']
                    annos = AnnotationDAO().prepare_annotations(annos, obj['labelId'], user_id, True, db_session)
                    for j, anno in enumerate(annos):
                        aid = self._helper_list[j]
                        if aid is not None:
                            anno.id = aid
                    self._helper_list.clear()
                else:
                    has_unanno_objs = True
                obj['createdBy'] = user_id
                if '_id' not in obj:
                    obj['_id'] = ObjectId()
                objects[i] = DetectedObject(**obj)
            image = doc['image']
            if type(image) is str:
                image = b64decode(image)
            image, thumb, width, height, pil_img = self.process_image_data(image)
            proj_id = doc.get('projectId', None)
            doc = ImgDoc(project_id=proj_id, name=doc['name'], fname=doc['fname'],
                         width=width, height=height, created_by=user_id, objects=objects)
            if as_bulk:
                return (doc, image, thumb, not has_unanno_objs) if has_annos else (doc, image, thumb)
            else:
                return self.insert_doc(doc, image, thumb, proj_id, has_annos, has_unanno_objs,
                                       generate_response=generate_response, db_session=db_session)
        finally:
            self._helper_list.clear()

    # @transaction
    def add_with_annos(self, name, fname, image, annotations, label, user_id, proj_id=None,
                       as_bulk=False, detect_objs=False, generate_response=False, db_session=None):
        # creates a new document in the docs collection
        try:
            label_id = label['_id']
            image, thumb, width, height, pil_img = self.process_image_data(image)
            has_annos = bool(annotations)
            if has_annos:
                annotations = AnnotationDAO().prepare_annotations(annotations, label_id, user_id, True)
            new_id = ObjectId()
            detected = None
            objs = [None]
            if detect_objs:
                detected = True
                # keep only the one BBox with the highest surface area
                max_bbox_surface = 0
                for bbox, _ in detect_objects(pil_img, label['categories']):
                    curr_surface = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
                    new_obj = DetectedObject(id=new_id, labelId=label_id, tlx=bbox[0], tly=bbox[1], brx=bbox[2],
                                             bry=bbox[3], annotations=annotations, created_by=user_id)
                    if max_bbox_surface < curr_surface:
                        max_bbox_surface = curr_surface
                        objs[0] = new_obj
            if objs[0] is None:
                if detect_objs:
                    detected = False
                objs[0] = DetectedObject(id=new_id, label_id=label_id, tlx=0, tly=0, brx=width, bry=height,
                                         annotations=annotations, created_by=user_id)
            doc = ImgDoc(project_id=proj_id, name=name, fname=fname, width=width,
                         height=height, created_by=user_id, objects=objs)
            if as_bulk:
                return (doc, image, thumb, not has_annos) if has_annos else (doc, image, thumb), detected
            else:
                return self.insert_doc(doc, image, thumb, proj_id,
                                       generate_response=generate_response, db_session=db_session), detected
        finally:
            self._helper_list.clear()

    @dao_update(update_many=False)
    def update_image(self, doc_id, new_img):
        new_img, thumb, width, height, _ = self.process_image_data(new_img)
        self.add_query("_id", doc_id)
        self.add_update('image', new_img)
        self.add_update('width', width)
        self.add_update('height', height)
        # TODO: validate that object bboxes are still valid in new image

    @dao_update(update_many=False)
    def rename_doc(self, doc_id, name):
        self.add_query("_id", doc_id)
        self.add_update('name', name)

    @dao_update(update_many=False)
    def remove_project_id(self, doc_id):
        self.add_query("_id", doc_id)
        self.add_update('projectId', None)

    @dao_query()
    def export_dataset_info(self, doc_ids):
        self.add_query("_id", doc_ids, "$in")
        self.join('objects.label', unroll_depth=1)
        self.join('objects.annotations.concepts', unroll_depth=1)

    def export_image_info(self, doc_ids, include_features=True, projection=None):
        yield '[\n'
        prev_doc = None
        for doc in self.export_dataset_info(doc_ids, projection=projection, get_cursor=True):
            doc['image'] = self.load_image(doc['_id'])
            if include_features:
                try:
                    doc = self.validate_doc(doc, False)[0]
                    # Add visual features to the corresponding annotations
                    for i, obj in enumerate(doc['objects']):
                        for j, anno in enumerate(obj['annotations']):
                            aid = ObjectId(anno['_id'])
                            self._helper_list.append(aid)
                            self._field_check[aid] = (i, j)
                    feats = VisualFeatureDAO().find_by_annotations(self._helper_list,
                                                                   projection=('annotationId', 'conceptId', 'bboxs'))
                    for feat in feats:
                        aid = ObjectId(feat.pop('annotationId'))
                        del feat['_id']
                        feat['conceptId'] = str(feat.pop('conceptId'))
                        i, j = self._field_check[aid]
                        anno = doc['objects'][i]['annotations'][j]
                        if 'idxPath' not in anno:
                            anno['idxPath'] = [i, j]
                        anno_feats = anno.get('visFeatures', None)
                        if anno_feats is None:
                            anno['visFeatures'] = [feat]
                        else:
                            anno_feats.append(feat)
                finally:
                    self._helper_list.clear()
                    self._field_check.clear()
                doc = json.dumps(doc)
            else:
                doc = self.validate_doc(doc, False, True)[0]
            if prev_doc is not None:
                yield prev_doc + ',\n'
            prev_doc = doc
        if prev_doc is None:
            yield '\n]'
        else:
            yield prev_doc + '\n]'

    def _prepare_doc_import(self, doc):
        doc = loads(doc)
        thumb_id = fs.put(b64decode(doc['thumbnail']))
        doc['thumbnail'] = thumb_id
        img_id = fs.put(b64decode(doc['image']))
        doc['image'] = img_id
        return self.model(**doc).model_dump(by_alias=True)

    def replace_objects(self, doc_id, new_objects, old_object_ids=None, generate_response=False, db_session=None):
        VisualFeatureDAO().delete_features_by_image(doc_id, old_object_ids, db_session=db_session)
        result = self._replace_objects(doc_id, new_objects, generate_response=generate_response, db_session=db_session)
        if generate_response:
            object_res = result['result']['updatedTo']['set']['objects']
            for i, obj in enumerate(object_res):
                object_res[i] = ObjectPayload(**obj).to_dict()
        return result

    @dao_update(update_many=False)
    def _replace_objects(self, doc_id, new_objects):
        self.add_query("_id", doc_id)
        self.add_update('objects', new_objects)

    # @transaction
    def delete(self, delete_many=False, custom_query=None, db_session=None):
        """
        Execute the currently configured query, if custom_query=None.
        Otherwise this simply executes the query from custom_query.
        """
        # FIXME: for deletion of images, objects and annotations: optionally (because the bbox info might be valuable
        #  even if the annotation does not exist anymore) check for each removed annotation ID, if there are
        #  visual features assigned to it, cascade remove these visual features.
        #  Idea: include objects.annotations._id in the find
        try:
            query = self._query_matcher if custom_query is None else custom_query
            imgk, thumbk = 'image', 'thumbnail'
            self._projection_dict[imgk] = 1
            self._projection_dict[thumbk] = 1
            if delete_many:
                result = self.collection.find(query, self._projection_dict, session=db_session)
                for doc in result:
                    self._helper_list.append(doc['_id'])
                    fs.delete(doc[imgk], session=db_session)
                    fs.delete(doc[thumbk], session=db_session)
                self._remove_stat_ids_from_helper(db_session)
                result = self.collection.delete_many(query, session=db_session)
            else:
                result = self.collection.find_one(query, self._projection_dict, session=db_session)
                self._helper_list.append(result['_id'])
                fs.delete(result[imgk], session=db_session)
                fs.delete(result[thumbk], session=db_session)
                self._remove_stat_ids_from_helper(db_session)
                result = self.collection.delete_one(query, session=db_session)
        finally:
            self._helper_list.clear()
            self._projection_dict.clear()
            self.clear_query()
        return result

    # @transaction
    def delete_all(self, generate_response=False, db_session=None):
        """
        Execute the currently configured query, if custom_query=None.
        Otherwise this simply executes the query from custom_query.
        """
        imgk, thumbk = 'image', 'thumbnail'
        try:
            self._projection_dict[imgk] = 1
            self._projection_dict[thumbk] = 1
            result = self.collection.find(self._projection_dict, session=db_session)
            for doc in result:
                fs.delete(doc[imgk], session=db_session)
                fs.delete(doc[thumbk], session=db_session)
            result = super().delete_all(generate_response, db_session)
        finally:
            self._projection_dict.clear()
        return result

    def _delete_image(self, db_session=None):
        result = self.collection.find_one(self._query_matcher, self._projection_dict, session=db_session)
        fs.delete(result['image'], session=db_session)
        fs.delete(result['thumbnail'], session=db_session)
        return self.collection.delete_one(self._query_matcher, session=db_session)

    def _delete_images(self, db_session=None):
        result = self.collection.find(self._query_matcher, self._projection_dict, session=db_session)
        for doc in result:
            fs.delete(doc['image'], session=db_session)
            fs.delete(doc['thumbnail'], session=db_session)
        return self.collection.delete_many(self._query_matcher, session=db_session)

    # @transaction
    def delete_by_id(self, entity_id, generate_response=False, db_session=None):
        # TODO: delete all visual features of all deleted nested annotations, and delete work history
        try:
            self._query_matcher["_id"] = entity_id
            self._projection_dict['image'] = 1
            self._projection_dict['thumbnail'] = 1
            self._helper_list.append(entity_id)
            self._remove_stat_ids_from_helper(db_session)
            result = self._delete_image(db_session)
        finally:
            self._helper_list.clear()
            self._query_matcher.clear()
            self._projection_dict.clear()
        return self.to_response(result, BaseDAO.DELETE) if generate_response else result

    # @transaction
    def delete_many(self, ids, generate_response=False, db_session=None):
        try:
            for i in ids:
                self._helper_list.append(i)
            ids = self._helper_list
            self._in_query['$in'] = ids
            self._query_matcher["_id"] = self._in_query
            self._remove_stat_ids_from_helper(db_session)
            self._projection_dict['image'] = 1
            self._projection_dict['thumbnail'] = 1
            result = self._delete_images(db_session)
        finally:
            self._query_matcher.clear()
            self._in_query.clear()
            self._helper_list.clear()
            self._projection_dict.clear()
        if generate_response:
            return self.to_response(result, operation=BaseDAO.DELETE)
        return result

    # @transaction
    def simple_delete(self, key, value, generate_response=False, db_session=None, delete_many=True):
        try:
            self._query_matcher[key] = value
            self._projection_dict['image'] = 1
            self._projection_dict['thumbnail'] = 1
            self._remove_stats(self._query_matcher, db_session)
            result = self._delete_images(db_session) if delete_many else self._delete_image(db_session)
        finally:
            del self._query_matcher[key]
            self._projection_dict.clear()
        return self.to_response(result) if generate_response else result
