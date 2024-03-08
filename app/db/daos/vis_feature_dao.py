from datetime import datetime

from bson import ObjectId
from pymongo import ASCENDING

from app.db.daos.annotation_dao import AnnotationDAO
from app.db.daos.base import JoinableDAO, BaseDAO, dao_query
from app.db.daos.concept_dao import ConceptDAO
from app.db.daos.object_dao import ObjectDAO
from app.db.daos.user_dao import UserDAO
from app.db.models.payloads.vis_feature import VisualFeaturePayload
from app.db.models.vis_feature import VisualFeature, BoundingBox


class VisualFeatureDAO(JoinableDAO):
    def __init__(self):
        super().__init__("visfeatures", VisualFeature, VisualFeaturePayload)
        self.references = {
            'annotationId': ('annotation', AnnotationDAO, False),
            'conceptId': ('concept', ConceptDAO, False),
            'createdBy': ('creator', UserDAO, False)
        }

        self.create_index('feature_index', ("annotationId", ASCENDING), ("conceptId", ASCENDING), unique=True)

    @staticmethod
    def validate_bboxs_fit_into_parent(bboxs, parentbb):
        # Non-negativity is checked in the VisualFeature's BoundingBox model
        px = parentbb[2] - parentbb[0]
        py = parentbb[3] - parentbb[1]
        for bbox in bboxs:
            if isinstance(bbox, (list, tuple)):
                brx = bbox[2]
                bry = bbox[3]
            else:
                brx = bbox['brx']
                bry = bbox['bry']
            if brx > px:
                raise ValueError('The bounding box exceeds its parent bounding box on its x-axis!')
            elif bry > py:
                raise ValueError('The bounding box exceeds its parent bounding box on its y-axis!')

    @dao_query()
    def unrolled(self):
        self.join(('annotation', 'creator'), unroll_depth=3)

    def find_by_annotation(self, anno_id, projection=None, generate_response=False, db_session=None):
        return self.simple_match('annotationId', anno_id, projection, generate_response, db_session)

    def find_by_annotations(self, anno_ids, projection=None, generate_response=False, db_session=None):
        self._in_query['$in'] = anno_ids
        self._query_matcher["annotationId"] = self._in_query
        projection = self.build_projection(projection)
        result = self.collection.find(self._query_matcher, projection, session=db_session)
        result = list(self._apply_sort_limit(result))
        self._in_query.clear()
        self._query_matcher.clear()
        if projection:
            projection.clear()
        return self.to_response(result) if generate_response else result

    def find_by_annotation_concept(self, anno_id, concept_id, projection=None,
                                   generate_response=False, db_session=None):
        projection = self.build_projection(projection)
        self._query_matcher['annotationId'] = anno_id
        self._query_matcher['conceptId'] = concept_id
        result = self.collection.find_one(self._query_matcher, projection, session=db_session)
        self._query_matcher.clear()
        if projection:
            projection.clear()
        return self.to_response(result) if generate_response else result

    def find_by_object(self, obj_id, projection=None, generate_response=False, db_session=None, get_cursor=False):
        return self.simple_match('objectId', obj_id, projection,
                                 generate_response, db_session, get_cursor=get_cursor)

    def add(self, obj_id, anno_id, concept_id, bboxs, generate_response=False, db_session=None):
        user_id = UserDAO().get_current_user_id()
        feat = VisualFeature(object_id=obj_id, annotation_id=anno_id, concept_id=concept_id,
                             bboxs=bboxs, created_by=user_id)
        return self.insert_doc(feat, generate_response=generate_response, db_session=db_session)

    def add_secure(self, obj_id, anno_id, concept_id, bboxs, parent_bbox=None, generate_response=False,
                   db_session=None):
        user_id = UserDAO().get_current_user_id()
        if parent_bbox is None:
            parent_bbox = ObjectDAO().find_bbox_by_id(obj_id, db_session=db_session)
            if parent_bbox is None:
                raise ValueError(f'Annotation with ID {anno_id} could not be found!')
            parent_bbox = (parent_bbox['tlx'], parent_bbox['tly'], parent_bbox['brx'], parent_bbox['bry'])
        VisualFeatureDAO.validate_bboxs_fit_into_parent(bboxs, parent_bbox)
        feat = VisualFeature(object_id=obj_id, annotation_id=anno_id, concept_id=concept_id,
                             bboxs=bboxs, created_by=user_id)
        return self.insert_doc(feat, generate_response=generate_response, db_session=db_session)

    def _collect_features(self, obj_id, anno_id, concept_ids, bboxs, user_id, parent_bbox, db_session):
        if parent_bbox is None:
            parent_bbox = ObjectDAO().find_bbox_by_id(obj_id, db_session=db_session)
            parent_bbox = (parent_bbox['tlx'], parent_bbox['tly'], parent_bbox['brx'], parent_bbox['bry'])
        for i, (cid, bbs) in enumerate(zip(concept_ids, bboxs)):
            VisualFeatureDAO.validate_bboxs_fit_into_parent(bbs, parent_bbox)
            self._helper_list.append(VisualFeature(object_id=obj_id, annotation_id=anno_id, concept_id=cid,
                                                   bboxs=bbs, created_by=user_id))
        return concept_ids

    def add_many(self, obj_ids, anno_ids, concept_ids, bboxs, parent_bboxs=None,
                 generate_response=False, db_session=None):
        user_id = UserDAO().get_current_user_id()
        if isinstance(anno_ids, ObjectId):
            self._collect_features(obj_ids, anno_ids, concept_ids, bboxs, user_id, parent_bboxs, db_session)
        else:
            if parent_bboxs is None:
                for oid, aid, cids, bbs in zip(obj_ids, anno_ids, concept_ids, bboxs):
                    self._collect_features(oid, aid, cids, bbs, user_id, parent_bboxs, db_session)
            else:
                for i, (oid, aid, cids, bbs) in enumerate(zip(obj_ids, anno_ids, concept_ids, bboxs)):
                    self._collect_features(oid, aid, cids, bbs, user_id, parent_bboxs[i], db_session)
        response = self.insert_docs(self._helper_list, generate_response=generate_response, db_session=db_session)
        if not generate_response:
            self._helper_list.clear()
        return response

    def push_bboxs(self, feat_id, bboxs, generate_response=False, db_session=None):
        for i, bbox in enumerate(bboxs):
            if isinstance(bbox, (list, tuple)):
                bboxs[i] = BoundingBox(tlx=bbox[0], tly=bbox[1], brx=bbox[2], bry=bbox[3]).to_dict()
        self._set_field_op['updatedAt'] = datetime.now()
        self._update_commands['$set'] = self._set_field_op
        result = self.array_push_many('bboxs', bboxs, ('_id', feat_id), False, db_session)
        del self._set_field_op['updatedAt']
        return self.to_response(result, BaseDAO.UPDATE) if generate_response else result
