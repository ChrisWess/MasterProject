from bson import ObjectId
from bson.errors import InvalidId
from flask import request, abort

from app import application
from app.db.daos.concept_dao import ConceptDAO


@application.route('/concept', methods=['GET'])
def find_concepts():
    return ConceptDAO().find_all(projection=request.args, generate_response=True)


@application.route('/concept/<concept_id>', methods=['GET'])
def find_concept_by_id(concept_id):
    try:
        concept = ConceptDAO().find_by_id(ObjectId(concept_id), projection=request.args, generate_response=True)
        if concept is None:
            err_msg = "No Concept with the given ID could be found!"
            application.logger.error(err_msg)
            abort(404, err_msg)
        else:
            return concept
    except InvalidId:
        err_msg = "The Label ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
