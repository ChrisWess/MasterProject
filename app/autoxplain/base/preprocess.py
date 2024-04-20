import os

from pymongo import MongoClient, DESCENDING

import config


def extract_top_concepts(client):
    coll = client.concepttfidf
    result = coll.aggregate([
        {"$group": {
            "_id": "$_id.label",
            "top": {"$topN": {"n": 20, "sortBy": {"tfIdf": DESCENDING}, "output": "$_id.concept"}}
        }},
        {'$unwind': '$top'},
        {
            "$lookup": {
                "from": "concepts",
                "localField": "top",
                "foreignField": "_id",
                "as": "concept",
                "pipeline": [{'$project': {"phraseIdxs": 1, "phraseWords": 1}}]
            }
        },
        {'$limit': 10}
    ])
    print(list(result))
    return result


if __name__ == '__main__':
    config = config.Production if 'PRODUCTION' in os.environ else config.Debug
    db_client = MongoClient(config.MONGODB_DATABASE_URI).xplaindb
    extract_top_concepts(db_client)
