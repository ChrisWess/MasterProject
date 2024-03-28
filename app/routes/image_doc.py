from io import BytesIO
from json import loads

from bson import ObjectId
from bson.errors import InvalidId
from flask import request, abort, flash, redirect, send_file, make_response
from werkzeug.utils import secure_filename

from app import application, ALLOWED_FILE_EXTS
from app.db.daos.image_doc_dao import ImgDocDAO
from app.db.daos.project_dao import ProjectDAO


@application.route('/idoc', methods=['GET'])
def find_docs():
    args = request.args
    img_dao = ImgDocDAO()
    if 'limit' in args:
        img_dao.limit(int(args['limit']))
    return img_dao.find_all(projection=args, generate_response=True)


@application.route('/idoc/full', defaults={'depth': 1}, methods=['GET'])
@application.route('/idoc/full/<path:depth>', methods=['GET'])
def unroll_complete_image_document_data(depth):
    return ImgDocDAO().unrolled(int(depth), projection=request.args, generate_response=True)


@application.route('/idoc/img/<doc_id>', methods=['GET'])
def get_image(doc_id=None):
    try:
        image = ImgDocDAO().load_image(ObjectId(doc_id))
        if image is None:
            err_msg = f"No image with ID {doc_id} could be found!"
            application.logger.error(err_msg)
            abort(404, err_msg)
        image = BytesIO(image)
        response = make_response(send_file(image, mimetype='image/jpeg'))
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    except InvalidId:
        err_msg = "The Image Document ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/idoc/thumbnail', methods=['GET'])
def get_thumbnails():
    return ImgDocDAO().load_thumbnails(sort_by=request.args, generate_response=True)


@application.route('/idoc/thumbnail/<int:page_idx>', methods=['GET'])
def get_thumbnail_page(page_idx):
    return ImgDocDAO().load_thumbnails_paginated(page_idx, sort_by=request.args, generate_response=True)


@application.route('/idoc/<doc_id>', methods=['GET'])
def find_doc_by_id(doc_id=None):
    try:
        doc = ImgDocDAO().find_by_id(ObjectId(doc_id), projection=request.args, generate_response=True)
        if doc is None:
            err_msg = "No image document with the given ID could be found!"
            application.logger.error(err_msg)
            abort(404, err_msg)
        else:
            return doc
    except InvalidId:
        err_msg = "The Image Document ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/idoc/name/<doc_name>', methods=['GET'])
def find_docs_by_name(doc_name):
    return ImgDocDAO().find_by_name(doc_name, projection=request.args, generate_response=True)


@application.route('/idoc/object/<object_id>', methods=['GET'])
def find_doc_with_object(object_id):
    try:
        doc = ImgDocDAO().find_by_object(ObjectId(object_id), projection=request.args, generate_response=True)
        if doc is None:
            err_msg = "No object with the given ID could be found!"
            application.logger.error(err_msg)
            abort(404, err_msg)
        else:
            return doc
    except InvalidId:
        err_msg = "The Object ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/idoc/annotation/<annotation_id>', methods=['GET'])
def find_doc_with_annotation(annotation_id):
    try:
        doc = ImgDocDAO().find_by_annotation(ObjectId(annotation_id), projection=request.args, generate_response=True)
        if doc is None:
            err_msg = "No annotation with the given ID could be found!"
            application.logger.error(err_msg)
            abort(404, err_msg)
        else:
            return doc
    except InvalidId:
        err_msg = "The Annotation ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/idoc/annotation', methods=['GET'])
def search_doc_with_matching_substring_in_annotation():
    query = request.args['query']
    return ImgDocDAO().search_in_annotations(query, projection=request.args, generate_response=True)


@application.route('/idoc/<doc_id>', methods=['DELETE'])
def delete_doc_by_id(doc_id):
    # TODO: remove this doc from its project(s)
    try:
        response = ImgDocDAO().delete_by_id(ObjectId(doc_id), generate_response=True)
        application.logger.info(f"ImgDoc with ID {doc_id} has been deleted")
        return response
    except InvalidId:
        err_msg = "The Image Document ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_FILE_EXTS


@application.route('/idoc', methods=['POST'])
def add_image():
    form = request.form
    files = request.files
    if "name" not in form or "image" not in files:
        err_msg = 'Your request form must contain the key-value pair "name" and a file with key "image"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    file = files.get("image")
    fname = file.filename
    if fname == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(fname):
        filename = secure_filename(fname)
        proj_id = form.get('projectId', None)
        if proj_id:
            try:
                proj_id = ObjectId(proj_id)
            except InvalidId:
                err_msg = "The Project ID you provided is not a valid ID!"
                application.logger.error(err_msg)
                abort(404, err_msg)
        detect_objects = form.get('detectObjects', True)
        response = ImgDocDAO().add(form["name"], filename, file.read(), proj_id,
                                   detect_objs=detect_objects, generate_response=True)
        doc_id = response['result']
        if proj_id:
            ProjectDAO().add_idoc_to_project(proj_id, ObjectId(doc_id), False)
            application.logger.info(f"Image {doc_id} inserted into project {proj_id}")
        else:
            application.logger.info("Image inserted: " + doc_id)
        return response
    else:
        err_msg = 'The name of the uploaded file indicates that you uploaded the wrong (image) file format!'
        application.logger.error(err_msg)
        abort(400, err_msg)


@application.route('/idoc/annotated', methods=['POST'])
def add_annotated_image():
    form = request.form
    files = request.files
    if "image" not in files or "name" not in form or "objects" not in form:
        err_msg = 'Your request form must contain the key-value pairs "name", "objects" and a file with key "image"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    file = files.get("image")
    fname = file.filename
    if fname == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(fname):
        filename = secure_filename(fname)
        objects = form['objects']
        if isinstance(objects, str):
            objects = loads(objects)
        proj_id = form.get('projectId', None)
        if proj_id:
            try:
                proj_id = ObjectId(proj_id)
            except InvalidId:
                err_msg = "The Project ID you provided is not a valid ID!"
                application.logger.error(err_msg)
                abort(404, err_msg)
        response = ImgDocDAO().add(form["name"], filename, file.read(), proj_id, objects, generate_response=True)
        doc_id = response['result']
        if proj_id:
            ProjectDAO().add_idoc_to_project(proj_id, ObjectId(doc_id), False)
        application.logger.info("Image inserted: " + doc_id)
        return response
    else:
        err_msg = 'The name of the uploaded file indicates that you uploaded the wrong (image) file format!'
        application.logger.error(err_msg)
        abort(400, err_msg)


@application.route('/idoc/<doc_id>/detection', methods=['POST'])
def detect_objects_in_image(doc_id=None):
    args = request.json
    try:
        return ImgDocDAO().detect_objects_for_image(ObjectId(doc_id), classes=args.get('classes', None),
                                                    generate_response=True)
    except InvalidId:
        err_msg = "The Image Document ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/idoc', methods=['PUT'])
def update_img():
    form = request.form.to_dict()
    if "docId" not in form or "newImg" not in form:
        err_msg = 'Your request body must contain all key-value pairs with keys "docId" and "newImg"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    try:
        doc_id = ObjectId(form["docId"])
        img = form["newImg"]
        response = ImgDocDAO().update_image(doc_id, img, generate_response=True)
        application.logger.info(f"Image of ImgDoc with ID {doc_id} has been updated")
        return response
    except InvalidId:
        err_msg = "The Image Document ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/idoc/rename', methods=['PUT'])
def rename_doc():
    args = request.json
    if "docId" not in args or "docName" not in args:
        err_msg = 'Your request body must contain all key-value pairs with keys "docId" and "docName"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    try:
        doc_id = ObjectId(args["docId"])
        name = args["docName"]
        response = ImgDocDAO().rename_doc(doc_id, name, generate_response=True)
        application.logger.info(f"ImgDoc with ID {doc_id} has been renamed to {name}")
        return response
    except InvalidId:
        err_msg = "The Image Document ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/idoc', methods=['DELETE'])
def purge_images():
    application.logger.info(f"Removed all Image Documents!")
    # TODO: remove all docIds from all projects
    return ImgDocDAO().delete_all(generate_response=True)
