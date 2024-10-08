from bson import ObjectId
from bson.errors import InvalidId
from flask import request, abort

from app import application
from app.db.daos.base import BaseDAO
from app.db.daos.object_dao import ObjectDAO
from app.db.daos.vis_feature_dao import VisualFeatureDAO
from app.db.models.payloads.vis_feature import VisualFeaturePayload


@application.route('/visFeature', methods=['GET'])
def find_all_features():
    return VisualFeatureDAO().find_all(projection=request.args, generate_response=True)


@application.route('/visFeature/expanded', methods=['GET'])
def expand_all_features():
    return VisualFeatureDAO().unrolled(generate_response=True)


@application.route('/visFeature/object/<obj_id>', methods=['GET'])
def find_features_of_object(obj_id):
    try:
        return VisualFeatureDAO().find_by_object(ObjectId(obj_id), projection=request.args, generate_response=True)
    except InvalidId:
        err_msg = "The Detected Object ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/visFeature/annotation/<anno_id>/concept/<concept_id>', methods=['GET'])
def find_feature_by_annotation_concept(anno_id, concept_id):
    try:
        anno_id = ObjectId(anno_id)
    except InvalidId:
        err_msg = "The Annotation ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    try:
        feat = VisualFeatureDAO().find_by_annotation_concept(anno_id, ObjectId(concept_id), projection=request.args,
                                                             generate_response=True)
        if feat is None:
            err_msg = "No visual feature found by the given IDs!"
            application.logger.error(err_msg)
            abort(400, err_msg)
        return feat
    except InvalidId:
        err_msg = "The Concept ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/visFeature/annotation/<anno_id>', methods=['GET'])
def find_features_of_annotation(anno_id):
    try:
        return VisualFeatureDAO().find_by_annotation(ObjectId(anno_id), projection=request.args, generate_response=True)
    except InvalidId:
        err_msg = "The annotation ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/visFeature/annotations', methods=['GET'])
def find_features_of_annotations():
    args = request.args
    if "annoIds" not in args:
        err_msg = 'Your request body must contain the key-value pair "annoIds"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    anno_ids = args["annoIds"].split(',')
    for i, aid in enumerate(anno_ids):
        try:
            anno_ids[i] = ObjectId(aid)
        except InvalidId:
            err_msg = f"The annotation ID {aid} you provided is not a valid ID!"
            application.logger.error(err_msg)
            abort(404, err_msg)
    return VisualFeatureDAO().find_by_annotations(anno_ids, projection=request.args, generate_response=True)


def validate_visual_feature(annotation_id, concept_id, bboxs):
    obj = ObjectDAO().prepare_feature_check(annotation_id)
    if obj is None:
        err_msg = "No annotation with the given ID could be found!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    contains_flag = False
    for cid in obj['annotations']['conceptIds']:
        if cid == concept_id:
            contains_flag = True
            break
    if not contains_flag:
        err_msg = "The concept ID you provided is not present in the given annotation!"
        application.logger.error(err_msg)
        abort(400, err_msg)
    parent_bb = (obj['tlx'], obj['tly'], obj['brx'], obj['bry'])
    check_bbs = tuple((tlx + parent_bb[0], tly + parent_bb[1], brx + parent_bb[0], bry + parent_bb[1])
                      for tlx, tly, brx, bry in bboxs)
    VisualFeatureDAO.validate_bboxs_fit_into_parent(check_bbs, parent_bb)
    return obj['_id']


def prepare_add_or_update(args):
    if "conceptId" not in args or "bboxs" not in args or "annoId" not in args:
        err_msg = 'Your request body must contain the key-value pairs with keys "conceptId", "annoId" and "bboxs"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    bboxs = args["bboxs"]
    if type(bboxs) is not list:
        err_msg = ("The visual feature bounding boxes have to be lists of integers with top-left x-y and "
                   "bottom-right x-y coordinates (contained in a list)!")
        application.logger.error(err_msg)
        abort(400, err_msg)
    elif bboxs and isinstance(bboxs[0], (int, float)):
        if len(bboxs) != 4:
            err_msg = ("A bounding box definition must contain the info of the top-left x-y and "
                       "bottom-right x-y coordinates = 4 xy-values!")
            application.logger.error(err_msg)
            abort(400, err_msg)
        bboxs = [bboxs]
    for bbox in bboxs:
        for i, coord in enumerate(bbox):
            bbox[i] = int(coord)
    annotation_id = args["annoId"]
    try:
        anno_id = ObjectId(annotation_id)
    except InvalidId:
        err_msg = "The annotation ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    try:
        concept_id = ObjectId(args["conceptId"])
        try:
            obj_id = validate_visual_feature(anno_id, concept_id, bboxs)
        except ValueError as e:
            err_msg = str(e)
            application.logger.error(err_msg)
            abort(400, err_msg)
        return anno_id, concept_id, obj_id, bboxs
    except InvalidId:
        err_msg = "The concept ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/visFeature', methods=['POST'])
# @login_required
def add_feature():
    args = request.json
    anno_id, concept_id, obj_id, bboxs = prepare_add_or_update(args)
    ex_feature = VisualFeatureDAO().find_by_annotation_concept(anno_id, concept_id, projection='_id')
    if ex_feature is None:
        feat_dao = VisualFeatureDAO()
        feature = feat_dao.add(obj_id, anno_id, concept_id, bboxs)[1]
        application.logger.info(f"Added new feature {feature['_id']} to annotation {anno_id} !")
        response = feat_dao.to_response(feature, BaseDAO.CREATE)
        response['result'] = VisualFeaturePayload(**feature).to_dict()
        return response
    else:
        err_msg = "A Visual Feature with the given IDs does already exist!"
        application.logger.error(err_msg)
        abort(400, err_msg)


@application.route('/visFeature', methods=['PUT'])
# @login_required
def update_feature():
    args = request.json
    anno_id, concept_id, obj_id, bboxs = prepare_add_or_update(args)
    ex_feature = VisualFeatureDAO().find_by_annotation_concept(anno_id, concept_id, projection='bboxs')
    if ex_feature is None:
        err_msg = "No Visual Feature with the given IDs exist, yet! Please insert the feature!"
        application.logger.error(err_msg)
        abort(400, err_msg)
    old_bboxs = ex_feature['bboxs']
    for i, bbox in enumerate(bboxs):
        for j in range(i + 1, len(bboxs) - i):
            if bbox == bboxs[j]:
                err_msg = (f"Duplicate bounding box with corners ({bbox[0]}, {bbox[1]}), ({bbox[2]}, "
                           f"{bbox[3]}) in the input bounding boxes!")
                application.logger.error(err_msg)
                abort(400, err_msg)
        for obbox in old_bboxs:
            if (bbox[0] == obbox['tlx'] and bbox[1] == obbox['tly'] and bbox[2] == obbox['brx'] and
                    bbox[3] == obbox['bry']):
                err_msg = f"Duplicate bounding box with corners ({bbox[0]}, {bbox[1]}), ({bbox[2]}, {bbox[3]})!"
                application.logger.error(err_msg)
                abort(400, err_msg)
    feat_id = ex_feature['_id']
    response = VisualFeatureDAO().push_bboxs(feat_id, bboxs, generate_response=True)
    application.logger.info(f"Added {len(bboxs)} new bounding boxes to visual feature {str(feat_id)} !")
    return response
