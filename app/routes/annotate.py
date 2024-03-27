from json import loads

from bson import ObjectId
from bson.errors import InvalidId
from flask import request, abort

from app import application
from app.db.daos.annotation_dao import AnnotationDAO
from app.db.daos.image_doc_dao import ImgDocDAO
from app.db.daos.user_dao import UserDAO


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


@application.route('/annotation/preprocess', methods=['GET'])
def get_preprocessed_annotation():
    args = request.args
    if 'annotation' not in args or "labelId" not in args:
        err_msg = 'Your query params must contain the key-value pairs with keys "annotation" and "labelId"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    try:
        return AnnotationDAO().process_annotation_text(args['annotation'], ObjectId(args['labelId']),
                                                       generate_response=True)
    except InvalidId:
        err_msg = "The Label ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/annotation/fromIdxs', methods=['GET'])
def get_annotation_from_corpus_idxs():
    args = request.args
    if 'corpusIdxs' not in args or "category" not in args:
        err_msg = 'Your query params must contain the key-value pairs with keys "corpusIdxs" and "category"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    user_id = UserDAO().get_current_user_id()
    word_idxs = loads(args['corpusIdxs'])
    assert all(type(idxs) is list for idxs in word_idxs)
    return AnnotationDAO().from_concepts(word_idxs, args['category'], user_id, generate_response=True)


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
    if 'annotation' not in args != 'annotations' not in args or "objectId" not in args:
        err_msg = ('Your request body must contain the key-value pairs with keys '
                   '"annotation" or "annotations" and "objectId"!')
        application.logger.error(err_msg)
        abort(400, err_msg)
    try:
        object_id = args["objectId"]
        obj_id = ObjectId(object_id)
        obj = ImgDocDAO().find_by_object(obj_id, projection=('projectId', 'objects.labelId'))
        if obj is None:
            err_msg = "No Detected Object with the given ID could be found!"
            application.logger.error(err_msg)
            abort(404, err_msg)
        if 'annotation' in args:
            response = AnnotationDAO().add(obj_id, args['annotation'], obj['objects'][0]['labelId'],
                                           obj['_id'], obj['projectId'], generate_response=True)
            application.logger.info(f"Added new annotation {response['result']} to object {object_id} !")
        else:
            annotations = args['annotations']
            if isinstance(annotations, str):
                annotations = loads(annotations)
            response = AnnotationDAO().add_many(obj_id, annotations, obj['_id'], obj['objects'][0]['labelId'],
                                                obj['projectId'], generate_response=True)
            application.logger.info(f"Added {response['numResults']} new annotations to object {object_id} !")
        return response
    except InvalidId:
        err_msg = "The Detected Object ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/annotation/full', methods=['POST'])
def push_new_annotation_entity():
    args = request.json
    if 'annotation' not in args or "objectId" not in args:
        err_msg = ('Your request body must contain the key-value pairs with keys '
                   '"annotation" or "annotations" and "objectId"!')
        application.logger.error(err_msg)
        abort(400, err_msg)
    try:
        object_id = args["objectId"]
        obj_id = ObjectId(object_id)
        obj = ImgDocDAO().find_by_object(obj_id, projection='projectId')
        if obj is None:
            err_msg = "No Detected Object with the given ID could be found!"
            application.logger.error(err_msg)
            abort(404, err_msg)
        annotation = args['annotation']
        cids = annotation['conceptIds']
        for i, cid in enumerate(cids):
            cids[i] = ObjectId(cid)
        response = AnnotationDAO().push_annotation(obj_id, obj['_id'], annotation,
                                                   obj['projectId'], generate_response=True)
        application.logger.info(f"Added new annotation {response['result']} to object {object_id} !")
        return response
    except InvalidId:
        err_msg = "The Detected Object ID you provided is not a valid ID!"
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


@application.route('/annotation/<anno_id>/removeConcept/<int:concept_idx>', methods=['DELETE'])
def remove_concept(anno_id, concept_idx):
    try:
        response = AnnotationDAO().remove_concept(ObjectId(anno_id), concept_idx, generate_response=True)
        if response is None:
            err_msg = "Operation failed! The provided concept index is not in the legal range of indices!"
            application.logger.error(err_msg)
            abort(400, err_msg)
        return response
    except InvalidId:
        err_msg = "The Annotation ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
