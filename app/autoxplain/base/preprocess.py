import os
from collections import defaultdict

from pymongo import MongoClient, DESCENDING

import config


def extract_top_concepts(client, top_n=4, max_adjs=3):
    result = client.concepttfidf.aggregate([
        {"$group": {
            "_id": "$_id.label",
            "topConcepts": {"$topN": {"n": 40, "sortBy": {"tfIdf": DESCENDING},
                                      "output": {'concept': "$_id.concept", 'tfIdf': "$tfIdf"}}}
        }},
        {'$unwind': '$topConcepts'},
        {
            "$lookup": {
                "from": "concepts",
                "localField": "topConcepts.concept",
                "foreignField": "_id",
                "as": "concepts",
                "pipeline": [{'$project': {"phraseIdxs": 1, "phraseWords": 1, "nounCount": 1}}]
            }
        },
        {'$unwind': '$concepts'},
        {"$match": {"concepts.phraseIdxs": {"$ne": 0}}},  # filter out all concepts referring to the subject
        {"$group": {
            "_id": "$_id",
            "concepts": {"$push": {"_id": "$concepts._id", "phraseIdxs": "$concepts.phraseIdxs",
                                   "phraseWords": "$concepts.phraseWords", "nounCount": "$concepts.nounCount",
                                   "tfIdf": "$topConcepts.tfIdf"}},
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
        {'$unwind': '$label'},
        {"$project": {
            "concepts": {"$slice": ["$concepts", 15]},
            "label": 1,
        }},
    ])
    selected_concepts = defaultdict(list)
    for doc in result:
        label = doc["label"]
        label_concepts = selected_concepts[label['name']]
        for c in doc["concepts"]:
            sidxs = c['phraseIdxs']
            num_nouns = c["nounCount"]
            noun_idxs = set(sidxs[-num_nouns:])
            for selected in label_concepts:
                cand_nouns = selected['nounCount']
                cand_sidxs = selected['phraseIdxs']
                cand_noun_idxs = set(cand_sidxs[-cand_nouns:])
                num_cand_adjs = len(cand_sidxs) - cand_nouns
                if num_cand_adjs < max_adjs and noun_idxs == cand_noun_idxs:
                    # if noun is the same, then add the adjective to the selected concept
                    adj_idxs = sidxs[:-num_nouns]
                    cand_adjs_set = set(cand_sidxs[:-cand_nouns])
                    for i in range(len(sidxs) - num_nouns):
                        adj = adj_idxs[i]
                        if adj not in cand_adjs_set:
                            pos = num_cand_adjs - 1
                            cand_sidxs.insert(pos, adj)
                            selected['phraseWords'].insert(pos, c['phraseWords'][i])
                    break
                elif len(noun_idxs & cand_noun_idxs) >= len(cand_noun_idxs) / 2:
                    break  # if a concept has more or equal words in common with any previously selected concept
            else:
                if len(label_concepts) < top_n:
                    label_concepts.append(c)  # select new concept, if it is diverse enough
    return selected_concepts


def write_to_file(fname, top_concepts):
    with open(fname, "w") as f:
        for i, (label, concepts) in enumerate(top_concepts.items(), start=1):
            f.write(f'{i}: {label}\n')
            for concept in concepts:
                f.write(' '.join(concept['phraseWords']) + '\n')
            f.write('\n')


if __name__ == '__main__':
    config = config.Production if 'PRODUCTION' in os.environ else config.Debug
    db_client = MongoClient(config.MONGODB_DATABASE_URI).xplaindb
    selection = extract_top_concepts(db_client)
    write_to_file("top_class_concepts.txt", selection)
