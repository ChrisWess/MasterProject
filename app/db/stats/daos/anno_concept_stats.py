from collections import defaultdict
from datetime import datetime

import numpy as np

from app.db.daos.concept_dao import ConceptDAO
from app.db.daos.label_dao import LabelDAO
from app.db.stats.daos.base import CategoricalDocStatsDAO, MultiDimDocStatsDAO, CombinedCategoricalDocStatsDAO
from app.db.stats.models.annotation import DocOccurrenceCountStat, TfIdfStat, \
    VectorizedCountsStat, UnrolledConceptCountsStat, TopImgConceptsStat


class ConceptCountDAO(CategoricalDocStatsDAO):
    """ Tells us how often a concept occurred in all annotations """

    def __init__(self):
        super().__init__('fullconceptcount', 'images', DocOccurrenceCountStat,
                         [
                             {"$unwind": "$objects"},
                             {"$unwind": "$objects.annotations"},
                             {"$unwind": "$objects.annotations.conceptIds"},
                             {"$group": {"_id": "$objects.annotations.conceptIds", "occurrenceCount": {"$sum": 1}}},
                         ])


class DocConceptCountVectorizerDAO(CategoricalDocStatsDAO):
    """ Counts the number of all concept occurrences for each class (i.e. document) """
    __slots__ = "_expand_and_limit_query"

    def __init__(self):
        super().__init__('conceptcountvectors', 'images', VectorizedCountsStat,
                         [
                             {"$unwind": "$objects"},
                             {"$unwind": "$objects.annotations"},
                             {"$unwind": "$objects.annotations.conceptIds"},
                             {"$group": {"_id": {"concept": "$objects.annotations.conceptIds",
                                                 "label": "$objects.labelId"},
                                         "count": {"$sum": 1}}},
                         ])
        self._expand_and_limit_query = [
            {"$group": {"_id": "$_id.label",
                        "topConcepts": {
                            "$topN": {"n": 20, "sortBy": {"conceptCount": -1},
                                      "output": {"count": "$conceptCount", "concept": "$_id.concept"}}
                        }}
             },
            {
                "$lookup": {
                    "from": "labels",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "label",
                    "pipeline": [{'$project': {"name": 1, "labelIdx": 1}}]
                }
            },
            {"$unwind": "$topConcepts"},
            {
                "$lookup": {
                    "from": "concepts",
                    "localField": "topConcepts.concept",
                    "foreignField": "_id",
                    "as": "concept",
                    "pipeline": [{'$project': {"phraseIdxs": 1, "phraseWords": 1}}]
                }
            },
            {"$unwind": "$label"},
            {"$unwind": "$concept"},
            {'$project': {"label": 1, "concept": 1, "count": "$topConcepts.count"}}
        ]

    def find_top_concepts_with_info(self, top_n_concepts=20, generate_response=False):
        self._expand_and_limit_query[0]["$group"]["topConcepts"]["$topN"]["n"] = top_n_concepts
        result = list(self.collection.aggregate(self._expand_and_limit_query))
        if generate_response:
            for i, res in enumerate(result):
                result[i] = UnrolledConceptCountsStat(**res).to_dict()
            return {"result": result, "numResults": len(result),
                    "status": 200, 'model': "UnrolledConceptCountsStat", 'isComplete': True}
        else:
            return result

    def find_by_label(self, label_id):
        self._fetch_stat_query['_id.label'] = label_id
        result = []
        try:
            for res in self.collection.find(self._fetch_stat_query):
                result.append((res['_id']['concept'], res['count']))
        finally:
            self._fetch_stat_query.clear()
        return result

    def count_total_labels(self):
        return len(self.collection.distinct('_id.label'))

    def get_concept_counts_for_each_label(self, string_labels=False):
        # for each label, get the full list of tuples/pairs with (count, concept_id)
        qresult = self.find_all_stats(get_cursor=True)
        label_map = defaultdict(list)
        for res in qresult:
            res_id = res['_id']
            if string_labels:
                label_id = str(res_id['label'])
                concept_id = str(res_id['concept'])
            else:
                label_id = res_id['label']
                concept_id = res_id['concept']
            label_map[label_id].append((concept_id, res['count']))
        return label_map


class ConceptOccurrenceDAO(CategoricalDocStatsDAO):
    """ Tells us in how many classes a particular concept has occurred """

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


class ConceptTfIdfDAO(CombinedCategoricalDocStatsDAO):
    def __init__(self):
        super().__init__('concepttfidf', 'images', TfIdfStat,
                         self._compute_tf_idf, {'concept': ConceptDAO, 'label': LabelDAO})

    def _compute_tf_idf(self):
        word_dao = DocConceptCountVectorizerDAO()
        word_dao.update()
        count_lists = word_dao.get_concept_counts_for_each_label()
        total_docs = len(count_lists)
        doc_dao = ConceptOccurrenceDAO()
        doc_dao.update()
        idfs = {doc["_id"]: np.log(total_docs / doc["occurrenceCount"])
                for doc in doc_dao.find_all_stats(get_cursor=True)}
        new_time = datetime.now()
        for label, cl in count_lists.items():
            for concept, count in cl:
                yield self.model(id={"label": label, 'concept': concept}, tf_idf=count * idfs[concept],
                                 updated_at_ts=new_time).model_dump(by_alias=True)

    def find_top_by_label(self, label_id, page_idx, generate_response=False):
        skip = page_idx * 15
        return self.find_by_dim_val('label', label_id, sort='tfIdf', skip=skip, limit=15,
                                    expand_dims='concept', generate_response=generate_response)


class ConceptTfIdfDAO2(MultiDimDocStatsDAO):
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
                                         # TODO: summing all tf over all documents is probably wrong: need to keep the count in each document (maybe using $push)
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

    def find_top_by_label(self, label_id, page_idx, generate_response=False):
        skip = page_idx * 15
        return self.find_by_dim_val('label', label_id, sort='tfIdf', skip=skip, limit=15,
                                    expand_dims='concept', generate_response=generate_response)


class ImageConceptCountVectorizerDAO(CategoricalDocStatsDAO):
    """ Counts the number of all concept occurrences for each image """

    def __init__(self):
        super().__init__('imgconceptcounts', 'images', TopImgConceptsStat,
                         [
                             {"$unwind": "$objects"},
                             {"$unwind": "$objects.annotations"},
                             {"$unwind": "$objects.annotations.conceptIds"},
                             {"$group": {"_id": {"concept": "$objects.annotations.conceptIds",
                                                 "objImage": "$objects._id"},
                                         "count": {"$sum": 1},
                                         "label": {"$first": "$objects.labelId"}}},
                             {"$group": {"_id": "$_id.objImage", "topConcepts": {
                                 "$topN": {"n": 10, "sortBy": {"count": -1}, "output": "$_id.concept"}},
                                         "label": {"$first": "$label"}
                                         }},
                         ])
