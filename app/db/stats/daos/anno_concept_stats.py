from app.db.daos.concept_dao import ConceptDAO
from app.db.daos.label_dao import LabelDAO
from app.db.stats.daos.base import CategoricalDocStatsDAO, MultiDimDocStatsDAO
from app.db.stats.models.annotation import AnnotationConceptCountStat, DocOccurrenceCountStat, TfIdfStat


class ConceptCountDAO(CategoricalDocStatsDAO):
    def __init__(self):
        super().__init__('fullconceptcount', 'images', AnnotationConceptCountStat,
                         [
                             {"$unwind": "$objects"},
                             {"$unwind": "$objects.annotations"},
                             {"$unwind": "$objects.annotations.conceptIds"},
                             {"$group": {"_id": "$objects.annotations.conceptIds", "conceptCount": {"$sum": 1}}},
                         ])


class MostFrequentConceptsDAO(CategoricalDocStatsDAO):
    def __init__(self):
        super().__init__('frequentconceptcount', 'images', AnnotationConceptCountStat,
                         [
                             {"$unwind": "$objects"},
                             {"$unwind": "$objects.annotations"},
                             {"$unwind": "$objects.annotations.conceptIds"},
                             {"$group": {"_id": {"concept": "$objects.annotations.conceptIds",
                                                 "label": "$objects.labelId"},
                                         "conceptCount": {"$sum": 1}}},
                         ])


class ConceptOccurrenceDAO(CategoricalDocStatsDAO):
    def __init__(self):
        super().__init__('conceptoccurrencecount', 'images', DocOccurrenceCountStat,
                         [
                             {"$unwind": "$objects"},
                             {"$unwind": "$objects.annotations"},
                             {"$unwind": "$objects.annotations.conceptIds"},
                             {"$group": {
                                 "_id": {"concept": "$objects.annotations.conceptIds", "label": "$objects.labelId"}}},
                             {"$group": {"_id": "$_id.concept", "occurrenceCount": {"$sum": 1}}},
                         ])


class ConceptTfIdfDAO(MultiDimDocStatsDAO):
    def __init__(self):
        super().__init__('concepttfidf', 'images', TfIdfStat,
                         [
                             {"$unwind": "$objects"},
                             {"$unwind": "$objects.annotations"},
                             {"$unwind": "$objects.annotations.conceptIds"},
                             {"$group": {"_id": {"concept": "$objects.annotations.conceptIds",
                                                 "label": "$objects.labelId"},
                                         "tf": {"$sum": 1}}},
                             {"$group": {"_id": "$_id.concept", "tf": {"$sum": "$tf"},
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
                                             {"concept": "$_id", "tfidf": "$tfidf"},
                                             "$$REMOVE"
                                         ]
                                     }
                                     }}},
                             {"$unwind": "$tfidf"},
                             {
                                 "$project": {
                                     "_id": {"concept": "$tfidf.concept", "label": "$_id"},
                                     "tfIdf": "$tfidf.tfidf",
                                 }
                             },
                         ], {'concept': ConceptDAO, 'label': LabelDAO})

    def find_top_by_label(self, label_id, generate_response=False):
        return self.find_by_dim_val('label', label_id, sort='tfIdf', limit=10,
                                    expand_dims='label', generate_response=generate_response)


class MostFrequentConceptsOfClassDAO(CategoricalDocStatsDAO):
    def __init__(self):
        super().__init__('labelconceptcount', 'images', AnnotationConceptCountStat,
                         [  # TODO: inject desired label as parameter
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
                             {"$group": {"_id": "$concepts._id", "conceptCount": {"$sum": 1}}},
                             {"$sort": {"conceptCount": -1}},
                             {"$limit": 10},
                         ])
