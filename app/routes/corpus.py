from flask import request

from app import application
from app.db.daos.corpus_dao import CorpusDAO


@application.route('/corpus', methods=['GET'])
def find_words():
    return CorpusDAO().find_all(projection=request.args, generate_response=True)
