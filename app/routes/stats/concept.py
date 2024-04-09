from bson import ObjectId
from bson.errors import InvalidId
from flask import request, abort

from app import application
from app.db.stats.daos.anno_concept_stats import ConceptTfIdfDAO


@application.route('/stats/concept/tfIdf', methods=['GET'])
def find_concept_tf_idfs():
    args = request.args
    limit = None
    if 'limit' in args:
        limit = int(args['limit'])
    return ConceptTfIdfDAO().find_all_stats(generate_response=True, limit=limit)


@application.route('/stats/concept/tfIdf/label/<label_id>', defaults={'page_idx': 0})
@application.route('/stats/concept/tfIdf/label/<label_id>/<path:page_idx>', methods=['GET'])
def find_concept_tf_idfs_by_label(label_id, page_idx):
    try:
        return ConceptTfIdfDAO().find_top_by_label(ObjectId(label_id), int(page_idx), generate_response=True)
    except InvalidId:
        err_msg = "The Label ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/stats/concept/tfIdf', methods=['PUT'])
def force_concept_tf_idfs_update():
    return ConceptTfIdfDAO().update(force_update=True, generate_response=True)
