from collections import defaultdict
from datetime import datetime

import numpy as np

from app.db.daos.corpus_dao import CorpusDAO
from app.db.daos.label_dao import LabelDAO
from app.db.stats.daos.base import CategoricalDocStatsDAO, MultiDimDocStatsDAO, CombinedCategoricalDocStatsDAO
from app.db.stats.models.annotation import DocOccurrenceCountStat, TfIdfStat, VectorizedCountsStat


class WordCountOverConceptsDAO(CategoricalDocStatsDAO):
    def __init__(self):
        super().__init__('fullwordcount', 'images', DocOccurrenceCountStat,
                         [
                             {"$unwind": "$objects"},
                             {"$unwind": "$objects.annotations"},
                             {"$unwind": "$objects.annotations.conceptIds"},
                             {
                                 "$lookup": {
                                     "from": "concepts",
                                     "localField": "objects.annotations.conceptIds",
                                     "foreignField": "_id",
                                     "as": "concepts"
                                 }
                             },
                             {"$unwind": "$concepts"},
                             {"$unwind": "$concepts.phraseIdxs"},
                             {"$group": {"_id": "$concepts.phraseIdxs", "occurrenceCount": {"$sum": 1}}},
                         ])


class DocWordCountVectorizerDAO(CategoricalDocStatsDAO):
    """ Counts the number of all noun and adjective (group) occurrences for each class (i.e. document) """

    def __init__(self):
        super().__init__('wordcountvectors', 'images', VectorizedCountsStat,
                         [
                             {"$unwind": "$objects"},
                             {"$unwind": "$objects.annotations"},
                             {"$unwind": "$objects.annotations.conceptIds"},
                             {
                                 "$lookup": {
                                     "from": "concepts",
                                     "localField": "objects.annotations.conceptIds",
                                     "foreignField": "_id",
                                     "as": "concepts"
                                 }
                             },
                             {"$unwind": "$concepts"},
                             {"$unwind": {"path": "$concepts.phraseWordIds", "includeArrayIndex": "wIdx1"}},
                             {"$unwind": {"path": "$concepts.phraseIdxs", "includeArrayIndex": "wIdx2"}},
                             {"$project": {"_id": 1, "concepts.phraseIdxs": 1, "concepts.phraseWordIds": 1,
                                           "objects.labelId": 1, "valid": {"$eq": ["$wIdx1", "$wIdx2"]}}},
                             {"$match": {"valid": True}},
                             {
                                 "$lookup": {
                                     "from": "corpus",
                                     "localField": "concepts.phraseWordIds",
                                     "foreignField": "_id",
                                     "as": "word"
                                 }
                             },
                             {"$unwind": "$word"},
                             {"$group": {"_id": {"wordIdx": "$concepts.phraseIdxs", "label": "$objects.labelId",
                                                 "isNoun": "$word.nounFlag"},
                                         "count": {"$sum": 1}}},
                         ])

    def get_word_counts_for_each_label(self, string_labels=False):
        # for each label, get the full list of tuples with (count, word_idx, noun_flag)
        qresult = self.find_all_stats(get_cursor=True)
        label_map = defaultdict(list)
        for res in qresult:
            res_id = res['_id']
            if string_labels:
                label_id = str(res_id['label'])
                word_idx = str(res_id['wordIdx'])
            else:
                label_id = res_id['label']
                word_idx = res_id['wordIdx']
            noun_code = 't' if res_id['isNoun'] else 'f'
            label_map[label_id].append((word_idx, noun_code, res['count']))
        return label_map


class WordOccurrenceDAO(CategoricalDocStatsDAO):
    """ Tells us in how many classes a particular noun or adjective (group) has occurred """

    def __init__(self):
        super().__init__('wordoccurrencecount', 'images', DocOccurrenceCountStat,
                         [
                             {"$unwind": "$objects"},
                             {"$unwind": "$objects.annotations"},
                             {"$unwind": "$objects.annotations.conceptIds"},
                             {
                                 "$lookup": {
                                     "from": "concepts",
                                     "localField": "objects.annotations.conceptIds",
                                     "foreignField": "_id",
                                     "as": "concepts"
                                 }
                             },
                             {"$unwind": "$concepts"},
                             {"$unwind": {"path": "$concepts.phraseWordIds", "includeArrayIndex": "wIdx1"}},
                             {"$unwind": {"path": "$concepts.phraseIdxs", "includeArrayIndex": "wIdx2"}},
                             {"$project": {"_id": 1, "concepts.phraseIdxs": 1, "concepts.phraseWordIds": 1,
                                           "objects.labelId": 1, "valid": {"$eq": ["$wIdx1", "$wIdx2"]}}},
                             {"$match": {"valid": True}},
                             {
                                 "$lookup": {
                                     "from": "corpus",
                                     "localField": "concepts.phraseWordIds",
                                     "foreignField": "_id",
                                     "as": "word"
                                 }
                             },
                             {"$unwind": "$word"},
                             {"$group": {"_id": {"wordIdx": "$concepts.phraseIdxs", "label": "$objects.labelId",
                                                 "isNoun": "$word.nounFlag"}}},
                             {"$group": {"_id": {"wordIdx": "$_id.wordIdx", "isNoun": "$_id.isNoun"},
                                         "occurrenceCount": {"$sum": 1}}},
                         ])


class CorpusTfIdfDAO(CombinedCategoricalDocStatsDAO):
    __slots__ = "_distinct_word_lookup"

    def __init__(self):
        super().__init__('corpustfidf', 'images', TfIdfStat,
                         self._compute_tf_idf, {'wordIdx': ('word', CorpusDAO), 'label': LabelDAO})
        # make sure only the first lookup result is added to the query result
        self._distinct_word_lookup = {"nounFlag": False}
        self._lookups['word']["$lookup"] = {
            "from": "corpus",
            "let": {"index": "$_id.wordIdx"},
            "pipeline": [
                {"$match": {'$and': [self._distinct_word_lookup, {"$expr": {"$eq": ["$index", "$$index"]}}]}},
                {"$limit": 1}
            ],
            "as": "word"
        }

    def _compute_tf_idf(self):
        word_dao = DocWordCountVectorizerDAO()
        word_dao.update()
        count_lists = word_dao.get_word_counts_for_each_label()
        total_docs = len(count_lists)
        doc_dao = WordOccurrenceDAO()
        doc_dao.update()
        idfs = {str(doc["_id"]["wordIdx"]) + ('t' if doc["_id"]["isNoun"] else 'f'):
                    np.log(total_docs / doc["occurrenceCount"]) for doc in doc_dao.find_all_stats(get_cursor=True)}
        # TODO: filter words that only have a low occurrence rate (e.g. less than 5% of total words), but do this
        #  only when the label has enough words (e.g. starting at 500 words).
        new_time = datetime.now()
        for label, cl in count_lists.items():
            for word_idx, noun_code, count in cl:
                yield self.model(id={"label": label, 'wordIdx': word_idx, 'isNoun': noun_code == 't'},
                                 tf_idf=count * idfs[str(word_idx) + noun_code],
                                 updated_at_ts=new_time).model_dump(by_alias=True)

    def find_top_adjectives_by_label(self, label_id, top_n=15, generate_response=False):
        self._distinct_word_lookup['nounFlag'] = False
        return self.find_dim_stats({'_id.label': label_id, '_id.isNoun': False}, sort='tfIdf',
                                   limit=top_n, expand_dims='word', generate_response=generate_response)

    def find_top_nouns_by_label(self, label_id, top_n=15, generate_response=False):
        self._distinct_word_lookup['nounFlag'] = True
        return self.find_dim_stats({'_id.label': label_id, '_id.isNoun': True}, sort='tfIdf',
                                   limit=top_n, expand_dims='word', generate_response=generate_response)


class CorpusTfIdfDAO2(MultiDimDocStatsDAO):
    __slots__ = "_distinct_word_lookup"

    def __init__(self):
        super().__init__('corpustfidf', 'images', TfIdfStat,
                         [
                             {"$unwind": "$objects"},
                             {"$unwind": "$objects.annotations"},
                             {"$unwind": "$objects.annotations.conceptIds"},
                             {
                                 "$lookup": {
                                     "from": "concepts",
                                     "localField": "objects.annotations.conceptIds",
                                     "foreignField": "_id",
                                     "as": "concepts"
                                 }
                             },
                             {"$unwind": "$concepts"},
                             {"$unwind": {"path": "$concepts.phraseWordIds", "includeArrayIndex": "wIdx1"}},
                             {"$unwind": {"path": "$concepts.phraseIdxs", "includeArrayIndex": "wIdx2"}},
                             {"$project": {"_id": 1, "concepts.phraseIdxs": 1, "concepts.phraseWordIds": 1,
                                           "objects.labelId": 1, "valid": {"$eq": ["$wIdx1", "$wIdx2"]}}},
                             {"$match": {"valid": True}},
                             {
                                 "$lookup": {
                                     "from": "corpus",
                                     "localField": "concepts.phraseWordIds",
                                     "foreignField": "_id",
                                     "as": "word"
                                 }
                             },
                             {"$unwind": "$word"},
                             {"$group": {"_id": {"wordIdx": "$concepts.phraseIdxs", "label": "$objects.labelId",
                                                 "isNoun": "$word.nounFlag"},
                                         "tf": {"$sum": 1}}},
                             {"$group": {"_id": {"wordIdx": "$_id.wordIdx", "isNoun": "$_id.isNoun"},
                                         "tf": {"$sum": "$tf"},
                                         "docs": {"$addToSet": "$_id.label"}}},
                             {
                                 "$addFields": {
                                     "df": {"$size": "$docs"}
                                 }
                             },
                             {
                                 "$addFields": {
                                     "idf": {"$ln": {"$divide": ["$df", {"$literal": 1}]}}
                                 }
                             },
                             {
                                 "$addFields": {
                                     "tfidf": {"$multiply": ["$tf", "$idf"]}
                                 }
                             },
                             {"$unwind": "$docs"},
                             {
                                 "$group": {
                                     "_id": "$docs",
                                     "tfidf": {"$push": {
                                         "$cond": [
                                             {"$ne": ["$tfidf", 0]},
                                             {"wordIdx": "$_id.wordIdx", "isNoun": "$_id.isNoun", "tfidf": "$tfidf"},
                                             "$$REMOVE"
                                         ]
                                     }
                                     }}},
                             {"$unwind": "$tfidf"},
                             {
                                 "$project": {
                                     "_id": {"wordIdx": "$tfidf.wordIdx", "isNoun": "$tfidf.isNoun", "label": "$_id"},
                                     "tfIdf": "$tfidf.tfidf",
                                 }
                             },
                         ], {'wordIdx': ('word', CorpusDAO), 'label': LabelDAO})
        # make sure only the first lookup result is added to the query result
        self._distinct_word_lookup = {"nounFlag": False}
        self._lookups['word']["$lookup"] = {
            "from": "corpus",
            "let": {"index": "$_id.wordIdx"},
            "pipeline": [
                {"$match": {'$and': [self._distinct_word_lookup, {"$expr": {"$eq": ["$index", "$$index"]}}]}},
                {"$limit": 1}
            ],
            "as": "word"
        }

    def find_top_adjectives_by_label(self, label_id, top_n=15, generate_response=False):
        self._distinct_word_lookup['nounFlag'] = False
        return self.find_dim_stats({'_id.label': label_id, '_id.isNoun': False}, sort='tfIdf',
                                   limit=top_n, expand_dims='word', generate_response=generate_response)

    def find_top_nouns_by_label(self, label_id, top_n=15, generate_response=False):
        self._distinct_word_lookup['nounFlag'] = True
        return self.find_dim_stats({'_id.label': label_id, '_id.isNoun': True}, sort='tfIdf',
                                   limit=top_n, expand_dims='word', generate_response=generate_response)
