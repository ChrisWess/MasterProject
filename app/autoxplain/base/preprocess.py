import os

from pymongo import MongoClient, DESCENDING

import config


def extract_top_concepts(client):
    coll = client.concepttfidf
    label_count = coll.aggregate([
        {"$group": {
            "_id": "$_id.label",
        }},
        {"$count": 'numLabels'}
    ]).next()['numLabels']
    count_limit = label_count / 2  # filter concept, if it occurs more often than this limit (50% of concepts)
    result = coll.aggregate([
        {"$group": {
            "_id": "$_id.label",
            "topConcepts": {"$topN": {"n": 10, "sortBy": {"tfIdf": DESCENDING}, "output": "$_id.concept"}}
        }},
        {
            "$lookup": {
                "from": "labels",
                "localField": "_id",
                "foreignField": "_id",
                "as": "label",
                "pipeline": [{'$project': {"name": 1, "labelIdx": 1}}]
            }
        },
        {
            "$lookup": {
                "from": "concepts",
                "localField": "topConcepts",
                "foreignField": "_id",
                "as": "concept",
                "pipeline": [{'$project': {"phraseIdxs": 1, "phraseWords": 1}}]
            }
        },
        {'$project': {"concept": 1, "label": 1}},
        {'$limit': 10}
    ])
    """
            {'$unwind': '$topConcepts'},
            {
                "$lookup": {
                    "from": "concepts",
                    "localField": "topConcepts",
                    "foreignField": "_id",
                    "as": "concept",
                    "pipeline": [{'$project': {"phraseIdxs": 1, "phraseWords": 1}}]
                }
            },
            {'$project': {"concept": 1}},
            {'$unwind': '$concept'},
            {"$match": {"concept.phraseIdxs": {"$ne": 0}}},  # filter out all concepts referring to the subject
            {"$group": {
                "_id": "$concept._id",
                "occur": {"$sum": 1},
                "concept": {"$first": "$concept"},
                "labels": {"$push": "$_id"},
            }},
            {"$match": {"occur": {"$lte": count_limit}}},
            {'$sort': {"occur": ASCENDING}},
            {'$unwind': '$labels'},
            {"$group": {
                "_id": "$labels",
                # "concepts": {"$push": "$concept"},
                "concepts": {"$topN": {"n": 10, "sortBy": {"occur": ASCENDING}, "output": "$concept"}}
            }},
            {
                "$lookup": {
                    "from": "labels",
                    "localField": "_id",
                    "foreignField": "_id",
                    "as": "label",
                    "pipeline": [{'$project': {"name": 1, "labelIdx": 1}}]
                }
            },
            {'$limit': 20}"""
    from pprint import pprint
    pprint(list(result))
    return result


if __name__ == '__main__':
    config = config.Production if 'PRODUCTION' in os.environ else config.Debug
    db_client = MongoClient(config.MONGODB_DATABASE_URI).xplaindb
    extract_top_concepts(db_client)
