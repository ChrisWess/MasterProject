from pymongo import ASCENDING

from app.autoxplain.base.tokenize import tokenizer
from app.db.daos.base import BaseDAO
from app.db.daos.manage_index import CorpusIndexManager
from app.db.models.corpus import CorpusWord
from app.db.models.payloads.corpus import WordPayload
from app.preproc.annotation import NounPhrase


class CorpusDAO(BaseDAO):
    __slots__ = "_word_search_content", "_uncased_word_search"

    def __init__(self):
        # Initialize mongodb collection of documents
        super().__init__("corpus", CorpusWord, WordPayload)
        self.create_index('corpus_index', ('index', ASCENDING))
        self.create_index('token_index', ('stem', ASCENDING), ('text', ASCENDING))
        self._word_search_content = {"$regex": None, "$options": 'im'}
        self._uncased_word_search = {"text": self._word_search_content}

        # TODO: add collection with inverted index for concepts
        #  (a concept corresponds to a document in the inverted index)

    def find_by_word(self, word_token, projection=None, generate_response=False, db_session=None):
        """
        Find the CorpusWord that has the given token assigned as its content
        :param word_token: string token of the word
        :param projection:
        :param generate_response:
        :param db_session:
        :return: CorpusWord that matches the given word
        """
        return self.simple_match("text", word_token, projection, generate_response, db_session, find_many=False)

    def find_by_word_uncased(self, word_token, db_session=None):
        """
        Find all CorpusWords that match the given token, ignoring capital letters
        :param word_token: string token of the word
        :param db_session:
        :return: CorpusWords that match the given string
        """
        # regex's anchored at the start (ie: starting with ^) are able to use indexes in the db
        self._word_search_content["$regex"] = '^' + word_token
        return list(self.collection.find(self._word_search_content, session=db_session))

    def find_by_lemma(self, lemma, projection=None, generate_response=False, db_session=None):
        """
        Find all CorpusWords with the given word lemma
        :param lemma: string token of the lemma (must be lower-case)
        :param projection:
        :param generate_response:
        :param db_session:
        :return: CorpusWord that matches the given lemma
        """
        return self.simple_match("lemma", lemma, projection, generate_response, db_session)

    def find_lemma_idx(self, lemma, db_session=None):
        """
        Find the index value that uniquely identifies each lemma
        :param lemma: string token of the stem (must be lower-case)
        :param db_session:
        :return: Integer index that represents the given stem
        """
        self._projection_dict['index'] = 1
        self._query_matcher["lemma"] = lemma
        result = self.collection.find(self._query_matcher, self._projection_dict, session=db_session).limit(1)
        try:
            result = result.next()['index']
        except StopIteration:
            result = None
        self._query_matcher.clear()
        self._projection_dict.clear()
        return result

    def find_by_index(self, word_idx, projection=None, generate_response=False, db_session=None):
        """
        Find all CorpusWords that contain the given word index. I.e. retrieve all words with the same stem.
        :param word_idx: integer word index to search for
        :param projection:
        :param generate_response:
        :param db_session:
        :return: CorpusWords that have the given index (they have the same stem)
        """
        return self.simple_match("index", word_idx, projection, generate_response, db_session)

    def find_all_nouns(self, projection=None, generate_response=False, db_session=None):
        """
        Find all CorpusWords that have the noun flag set
        :param projection:
        :param generate_response:
        :param db_session:
        :return: CorpusWords that are nouns
        """
        return self.simple_match("nounFlag", True, projection, generate_response, db_session)

    def find_all_adjectives(self, projection=None, generate_response=False, db_session=None):
        """
        Find all CorpusWords that do not have the noun flag set
        :param projection:
        :param generate_response:
        :param db_session:
        :return: CorpusWords that are adjectives (=> not nouns)
        """
        return self.simple_match("nounFlag", False, projection, generate_response, db_session)

    def index_exists(self, word_idx, db_session=None):
        """
        Checks if a word with the given index exists in the database
        :param word_idx: integer word index
        :param db_session:
        :return: True, if index exists, else False
        """
        self._query_matcher['index'] = word_idx
        self._projection_dict['_id'] = 1
        result = self.collection.find_one(self._query_matcher, self._projection_dict, session=db_session)
        self._query_matcher.clear()
        self._projection_dict.clear()
        return bool(result)

    def _find_word_by_lemmas(self, word, lemma, is_noun, db_session=None):
        lemma_idx = -1
        self._query_matcher['lemma'] = lemma
        for res in self.collection.find(self._query_matcher, self._projection_dict, session=db_session):
            if lemma_idx == -1:
                lemma_idx = res['index']
            if res['text'] == word and res['nounFlag'] == is_noun:
                self._query_matcher.clear()
                return res
        self._query_matcher.clear()
        return lemma_idx

    # @transaction
    def find_doc_or_add(self, word, is_noun, lemma=None, stem=None, generate_response=False, db_session=None):
        # creates a new word in the corpus collection
        if lemma is None:
            lemma = tokenizer.lemmatize_token(word)
        self._query_matcher['lemma'] = lemma
        res = self._find_word_by_lemmas(word, lemma, is_noun, db_session)
        if isinstance(res, dict):
            return False, res  # The word already exists in the database
        self._query_matcher.clear()
        if res == -1:
            res = CorpusIndexManager().get_incremented_index(db_session)
        word = CorpusWord(index_val=res, text=word, lemma=lemma, stem=stem, noun_flag=is_noun)
        if generate_response:
            return self.insert_doc(word, db_session=db_session)
        else:
            return True, self.insert_doc(word, generate_response=False, db_session=db_session)[1]

    @staticmethod
    def _check_insert_args_for_duplicates(w, lem, is_noun, result_list):
        for i, prev in enumerate(result_list):
            if isinstance(prev, tuple) and prev[2] == is_noun and prev[0] == w and prev[1] == lem:
                return i
        return None

    def _find_or_cache(self, token, is_noun, result_list, db_session):
        inpt = token.lower_, token.lemma_.lower(), is_noun
        # TODO: somehow possible to get all lemma indices easily all at once?
        if self._helper_list:
            idx = self._check_insert_args_for_duplicates(*inpt, result_list)
            if idx is not None:
                result_list.append(idx)
                return
        res = self._find_word_by_lemmas(*inpt, db_session)
        if isinstance(res, dict):
            result_list.append(res)
        else:
            self._helper_list.append((len(result_list), res))
            result_list.append(inpt)

    def _collect_phrase_info(self, phrase, result_list, db_session):
        for adj in phrase.adjs:
            self._find_or_cache(adj, False, result_list, db_session)
        root = phrase.root_noun
        if phrase.nouns:
            for noun in phrase.nouns:
                if root != noun:
                    self._find_or_cache(noun, True, result_list, db_session)
        return self._find_or_cache(root, True, result_list, db_session)

    # @transaction
    def find_phrase_words_or_add(self, phrases, generate_response=False, db_session=None):
        result = []
        if isinstance(phrases, NounPhrase):
            self._collect_phrase_info(phrases, result, db_session)
        else:
            for phrase in phrases:
                self._collect_phrase_info(phrase, result, db_session)
        num_new = len(self._helper_list)
        if num_new:
            index_start = CorpusIndexManager().multi_increment_index(num_new, db_session)
            for i, (idx, lemmidx) in enumerate(self._helper_list):
                word, lemma, is_noun = result[idx]
                if lemmidx == -1:
                    lemmidx = index_start + i
                self._helper_list[i] = CorpusWord(index_val=lemmidx, text=word, lemma=lemma,
                                                  stem=None, noun_flag=is_noun)
            self.insert_docs(self._helper_list, None, False, db_session)
            new_doc_idx = 0
            for i, res in enumerate(result):
                if type(res) is tuple:
                    result[i] = self._helper_list[new_doc_idx]
                    new_doc_idx += 1
                elif type(res) is int:
                    result[i] = result[res]
            self._helper_list.clear()
        return self.to_response(result) if generate_response else result
