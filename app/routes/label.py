from json import loads

from bson import ObjectId
from bson.errors import InvalidId
from flask import request, abort
from pymongo.errors import OperationFailure

from app import application
from app.db.daos.label_dao import LabelDAO


@application.route('/label/all', methods=['GET'])
def find_all_labels():
    return LabelDAO().find_all(projection=request.args, generate_response=True)


@application.route('/label', methods=['GET'])
def find_labels_by_ids():
    args = request.args
    if 'ids' in args:
        ids = loads(args['ids'])
        try:
            for j, i in enumerate(ids):
                ids[j] = ObjectId(i)
            return LabelDAO().find_many(ids, projection=request.args, generate_response=True)
        except InvalidId:
            err_msg = "The Label ID you provided is not a valid ID!"
            application.logger.error(err_msg)
            abort(404, err_msg)
    else:
        err_msg = 'No Label IDs provided (parameter "ids")!'
        application.logger.error(err_msg)
        abort(400, err_msg)


@application.route('/label/search', methods=['GET'])
def search_labels():
    args = request.args
    if 'query' in args:
        return LabelDAO().perform_label_search(args['query'])
    else:
        err_msg = "Please supply a search parameter with your request!"
        application.logger.error(err_msg)
        abort(400, err_msg)


@application.route('/label/<label_id>', methods=['GET'])
def find_label_by_id(label_id):
    try:
        label = LabelDAO().find_by_id(ObjectId(label_id), projection=request.args, generate_response=True)
        if label is None:
            err_msg = "No label with the given ID could be found!"
            application.logger.error(err_msg)
            abort(404, err_msg)
        else:
            return label
    except InvalidId:
        err_msg = "The Label ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/label/name/<label>', methods=['GET'])
def find_label_by_name(label):
    label = LabelDAO().find_by_name(label, projection=request.args, generate_response=True)
    if label is None:
        err_msg = "No label with the given name could be found!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    else:
        return label


@application.route('/label/index/<int:label_idx>', methods=['GET'])
def find_label_by_index(label_idx):
    label = LabelDAO().find_by_index(label_idx, projection=request.args, generate_response=True)
    if label is None:
        err_msg = "No label with the given index could be found!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    else:
        return label


@application.route('/label/category/<category>', methods=['GET'])
def find_labels_by_category(category):
    return LabelDAO().find_by_category(category, projection=request.args, generate_response=True)


@application.route('/category', methods=['GET'])
def find_categories():
    args = request.args
    if args.get('onlyNames', True):
        return LabelDAO().category_names(generate_response=True)
    return LabelDAO().find_all_categories(args.get('expand', False), generate_response=True)


@application.route('/category/<category>/<label_id>', methods=['DELETE'])
def delete_category_from_label(category, label_id):
    delete_unref = request.args.get('deleteIfUnref', False)
    try:
        return LabelDAO().remove_category_from_label(category, label_id, delete_unref, True)
    except InvalidId:
        err_msg = "The Label ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/label', methods=['POST'])
def create_label():
    try:
        args = request.json
        if "name" not in args:
            err_msg = 'Your request body must contain the key-value pair with key "name"!'
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
        response = LabelDAO().add(args["name"], categories, generate_response=True)
        application.logger.info("Label inserted: " + response['result'])
        return response
    except OperationFailure as e:
        application.logger.error(str(e))
        abort(500)
    except ValueError as e:
        application.logger.error(str(e))
        abort(400, e)
