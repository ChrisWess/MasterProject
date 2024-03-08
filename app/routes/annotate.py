from bson import ObjectId
from bson.errors import InvalidId
from flask import request, abort

from app import application
from app.db.daos.annotation_dao import AnnotationDAO
from app.db.daos.image_doc_dao import ImgDocDAO


@application.route('/annotation', methods=['GET'])
def find_all_annotations():
    return AnnotationDAO().find_all(projection=request.args, generate_response=True)


@application.route('/annotation/search', methods=['GET'])
# @login_required
def search_in_annotations():
    query = request.args['query']
    return AnnotationDAO().search_annotations(query, projection=request.args, generate_response=True)


@application.route('/annotation/withConcepts', methods=['GET'])
def find_unrolled_annotations_with_concepts():
    return AnnotationDAO().unrolled(projection=request.args, generate_response=True)


@application.route('/annotation/annotator/<annotator_id>', methods=['GET'])
# @login_required
def find_by_annotator(annotator_id):
    try:
        return AnnotationDAO().find_by_annotator(ObjectId(annotator_id), projection=request.args,
                                                 generate_response=True)
    except InvalidId:
        err_msg = "The user ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/annotation/<annotation_id>', methods=['GET'])
# @login_required
def find_annotation_by_id(annotation_id):
    try:
        result = AnnotationDAO().find_by_nested_id(ObjectId(annotation_id), projection=request.args,
                                                   generate_response=True)
        if result is None:
            err_msg = "No annotation with the given ID could be found!"
            application.logger.error(err_msg)
            abort(404, err_msg)
        return result
    except InvalidId:
        err_msg = "The annotation ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/annotation/idoc/<doc_id>', methods=['GET'])
def find_annotations_by_image(doc_id):
    try:
        return AnnotationDAO().find_by_id(ObjectId(doc_id), projection=request.args, generate_response=True)
    except InvalidId:
        err_msg = "The Annotation ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/annotation/annotator/<annotator_id>', methods=['DELETE'])
def delete_annotations_by_annotator(annotator_id):
    try:
        return AnnotationDAO().delete_all_by_annotator(ObjectId(annotator_id), generate_response=True)
    except InvalidId:
        err_msg = "The User ID of the annotator you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/annotation/<anno_id>', methods=['DELETE'])
def delete_annotation_by_id(anno_id):
    try:
        return AnnotationDAO().delete_nested_doc_by_id(ObjectId(anno_id), generate_response=True)
    except InvalidId:
        err_msg = "The Annotation ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/annotation/idoc/<doc_id>', methods=['DELETE'])
def delete_annotations_by_doc_id(doc_id):
    try:
        return AnnotationDAO().delete_all_nested_at_id(ObjectId(doc_id), generate_response=True)
    except InvalidId:
        err_msg = "The Image Document ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/annotation', methods=['POST'])
# @login_required
def annotate():
    args = request.json
    if "annotation" not in args or "objectId" not in args:
        err_msg = 'Your request body must contain the key-value pairs with keys "annotation" and "objectId"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    try:
        object_id = args["objectId"]
        obj_id = ObjectId(object_id)
        obj = ImgDocDAO().find_by_object(obj_id, projection=('projectId', 'objects.labelId'))
        if obj is None:
            err_msg = "No object with the given ID could be found!"
            application.logger.error(err_msg)
            abort(404, err_msg)
        response = AnnotationDAO().add(obj_id, args["annotation"], obj['_id'],
                                       obj['objects']['labelId'], obj['projectId'], generate_response=True)
        application.logger.info(f"Added new annotation {response['result']} to object {object_id} !")
        return response
    except InvalidId:
        err_msg = "The object ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/annotation', methods=['PUT'])
def update_concept():
    args = request.json
    if "annoId" not in args or "tokenStart" not in args or "tokenEnd" not in args:
        err_msg = 'Your request body must contain the key-value pairs with keys "annoId", "tokenStart" and "tokenEnd"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    try:
        anno_id = ObjectId(args["annoId"])
        response = AnnotationDAO().add_or_update_concept_at_range(anno_id,
                                                                  (args["tokenStart"], args["tokenEnd"]),
                                                                  generate_response=True)
        if response is None:
            err_msg = "The concept could not be analysed correctly! No noun phrase found!"
            application.logger.error(err_msg)
            abort(400, err_msg)
        return response
    except InvalidId:
        err_msg = "The Annotation ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
