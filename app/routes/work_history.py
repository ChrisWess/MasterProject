from bson import ObjectId
from bson.errors import InvalidId
from flask import request, abort
from pymongo.errors import OperationFailure

from app import application
from app.db.daos.project_dao import ProjectDAO
from app.db.daos.user_dao import UserDAO
from app.db.daos.work_history_dao import WorkHistoryDAO


@application.route('/workEntry/<entry_id>', methods=['GET'])
def find_entry_by_id(entry_id):
    try:
        entry = WorkHistoryDAO().find_by_id(ObjectId(entry_id), projection=request.args, generate_response=True)
        if entry is None:
            err_msg = "No Work Entry with the given ID could be found!"
            application.logger.error(err_msg)
            abort(404, err_msg)
        else:
            return entry
    except InvalidId:
        err_msg = "The Work Entry ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/workEntry/byUser', defaults={'user_id': None}, methods=['GET'])
@application.route('/workEntry/byUser/<path:user_id>', methods=['GET'])
def find_entries_by_user(user_id):
    if user_id is None:
        user_id = UserDAO().get_current_user_id()
    else:
        try:
            user_id = ObjectId(user_id)
        except InvalidId:
            err_msg = "The User ID you provided is not a valid ID!"
            application.logger.error(err_msg)
            abort(404, err_msg)
    return WorkHistoryDAO().find_worker_history_ordered(user_id, projection=request.args, generate_response=True)


@application.route('/workEntry/latest', methods=['GET'])
def find_users_most_recent_work():
    user_id = UserDAO().get_current_user_id()
    response = WorkHistoryDAO().find_workers_recent_task(user_id, projection=request.args, generate_response=True)
    if response is None:
        err_msg = "No work entries have been found for this User's profile!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    else:
        entry = response['result']
        proj_title = ProjectDAO().find_by_id(ObjectId(entry['projectId']), projection='title')['title']
        entry['projectTitle'] = proj_title
        return response


@application.route('/workEntry/idoc/<doc_id>/worker/<worker_id>', methods=['GET'])
def find_entry(doc_id, worker_id):
    try:
        doc_id = ObjectId(doc_id)
    except InvalidId:
        err_msg = "The Image Document ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    try:
        worker_id = ObjectId(worker_id)
    except InvalidId:
        err_msg = "The User ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    args = request.args
    unroll = args.get('unroll', None)
    if unroll is not None:
        unroll = int(unroll)
    entry = WorkHistoryDAO().find_entry(doc_id, worker_id, unroll, projection=args, generate_response=True)
    if entry is None:
        err_msg = "No Work Entry with the given ID could be found!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    else:
        return entry


@application.route('/workEntry', methods=['POST'])
def create_entry():
    try:
        args = request.json
        if "docId" not in args or "workerId" not in args:
            err_msg = 'Your request body must contain the key-value pairs "workerId" and "docId"!'
            application.logger.error(err_msg)
            abort(400, err_msg)
        try:
            doc_id = ObjectId(args["docId"])
        except InvalidId:
            err_msg = "The Image Document ID you provided is not a valid ID!"
            application.logger.error(err_msg)
            abort(404, err_msg)
        try:
            worker_id = ObjectId(args["workerId"])
        except InvalidId:
            err_msg = "The User ID you provided is not a valid ID!"
            application.logger.error(err_msg)
            abort(404, err_msg)
        proj_id = args.get('projectId', None)
        if proj_id:
            try:
                proj_id = ObjectId(proj_id)
            except InvalidId:
                err_msg = "The Project ID you provided is not a valid ID!"
                application.logger.error(err_msg)
                abort(404, err_msg)
        response = WorkHistoryDAO().add(doc_id, worker_id, proj_id, generate_response=True)
        application.logger.info("Work Entry inserted: " + response['result'])
        return response
    except OperationFailure as e:
        application.logger.error(str(e))
        abort(500)
    except ValueError as e:
        application.logger.error(str(e))
        abort(400, e)
