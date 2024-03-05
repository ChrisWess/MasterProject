from flask import request

from app import application
from app.db.daos.concept_dao import ConceptDAO


@application.route('/concept', methods=['GET'])
def find_concepts():
    return ConceptDAO().find_all(projection=request.args, generate_response=True)
