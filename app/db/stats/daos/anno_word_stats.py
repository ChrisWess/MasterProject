from app.db.daos.corpus_dao import CorpusDAO
from app.db.daos.label_dao import LabelDAO
from app.db.stats.daos.base import CategoricalDocStatsDAO, MultiDimDocStatsDAO
from app.db.stats.models.annotation import AnnotationWordCountStat, DocOccurrenceCountStat, TfIdfStat


class WordCountOverConceptsDAO(CategoricalDocStatsDAO):
    def __init__(self):
        super().__init__('fullwordcount', 'images', AnnotationWordCountStat,
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
                             {"$group": {"_id": "$concepts.phraseIdxs", "wordIdxCount": {"$sum": 1}}},
                         ])


class MostFrequentWordsDAO(CategoricalDocStatsDAO):
    def __init__(self):
        super().__init__('frequentwordcount', 'images', AnnotationWordCountStat,
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
                             {"$unwind": "$concepts.phraseWordIds"},
                             {
                                 "$lookup": {
                                     "from": "corpus",
                                     "localField": "concepts.phraseWordIds",
                                     "foreignField": "_id",
                                     "as": "word"
                                 }
                             },
                             {"$unwind": "$concepts.phraseIdxs"},
                             {"$group": {"_id": {"wordIdx": "$concepts.phraseIdxs", "label": "$objects.labelId",
                                                 "isNoun": "$word.nounFlag"},
                                         "wordIdxCount": {"$sum": 1}}},
                             {"$unwind": "$_id.isNoun"},
                         ])


class WordOccurrenceDAO(CategoricalDocStatsDAO):
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
                             {"$unwind": "$concepts.phraseWordIds"},
                             {
                                 "$lookup": {
                                     "from": "corpus",
                                     "localField": "concepts.phraseWordIds",
                                     "foreignField": "_id",
                                     "as": "word"
                                 }
                             },
                             {"$unwind": "$concepts.phraseIdxs"},
                             {"$group": {"_id": {"wordIdx": "$concepts.phraseIdxs", "label": "$objects.labelId",
                                                 "isNoun": "$word.nounFlag"}}},
                             {"$unwind": "$_id.isNoun"},
                             {"$group": {"_id": {"wordIdx": "$_id.wordIdx", "isNoun": "$_id.isNoun"},
                                         "occurrenceCount": {"$sum": 1}}},
                         ])


class CorpusTfIdfDAO(MultiDimDocStatsDAO):
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


class UngroupedMostFrequentWordsDAO(CategoricalDocStatsDAO):
    def __init__(self):
        super().__init__('ungroupedfrequcount', 'images', AnnotationWordCountStat,
                         [  # TODO: inject desired values to query for in places that contain "None"
                             {"$unwind": "$objects"},
                             {"$unwind": "$objects.annotations"},
                             {"$match": {"objects.labelId": None}},
                             {
                                 "$lookup": {
                                     "from": "concepts",
                                     "localField": "objects.annotations.conceptIds",
                                     "foreignField": "_id",
                                     "as": "concepts"
                                 }
                             },
                             {"$unwind": "$concepts"},
                             {"$unwind": "$concepts.phraseWordIds"},
                             {
                                 "$lookup": {
                                     "from": "corpus",
                                     "localField": "concepts.phraseWordIds",
                                     "foreignField": "_id",
                                     "as": "word"
                                 }
                             },
                             {"$match": {"word.nounFlag": None}},
                             {"$unwind": "$concepts.phraseIdxs"},
                             {"$group": {"_id": "$concepts.phraseIdxs", "wordIdxCount": {"$sum": 1}}},
                             {"$sort": {"wordIdxCount": -1}},
                             {"$limit": 15},
                         ])
