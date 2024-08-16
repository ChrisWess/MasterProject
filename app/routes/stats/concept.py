from operator import itemgetter

import numpy as np
from bson import ObjectId
from bson.errors import InvalidId
from flask import request, abort

from app import application
from app.db.stats.daos.anno_concept_stats import ConceptTfIdfDAO, DocConceptCountVectorizerDAO, ConceptOccurrenceDAO, \
    ImageConceptCountVectorizerDAO


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


@application.route('/stats/concept/count', methods=['GET'])
def count_concepts_by_label():
    return DocConceptCountVectorizerDAO().find_top_concepts_with_info(generate_response=True)


@application.route('/stats/concept/imageConcepts', methods=['PUT'])
def force_vectorize_image_concept_update():
    # TODO: make sure removed images are deleted from stats
    ImageConceptCountVectorizerDAO().update(force_update=True)
    return 'Updated Stats!'


@application.route('/stats/concept/tfIdf2/label/<label_id>', methods=['GET'])
def find_concept_tf_idfs2(label_id):
    word_dao = DocConceptCountVectorizerDAO()
    try:
        count_list = word_dao.find_by_label(ObjectId(label_id))
    except InvalidId:
        err_msg = "The Label ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    total_docs = word_dao.count_total_labels()
    doc_dao = ConceptOccurrenceDAO()
    # doc_dao.update()
    total = 0
    for i, (concept, count) in enumerate(count_list):
        total += count
        num_occurs = doc_dao.find_stats_by_id(concept)["occurrenceCount"]
        idf = np.log(total_docs / num_occurs)
        count_list[i] = (str(concept), count * idf)
    count_list.sort(key=itemgetter(1), reverse=True)
    for i, (concept, res) in enumerate(count_list):
        count_list[i] = (concept, res / total)
    return {'result': count_list[:20]}
