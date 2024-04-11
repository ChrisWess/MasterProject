from bson import ObjectId
from bson.errors import InvalidId
from flask import request, abort

from app import application
from app.db.stats.daos.anno_word_stats import CorpusTfIdfDAO


@application.route('/stats/corpus/tfIdf', methods=['GET'])
def find_corpus_tf_idfs():
    args = request.args
    limit = None
    if 'limit' in args:
        limit = int(args['limit'])
    return CorpusTfIdfDAO().find_all_stats(generate_response=True, limit=limit)


@application.route('/stats/corpus/adj/tfIdf/label/<label_id>', methods=['GET'])
def find_adjective_tf_idfs_by_label(label_id):
    args = request.args
    try:
        if 'limit' in args:
            limit = int(args['limit'])
            return CorpusTfIdfDAO().find_top_adjectives_by_label(ObjectId(label_id), limit, generate_response=True)
        else:
            return CorpusTfIdfDAO().find_top_adjectives_by_label(ObjectId(label_id), generate_response=True)
    except InvalidId:
        err_msg = "The Label ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/stats/corpus/noun/tfIdf/label/<label_id>', methods=['GET'])
def find_noun_tf_idfs_by_label(label_id):
    args = request.args
    try:
        if 'limit' in args:
            limit = int(args['limit'])
            return CorpusTfIdfDAO().find_top_nouns_by_label(ObjectId(label_id), limit, generate_response=True)
        else:
            return CorpusTfIdfDAO().find_top_nouns_by_label(ObjectId(label_id), generate_response=True)
    except InvalidId:
        err_msg = "The Label ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/stats/corpus/tfIdf', methods=['PUT'])
def force_corpus_tf_idfs_update():
    return CorpusTfIdfDAO().update(force_update=True, generate_response=True)
