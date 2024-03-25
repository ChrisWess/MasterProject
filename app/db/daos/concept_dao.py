from copy import deepcopy

from pymongo import ASCENDING, DESCENDING

from app.db.daos.base import JoinableDAO, dao_update
from app.db.daos.corpus_dao import CorpusDAO
from app.db.models.concept import Concept
from app.db.models.payloads.concept import ConceptPayload
from app.preproc.annotation import NounPhrase
from app.preproc.concept import DefaultConceptPreprocesser


class ConceptDAO(JoinableDAO):
    __slots__ = "_phrase_idxs", "_phrase_match", "_noun_phrase_agg", "_tokens", "_word_ids", "_idxs", "preproc"

    def __init__(self):
        # Initialize mongodb collection of annotation concepts
        super().__init__("concepts", Concept, ConceptPayload)
        self.references = {'phraseWordIds': ('phraseWordsData', CorpusDAO, True)}

        self.create_index('concept_phrase_index', ("phraseIdxs", ASCENDING))
        self.create_index('concept_key_index', ("key", ASCENDING), unique=True)
        self._phrase_idxs = []
        self._phrase_match = {"$match": {"phraseIdxs": {"$in": self._phrase_idxs}}}
        self._noun_phrase_agg = [
            self._phrase_match,
            {'$unwind': '$phraseIdxs'},
            self._phrase_match,
            {"$group": {"_id": "$key", "numRelDocs": {"$sum": 1}}},
            {"$sort": {"numRelDocs": DESCENDING}},
            {"$limit": 20}
        ]
        # for exact matching and adding concepts
        self._tokens = []
        self._word_ids = []
        self._idxs = []

        self.preproc = DefaultConceptPreprocesser()

    def find_by_key(self, key, projection=None, generate_response=False, db_session=None):
        """
        Find the Concept that is identified by the given key
        :param key: Concept key identifier to search for
        :param projection:
        :param generate_response:
        :param db_session:
        :return: Concept that matches the key or None
        """
        return self.simple_match("key", key, projection, generate_response, db_session, find_many=False)

    def find_by_keys(self, keys, projection=None, generate_response=False, get_cursor=False, db_session=None):
        """
        Find all Concepts that are successfully identified from the given list of keys
        :param keys: list of Concept key identifiers to search for
        :param projection:
        :param generate_response:
        :param get_cursor:
        :param db_session:
        :return: Concepts that matches the given keys
        """
        self._in_query['$in'] = keys
        self._query_matcher["key"] = self._in_query
        if get_cursor:
            projection = self.build_projection(projection)
            projection_copy = deepcopy(projection) if projection else projection
            result = self.collection.find(deepcopy(self._query_matcher), projection_copy, session=db_session)
            result = self._apply_sort_limit(result, True)
        else:
            if projection:
                projection = self.build_projection(projection)
                result = self.collection.find(self._query_matcher, projection, session=db_session)
            else:
                result = self.collection.find(self._query_matcher, session=db_session)
            result = list(self._apply_sort_limit(result))
        self._in_query.clear()
        self._query_matcher.clear()
        if projection:
            projection.clear()
        return self.to_response(result) if generate_response else result

    def find_by_corpus_word_id(self, word_id, projection=None, generate_response=False, db_session=None):
        """
        Find all Concepts that contain the given word ID
        :param word_id: word ID to search for
        :param projection:
        :param generate_response:
        :param db_session:
        :return: Concepts that contain the given word
        """
        return self.simple_match("phraseWordIds", word_id, projection, generate_response, db_session)

    def find_by_word(self, word, projection=None, generate_response=False, db_session=None):
        """
        Find all Concepts that contain the given word
        :param word: word string to search for
        :param projection:
        :param generate_response:
        :param db_session:
        :return: Concepts that contain the given word
        """
        return self.simple_match("phraseWords", word, projection, generate_response, db_session)

    def find_by_filter_index(self, conv_filter_idx, projection=None, generate_response=False, db_session=None):
        """
        Find the Concept that corresponds to the filter that represents this concept
        in the last convolutional layer of the classifier model.
        :param conv_filter_idx: index of the convolutional filter in the classifier model
        :param projection:
        :param generate_response:
        :param db_session:
        :return: Concept with the given index
        """
        return self.simple_match("convFilterIdx", conv_filter_idx, projection,
                                 generate_response, db_session, find_many=False)

    def find_by_relevance(self, noun_phrase, lemma_list=False, db_session=None):
        """
        Find all Concepts that contain the given noun phrase
        :param noun_phrase: list of tokens or NounPhrase object representing the noun phrase.
        :param lemma_list: Flag that is only relevant, if input is a list. Notifies the query
                           if the list contains word lemmas or the original tokens.
        :param db_session:
        :return: Subset of Concepts that contain at least all the queried words.
        """
        corpus = CorpusDAO()
        if lemma_list:
            for lemma in noun_phrase:
                idx = corpus.find_lemma_idx(lemma, db_session)
                if idx is None:
                    self._phrase_idxs.clear()
                    return self._phrase_idxs
        else:
            if not isinstance(noun_phrase, NounPhrase):
                if isinstance(noun_phrase, list):
                    noun_phrase = ' '.join(noun_phrase)
                noun_phrase = self.preproc.as_noun_phrase(noun_phrase)
                if noun_phrase is None:
                    return None
            for adj in noun_phrase.adjs:
                idx = corpus.find_lemma_idx(adj.lemma_, db_session)
                if idx is None:
                    self._phrase_idxs.clear()
                    return self._phrase_idxs
            if noun_phrase.nouns:
                for noun in noun_phrase.nouns:
                    idx = corpus.find_lemma_idx(noun.lemma_, db_session)
                    if idx is None:
                        self._phrase_idxs.clear()
                        return self._phrase_idxs
            else:
                idx = corpus.find_lemma_idx(noun_phrase.root_noun.lemma_, db_session)
                if idx is None:
                    self._phrase_idxs.clear()
                    return self._phrase_idxs
        # TODO: allow limit and projection
        # the more indices match, the earlier a concept will appear in the aggregation (bc of group and sort)
        return list(self.collection.aggregate(self._noun_phrase_agg, session=db_session))

    @dao_update(update_many=False)
    def update_filter(self, concept_id, filter_idx):
        self.add_query("_id", concept_id)
        self.add_update('convFilterIdx', filter_idx)

    # @transaction
    def add_from_key(self, concept_key, generate_response=False, db_session=None):
        self._idxs.extend(concept_key.split(','))
        for i, ixs in enumerate(self._idxs):
            self._idxs[i] = int(ixs)
        words, num_nouns, root_id = CorpusDAO().find_concept_words_from_indices(self._idxs, db_session=db_session)
        for word in words:
            self._tokens.append(word['text'])
            self._word_ids.append(word['_id'])
        concept = Concept(concept_key=concept_key, root_noun=root_id, phrase_word_ids=self._word_ids,
                          phrase_idxs=self._idxs, phrase_words=self._tokens, noun_count=num_nouns)
        response = self.insert_doc(concept, generate_response=generate_response, db_session=db_session)
        self._tokens.clear()
        self._word_ids.clear()
        self._idxs.clear()
        return response if generate_response else True, response[1]

    # @transaction
    def add_from_keys(self, concept_keys, generate_response=False, db_session=None):
        for i, key in enumerate(concept_keys):
            self._idxs.extend(key.split(','))
            for j, ixs in enumerate(self._idxs):
                self._idxs[j] = int(ixs)
            words, num_nouns, root_id = CorpusDAO().find_concept_words_from_indices(self._idxs, db_session=db_session)
            for word in words:
                self._tokens.append(word['text'])
                self._word_ids.append(word['_id'])
            concept = Concept(concept_key=key, root_noun=root_id, phrase_word_ids=self._word_ids.copy(),
                              phrase_idxs=self._idxs.copy(), phrase_words=self._tokens.copy(), noun_count=num_nouns)
            concept_keys[i] = concept
            self._tokens.clear()
            self._word_ids.clear()
            self._idxs.clear()
        return self.insert_docs(concept_keys, generate_response=generate_response, db_session=db_session)

    # @transaction
    def find_doc_or_add(self, noun_phrase, generate_response=False, db_session=None):
        # creates a new concept in the concepts collection
        # TODO: what is the "vector" value of a span i.e. how is it computed?
        #  Can we use the vector norm to query concepts?
        # TODO: add method to add all concepts at once
        words = CorpusDAO().find_phrase_words_or_add(noun_phrase, db_session=db_session)
        root_id = None
        num_nouns = 0
        for word in words:
            self._tokens.append(word['text'])
            self._word_ids.append(word['_id'])
            self._idxs.append(word['index'])
            if word['nounFlag']:
                num_nouns += 1
                root_id = word['_id']
        concept_key = ','.join(str(idx) for idx in sorted(self._idxs))
        matching_concept = self.find_by_key(concept_key, db_session=db_session)
        if matching_concept is not None:
            self._tokens.clear()
            self._word_ids.clear()
            self._idxs.clear()
            return False, matching_concept
        concept = Concept(concept_key=concept_key, root_noun=root_id, phrase_word_ids=self._word_ids,
                          phrase_idxs=self._idxs, phrase_words=self._tokens, noun_count=num_nouns)
        response = self.insert_doc(concept, generate_response=generate_response, db_session=db_session)
        self._tokens.clear()
        self._word_ids.clear()
        self._idxs.clear()
        if generate_response:
            return response
        else:
            return True, response[1]

    def _collect_concepts(self, result_list, db_session):
        dup_concept = False
        for i, idxs in enumerate(self._idxs):
            concept_key = ','.join(str(idx) for idx in sorted(idxs))
            if concept_key in self._field_check:
                dup_concept = True
                result_list[i] = self._field_check[concept_key]
            else:
                self._field_check[concept_key] = i
                self._helper_list.append(concept_key)
        matching_concepts = self.find_by_keys(self._helper_list, db_session=db_session)
        for doc in matching_concepts:
            result_list[self._field_check[doc['key']]] = doc
        idx = 0
        for res, idxs, tokens, word_ids in zip(result_list, self._idxs, self._tokens, self._word_ids):
            if isinstance(res, tuple):
                root_id, ncount = res
                self._helper_list[idx] = Concept(concept_key=self._helper_list[idx], root_noun=root_id,
                                                 phrase_word_ids=word_ids, phrase_idxs=idxs,
                                                 phrase_words=tokens, noun_count=ncount)
                idx += 1
            elif not isinstance(res, int):
                del self._helper_list[idx]
        self._tokens.clear()
        self._word_ids.clear()
        self._idxs.clear()
        self._field_check.clear()
        if self._helper_list:
            self.insert_docs(self._helper_list, None, False, db_session)
        return dup_concept

    # @transaction
    def find_concepts_or_add(self, noun_phrases, generate_response=False, db_session=None):
        words = CorpusDAO().find_phrase_words_or_add(noun_phrases, db_session=db_session)
        root_id = None
        num_nouns = 0
        result, tokens, word_ids, idxs = [], [], [], []
        for word in words:
            is_noun = word['nounFlag']
            if not is_noun and num_nouns:
                self._tokens.append(tokens)
                self._word_ids.append(word_ids)
                self._idxs.append(idxs)
                tokens, word_ids, idxs = [], [], []
                result.append((root_id, num_nouns))
                num_nouns = 0
            new_id = word['_id']
            tokens.append(word['text'])
            word_ids.append(new_id)
            idxs.append(word['index'])
            if is_noun:
                num_nouns += 1
                root_id = new_id
        self._tokens.append(tokens)
        self._word_ids.append(word_ids)
        self._idxs.append(idxs)
        result.append((root_id, num_nouns))
        dup_concept = self._collect_concepts(result, db_session)
        idx = 0
        for cdoc in self._helper_list:
            res = result[idx]
            while not isinstance(res, tuple):
                idx += 1
                res = result[idx]
            result[idx] = cdoc
            idx += 1
        if dup_concept:
            for i, j in enumerate(result):
                if type(j) is int:
                    result[i] = result[j]
        self._helper_list.clear()
        return self.to_response(result) if generate_response else result

    def add_to_annotation(self, noun_phrase, label_id, conv_filter_idx=None, generate_response=False, db_session=None):
        # creates a new concept in the concepts collection
        # TODO: Check if concept exists: if it does, return its ID, if it doesn't, then insert it
        #  and return its ID (the annotation adds it to its list of linked concept IDs).
        pass
