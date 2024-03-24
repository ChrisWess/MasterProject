from flask import request, abort

from app import application
from app.db.daos.corpus_dao import CorpusDAO


@application.route('/corpus', methods=['GET'])
def find_words():
    return CorpusDAO().find_all(projection=request.args, generate_response=True)


@application.route('/corpus/adjective', methods=['GET'])
def find_adjectives():
    args = request.args
    corpus = CorpusDAO()
    if 'limit' in args:
        corpus.limit(int(args['limit']))
    return corpus.find_all_adjectives(projection=args, generate_response=True)


@application.route('/corpus/noun', methods=['GET'])
def find_nouns():
    args = request.args
    corpus = CorpusDAO()
    if 'limit' in args:
        corpus.limit(int(args['limit']))
    return corpus.find_all_nouns(projection=args, generate_response=True)


@application.route('/corpus', methods=['POST'])
def find_corpus_word_or_add():
    args = request.json
    if "word" not in args or "isNoun" not in args:
        err_msg = 'Your request body must contain the key-value pairs with keys "word" and "isNoun"!'
        application.logger.error(err_msg)
        abort(400, err_msg)
    return CorpusDAO().find_doc_or_add(args['word'], args['isNoun'], args.get('lemma', None),
                                       args.get('stem', None), generate_response=True)
