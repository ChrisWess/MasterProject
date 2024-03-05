from bson import ObjectId
from bson.errors import InvalidId
from flask import request, abort

from app import application
from app.db.daos.image_doc_dao import ImgDocDAO
from app.db.daos.project_dao import ProjectDAO
from app.db.daos.user_dao import UserDAO
from app.db.daos.work_history_dao import WorkHistoryDAO


@application.route('/project', methods=['GET'])
def find_all_projects():
    return ProjectDAO().find_all(projection=request.args, generate_response=True)


@application.route('/project/<project_id>', methods=['GET'])
def find_project_by_id(project_id):
    try:
        response = ProjectDAO().find_by_id(ObjectId(project_id), projection=request.args, generate_response=True)
        if response is None:
            err_msg = "No Project with the given ID could be found!"
            application.logger.error(err_msg)
            abort(404, err_msg)
        else:
            return response
    except InvalidId:
        err_msg = "The Project ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/project/fromUser/<title>', methods=['GET'])
def find_project_by_my_project_title(title):
    user_id = UserDAO().get_current_user_id()
    response = ProjectDAO().find_by_users_project_title_with_stats(user_id, title, projection=request.args,
                                                                   generate_response=True)
    if response is None:
        err_msg = f'No Project with the title "{title}" could be found for User {user_id}!'
        application.logger.error(err_msg)
        abort(404, err_msg)
    else:
        return response


@application.route('/project/fromUser', methods=['GET'])
def find_all_projects_by_current_user():
    user_id = UserDAO().get_current_user_id()
    return ProjectDAO().find_all_of_user_with_progress(user_id, projection=request.args, generate_response=True)


@application.route('/project/<project_id>/randfetch', defaults={'num_res': 1})
@application.route('/project/<project_id>/randfetch/<path:num_res>', methods=['GET'])
def randomly_fetch_new_idocs(project_id, num_res):
    try:
        return ProjectDAO().random_fetch(ObjectId(project_id), int(num_res), projection=request.args,
                                         generate_response=True)
    except InvalidId:
        err_msg = "The Project ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/project/<project_id>/idoc/<doc_id>/simplefetch', defaults={'num_res': 1})
@application.route('/project/<project_id>/idoc/<doc_id>/simplefetch/<path:num_res>', methods=['GET'])
def fetch_next_idocs_simple(project_id, doc_id, num_res):
    num_res = int(num_res)
    if num_res == 0:
        return {'status': 200, 'result': [], 'numResults': 0}
    try:
        doc_id = ObjectId(doc_id)
    except InvalidId:
        err_msg = "The Image Document ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    try:
        result = ProjectDAO().find_new_doc_slice(ObjectId(project_id), ObjectId(doc_id), num_res,
                                                 projection=request.args, generate_response=True)
        if result is None:
            err_msg = ("Either the Project ID you provided does not exist or the Image Document ID you provided "
                       "does not exist or does not belong to the specified Project!")
            application.logger.error(err_msg)
            abort(404, err_msg)
        return result
    except InvalidId:
        err_msg = "The Project ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/project/<project_id>/idoc/<doc_id>/sortedfetch', defaults={'num_res': 1})
@application.route('/project/<project_id>/idoc/<doc_id>/sortedfetch/<path:num_res>', methods=['GET'])
def fetch_next_idoc_ids_sorted(project_id, doc_id, num_res):
    # TODO: add possibility to sort the documents of a project by some filter.
    #   Queries should be identical to load_thumbnails_paginated, because the
    #   Project Main Page will then show the images in the same order as we navigate
    #   through them.
    try:
        doc_id = ObjectId(doc_id)
    except InvalidId:
        err_msg = "The Image Document ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    try:
        # result = ProjectDAO().find_new_doc_slice(ObjectId(project_id), ObjectId(doc_id), int(num_res))
        result = 'TODO'
        if result is None:
            err_msg = ("Either the Project ID you provided does not exist or the Image Document ID you provided "
                       "does not exist or does not belong to the specified Project!")
            application.logger.error(err_msg)
            abort(404, err_msg)
        return result
    except InvalidId:
        err_msg = "The Project ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/project/<project_id>/fetchHistory', defaults={'num_res': 1})
@application.route('/project/<project_id>/fetchHistory/<path:num_res>', methods=['GET'])
def find_users_work_history_in_project(project_id, num_res):
    try:
        project_id = ObjectId(project_id)
    except InvalidId:
        err_msg = "The Project ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    user_id = UserDAO().get_current_user_id()
    doc_ids = WorkHistoryDAO().find_worker_history_by_project(user_id, project_id, num_res,
                                                              projection='docId', get_cursor=True)
    doc_ids = [doc['docId'] for doc in doc_ids]
    return ImgDocDAO().find_many_retain_order(doc_ids, projection=request.args, generate_response=True)


@application.route('/project/full', defaults={'depth': 1})
@application.route('/project/full/<path:depth>', methods=['GET'])
def unroll_project_data(depth):
    return ProjectDAO().unrolled(int(depth), projection=request.args, generate_response=True)


@application.route('/project/<project_id>/thumbnail/<int:page_idx>', methods=['GET'])
def get_project_thumbnail_page(project_id, page_idx):
    try:
        return ImgDocDAO().load_thumbnails_paginated(page_idx, ObjectId(project_id),
                                                     sort_by=request.args, generate_response=True)
    except InvalidId:
        err_msg = "The Project ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/project/<project_id>/thumbnail/search/<int:page_idx>', methods=['GET'])
def search_project_thumbnails(project_id, page_idx):
    args = request.args
    if 'search' in args:
        try:
            return ImgDocDAO().search_thumbnails(page_idx, args['search'], ObjectId(project_id), generate_response=True)
        except InvalidId:
            err_msg = "The Project ID you provided is not a valid ID!"
            application.logger.error(err_msg)
            abort(404, err_msg)
    else:
        err_msg = "Please supply a search parameter with your request!"
        application.logger.error(err_msg)
        abort(400, err_msg)


@application.route('/project', methods=['PUT'])
def add_img_to_project():
    args = request.json
    if "projectId" not in args or "docId" not in args:
        err_msg = 'Your request body must contain the key-value pairs "projectId" and "docId"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    try:
        project_id = ObjectId(args["projectId"])
    except InvalidId:
        err_msg = "The Project ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    try:
        doc_id = ObjectId(args["docId"])
    except InvalidId:
        err_msg = "The Image Document ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    response = ProjectDAO().add_idoc_to_project(project_id, doc_id, generate_response=True)
    if response['numUpdated'] == 0:
        err_msg = f"No project with ID {project_id} could be found!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    else:
        application.logger.info(f"Added Image Document {doc_id} to Project {project_id}!")
        return response


@application.route('/project/idoc', methods=['PUT'])
def remove_img_from_project():
    args = request.json
    if "projectId" not in args or "docId" not in args:
        err_msg = 'Your request body must contain the key-value pairs "projectId" and "docId"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    try:
        project_id = ObjectId(args["projectId"])
    except InvalidId:
        err_msg = "The Project ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    try:
        doc_id = ObjectId(args["docId"])
    except InvalidId:
        err_msg = "The Image Document ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    delete_flag = args.get("deleteFlag", True)
    response = ProjectDAO().remove_idoc_from_project(project_id, doc_id, delete_flag, generate_response=True)
    if response is None or response['numUpdated'] == 0:
        err_msg = f"The Image Document with ID {doc_id} is not assigned to Project {project_id}!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    else:
        application.logger.info(f"Removed Image Document {doc_id} from Project {project_id}!")
        return response


@application.route('/project', methods=['POST'])
def add_project():
    args = request.json
    if "title" not in args:
        err_msg = 'Your request body must contain the key-value pair "title"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    desc = args.get('desc', None)
    tags = args.get('tags')
    if type(tags) is str:
        tags = [tags]
    membs = args.get('members')
    if type(membs) is str:
        membs = [membs]
    try:
        response = ProjectDAO().add(args["title"], desc, tags, membs, generate_response=True)
        application.logger.info("Project created: " + response['result'])
        return response
    except InvalidId:
        err_msg = "A User ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/project/title', methods=['PUT'])
def rename_project():
    args = request.json
    if "projectId" not in args or "title" not in args:
        err_msg = 'Your request body must contain the key-value pairs "projectId" and "title"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    title = args["title"]
    proj_id = args["projectId"]
    try:
        response = ProjectDAO().rename(ObjectId(proj_id), title, generate_response=True)
        application.logger.info(f"Project {proj_id} renamed to: {title}")
        return response
    except InvalidId:
        err_msg = "The Project ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/project/member', methods=['PUT'])
def add_member_to_project():
    args = request.json
    if "projectId" not in args or "userEmail" not in args:
        err_msg = 'Your request body must contain the key-value pairs "projectId" and "userId"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    proj_id = args['projectId']
    email = args['userEmail']
    try:
        response = ProjectDAO().add_member(ObjectId(proj_id), email, generate_response=True)
    except InvalidId:
        err_msg = "The Project ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    if response is None:
        err_msg = "No existing User with the provided E-Mail!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    application.logger.info(f"User {email} was added as new member to Project {proj_id}")
    return response


@application.route('/project', methods=['DELETE'])
def delete_all_projects():
    return ProjectDAO().delete_all_cascade(generate_response=True)


@application.route('/project/<project_id>', methods=['DELETE'])
def delete_project_by_id(project_id):
    try:
        return ProjectDAO().delete_by_id_cascade(ObjectId(project_id), generate_response=True)
    except InvalidId:
        err_msg = "The Project ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
