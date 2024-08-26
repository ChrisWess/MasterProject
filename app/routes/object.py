from json import loads

from bson import ObjectId
from bson.errors import InvalidId
from flask import request, abort, session, make_response, send_file
from flask_login import login_required

from app import application
from app.db.daos.label_dao import LabelDAO
from app.db.daos.object_dao import ObjectDAO
from app.db.daos.vis_feature_dao import VisualFeatureDAO


@application.route('/object', methods=['GET'])
def find_objects():
    return ObjectDAO().find_all(projection=request.args, generate_response=True)


@application.route('/object/count', methods=['GET'])
def count_objects():
    return ObjectDAO().total_doc_count(generate_response=True)


@application.route('/object/<object_id>', methods=['GET'])
def find_object_by_id(object_id):
    try:
        obj = ObjectDAO().find_by_nested_id(ObjectId(object_id), projection=request.args, generate_response=True)
        if obj is None:
            err_msg = "No object with the given ID could be found!"
            application.logger.error(err_msg)
            abort(404, err_msg)
        else:
            return obj
    except InvalidId:
        err_msg = "The Detected Object ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/object/idoc/<doc_id>', methods=['GET'])
def find_objects_of_imgdoc(doc_id):
    try:
        return ObjectDAO().find_by_id(ObjectId(doc_id), projection=request.args, generate_response=True)
    except InvalidId:
        err_msg = "The Image Document ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


def get_objects_of_user(user_id):
    try:
        return ObjectDAO().find_by_creator(ObjectId(user_id), projection=request.args, generate_response=True)
    except InvalidId:
        err_msg = "The Detected Object ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/object/img/<object_id>', methods=['GET'])
def get_object_image_crop(object_id=None):
    try:
        image = ObjectDAO().find_object_img(ObjectId(object_id))
        if image is None:
            err_msg = f"No object with ID {object_id} could be found!"
            application.logger.error(err_msg)
            abort(404, err_msg)
        response = make_response(send_file(image, mimetype='image/jpeg'))
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except InvalidId:
        err_msg = "The Object ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/object/current/', methods=['GET'])
@login_required
def find_objects_of_current_user():
    user_id = session.get("userid", default=None)
    if user_id is None:
        err_msg = "Logged in user could not be found!"
        application.logger.error(err_msg)
        abort(400, err_msg)
    return get_objects_of_user(user_id)


@application.route('/object/user/<user_id>', methods=['GET'])
def find_objects_of_user(user_id=None):
    return get_objects_of_user(user_id)


@application.route('/object', methods=['POST'])
def add_detected_object():
    args = request.json
    if 'docId' not in args:
        err_msg = 'Your request body must contain the key-value pair "docId"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    # checks for "label" or "labelId" and bbox values "bboxTlx", "bboxTly", "bboxBrx", "bboxBry"
    doc_id, label_info, bbox = ObjectDAO.retrieve_insert_args(request.json, label_projection='_id')
    try:
        response = ObjectDAO().add(doc_id, label_info, bbox, generate_response=True)
        new_id = response['result']
        application.logger.info("Detected object inserted: " + new_id)
        response['result'] = {'objId': new_id, 'labelId': str(label_info)}
        return response
    except InvalidId:
        err_msg = "The Image Document ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/object/annotated', methods=['POST'])
def add_annotated_object():
    args = request.json
    if 'annotation' not in args != 'annotations' not in args:  # logical XOR
        err_msg = 'Your request body must contain either the key-value pair "annotation" or "annotations"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    if 'annotation' in args:
        annotations = args['annotation']
    else:
        annotations = args['annotations']
        if isinstance(annotations, str):
            annotations = loads(annotations)
    doc_id, label_info, bbox = ObjectDAO.retrieve_insert_args(request.json, label_projection='_id')
    try:
        response = ObjectDAO().add(doc_id, label_info, bbox, annotations, generate_response=True)
        application.logger.info("Detected object inserted: " + response['result'])
        return response
    except InvalidId:
        err_msg = "The Image Document ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/object', methods=['PUT'])
def update_bbox_validated():
    args = request.json
    if 'objectId' not in args or 'bbox' not in args:
        err_msg = 'Your request body must contain the key-value pairs "objectId" and "bbox"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    try:
        object_id = ObjectId(args['objectId'])
    except InvalidId:
        err_msg = "The Detected Object ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    bbox = args['bbox']
    assert len(bbox) == 4
    prev_bbox = ObjectDAO().find_bbox_by_id(object_id)
    delta_x = bbox[0] - prev_bbox['tlx']
    delta_y = bbox[1] - prev_bbox['tly']
    vis_feats = VisualFeatureDAO().find_by_object(object_id, projection=('annotationId', 'bboxs'))
    if vis_feats is None:
        err_msg = "The Detected Object ID you provided could not be found!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    elif len(vis_feats) > 0:
        # if any visual features suddenly fall outside the new boundaries, abort!
        for feat in vis_feats:
            try:
                VisualFeatureDAO.validate_bboxs_fit_into_parent(feat['bboxs'], bbox)
            except ValueError:
                err_msg = (f"The Visual Feature with ID {feat['_id']} of Annotation {feat['annotationId']} would exceed"
                           f" the boundaries of the new Bounding Box for the Detected Object you provided on "
                           f"execution of the update! Please Update all such Visual Features to fit into the desired"
                           f" Bounding Box before executing this function. Aborting the Update...")
                application.logger.error(err_msg)
                abort(400, err_msg)
        VisualFeatureDAO().reposition_bboxs_of_object(object_id, delta_x, delta_y)
    return ObjectDAO().update_bbox(object_id, bbox, generate_response=True)


@application.route('/object/replace', methods=['PUT'])
def replace_objects():
    # TODO: create
    pass


@application.route('/object/label', methods=['PUT'])
def update_object_label():
    args = request.json
    if 'objectId' not in args or 'labelId' not in args:
        err_msg = 'Your request body must contain the key-value pairs "objectId" and "labelId"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    try:
        object_id = ObjectId(args['objectId'])
    except InvalidId:
        err_msg = "The Detected Object ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    try:
        label_id = ObjectId(args['labelId'])
    except InvalidId:
        err_msg = "The Label ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    return ObjectDAO().update_label(object_id, label_id, generate_response=True)


@application.route('/object/label/new', methods=['POST'])
def update_to_new_label():
    args = request.json
    if 'objectId' not in args or 'label' not in args:
        err_msg = 'Your request body must contain the key-value pairs "objectId" and "label"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    if 'category' not in args != 'categories' not in args:
        err_msg = 'Your request body must contain either the key-value pair "category" or "categories"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    if 'category' in args:
        categories = args['category']
    else:
        categories = args['categories']
    if not categories:
        err_msg = "Provide at least one basic category for an object label!"
        application.logger.error(err_msg)
        abort(400, err_msg)
    try:
        object_id = ObjectId(args['objectId'])
    except InvalidId:
        err_msg = "The Detected Object ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    label_id = LabelDAO().add(args['label'], categories)[1]['_id']
    return ObjectDAO().update_label(object_id, label_id, generate_response=True)


@application.route('/object/<object_id>', methods=['DELETE'])
def delete_object_by_id(object_id):
    try:
        response = ObjectDAO().delete_nested_doc_by_id(ObjectId(object_id), generate_response=True)
        # TODO: delete visual features of the object (in all deletion methods)
        application.logger.info(f"Detected object with ID {object_id} has been deleted")
        return response
    except InvalidId:
        err_msg = "The Detected Object ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/object/creator/<creator_id>', methods=['DELETE'])
def delete_all_objects_from_creator(creator_id):
    try:
        return ObjectDAO().delete_all_by_creator(ObjectId(creator_id), generate_response=True)
    except InvalidId:
        err_msg = "The User ID of the creator you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
