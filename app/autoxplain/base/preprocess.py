import os
from collections import defaultdict
from itertools import islice

import inflect
import numpy as np
from pymongo import MongoClient, DESCENDING
from textblob import Word

import config

relevant_concept_query = [
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
        "concepts": {"$slice": ["$concepts", 30]},
        "label": 1,
    }},
]


def extract_top_concepts(client, top_n=3, limit_adjs=2):
    result = client.concepttfidf.aggregate(relevant_concept_query)
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
                if num_cand_adjs < limit_adjs and noun_idxs == cand_noun_idxs:
                    # if noun is the same, then add the adjective to the selected concept
                    adj_idxs = sidxs[:-num_nouns]
                    cand_adjs_set = set(cand_sidxs[:-cand_nouns])
                    for i in range(len(sidxs) - num_nouns):
                        adj = adj_idxs[i]
                        if adj not in cand_adjs_set and adj not in cand_noun_idxs:
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


def class_concepts_to_file(fname, top_concepts):
    with open(fname, "w") as f:
        for i, (label, concepts) in enumerate(top_concepts.items(), start=1):
            f.write(f'{i}: {label}\n')
            for concept in concepts:
                f.write(' '.join(concept['phraseWords']) + '\n')
            f.write('\n')


def concept_set_to_file(fname, concept_map):
    concepts = {' '.join(concept['phraseWords']) for concepts in concept_map.values() for concept in concepts}
    with open(fname, "w") as f:
        for concept in concepts:
            f.write(concept + '\n')


def extract_concepts_regular(client):
    selection = extract_top_concepts(client)
    class_concepts_to_file("top_class_concepts.txt", selection)
    concept_set_to_file("unique_concepts.txt", selection)


def word_singular_transform_factory():
    inflector = inflect.engine()

    def singular_trafo(word):
        singular = inflector.singular_noun(word)
        return singular if singular else word

    return singular_trafo


def textblob_word_singular_transform(word):
    return str(Word(word).singularize())


def extract_simple_concepts(client, min_occur=3):
    # extract only concepts with a single noun and 1 or 2 adjectives
    result = client.concepttfidf.aggregate(relevant_concept_query)
    doc_count_coll = client.conceptcountvectors
    selected_concepts = defaultdict(list)
    for doc in result:
        label = doc["label"]
        label_concepts = selected_concepts[label['name']]
        for c in doc["concepts"]:
            num_nouns = c["nounCount"]
            if num_nouns == 1 and len(c['phraseIdxs']) <= 3:
                if c['phraseWords'][-1] == 'larsus':
                    continue
                doc_id_query = {'_id': {'concept': c['_id'], 'label': label['_id']}}
                count = doc_count_coll.find_one(doc_id_query)['count']
                # check if concept with current concept ID occurs at least "min_occur" times in label
                if count >= min_occur:
                    noun = c['phraseIdxs'][-1]
                    for selected in label_concepts:
                        cand_noun = selected['phraseIdxs'][-1]
                        if noun == cand_noun:
                            break
                    else:
                        # This preprocessing is very specialized for the CUB dataset. In general, you could just
                        # disregard concepts with unknown words (i.e. spelling errors). These are only regarded and
                        # corrected here in order to lose the least amount of data.
                        noun = c['phraseWords'][-1]
                        if noun == 'supercilliary':
                            c['phraseWords'][-1] = 'superciliary'
                        elif noun == 'rectrice':
                            c['phraseWords'][-1] = 'retrices'
                        elif noun == 'cheekpatch':
                            c['phraseWords'][-1] = 'cheek-patch'
                        elif noun == 'tailfeathers':
                            c['phraseWords'][-1] = 'tail-feathers'
                        label_concepts.append(c)  # select new concept, if it is diverse enough
    inflector = inflect.engine()
    concept_dict = {}
    concept_set = set()
    vocab_dict = {}  # maps the original word to the singular version
    for concepts in selected_concepts.values():
        for concept in concepts:
            words = concept['phraseWords']
            c = ' '.join(words)
            if c not in concept_set:
                for word in words:
                    if word not in vocab_dict:
                        singular = inflector.singular_noun(word)
                        vocab_dict[word] = singular if singular else word
                concept_set.add(c)
                concept_dict[concept['_id']] = [c, words]
    concepts = list(concept_set)
    with open("data/unique_concepts.txt", "w") as f:
        for i, concept in enumerate(concepts):
            f.write(concept + '\n')
            for vals in concept_dict.values():
                if vals[0] == concept:
                    vals.append(i)
                    break
    classes = {}
    with open("data/class_ids.txt", "w") as f:
        for i, cls in enumerate(doc_count_coll.distinct('_id.label')):
            cls = str(cls)
            f.write(cls + '\n')
            classes[cls] = i
    return concept_dict, concepts, vocab_dict, classes


def top_concepts_per_image(client, concept_mapping, concept_list, classes, top_n=3, min_concepts=2):
    # Create and save 2 indicator (one-hot encoded) vectors in numpy:
    #  1) Class indicator vectors (which concepts occur in which class)
    #  2) Image indicator vectors (which concepts describe each image)
    num_concepts = len(concept_list)
    image_indicator_vectors = {}
    # Indicate (by one-hot vectors) which concepts appear in which class
    class_indicator_vector = np.zeros(shape=(num_concepts, len(classes)), dtype=bool)
    if not min_concepts:
        min_concepts = top_n
    total_num_concepts = 0
    for doc in client.imgconceptcounts.find():
        oimg_id = str(doc['_id'])
        class_id = classes[str(doc['label'])]
        top_concepts = filter(lambda x: x in concept_mapping, doc['topConcepts'])
        img_concepts = tuple(islice((concept_mapping[concept][0] for concept in top_concepts), top_n))
        if len(img_concepts) >= min_concepts:
            image_vec = np.zeros(shape=num_concepts, dtype=bool)
            for c in img_concepts:
                idx = concept_list.index(c)
                image_vec[idx] = True
                class_indicator_vector[idx][class_id] = True
                total_num_concepts += 1
            image_indicator_vectors[oimg_id] = (image_vec, class_id)
    sample_dim = len(image_indicator_vectors)
    print("Number of vectorized images:", sample_dim)
    print("Average number of concepts per image:", total_num_concepts / sample_dim, f"(max num of concepts: {top_n})")
    np.save('data/image_indicator_vectors.npy', image_indicator_vectors)
    np.save('data/class_indicator_vectors.npy', class_indicator_vector)
    return image_indicator_vectors, class_indicator_vector


def load_glove_vectors(glove_file):
    """Load the glove word vectors (weights from https://nlp.stanford.edu/projects/glove/ )"""
    word_vectors = {}
    with open(glove_file) as f:
        for line in f:
            split = line.split()
            word = split[0]
            if word == 'eye-ring':
                word = 'eyering'
            word_vectors[word] = np.array([float(x) for x in split[1:]])
    return word_vectors


uncommon_words = {'wingbar', 'wingbars', 'cheek-patch', 'tail-feathers', 'retrice',
                  'retrices', 'superciliary', 'superciliaries'}


def get_emb_matrix(vocab, glove_file, emb_size):
    """ Creates embedding matrix from word vectors"""
    vocab_to_idx = {"": 0, "UNK": 1}
    w = [np.zeros(emb_size, dtype=np.float32),  # adding a vector for padding
         np.random.uniform(-0.25, 0.25, emb_size)]  # adding a vector for unknown words

    pretrained = load_glove_vectors(glove_file)
    i = 2
    for word, singular in vocab.items():
        entry = word
        if word in uncommon_words:
            if word == 'superciliary' or word == 'superciliaries':
                entry = 'eyebrow'
            elif word == 'retrice':
                entry = 'retrices'
            else:
                continue
        elif singular in pretrained:
            entry = singular
        elif word == singular or word not in pretrained:
            raise ValueError('Word {} not found in vocabulary!'.format(word))
        vocab[word] = entry
        w.append(pretrained[entry])  # pretrained word vectors
        vocab_to_idx[word] = i
        i += 1
    vocab['edge'] = 'edge'
    w.append(pretrained['edge'])
    vocab_to_idx['edge'] = i
    return vocab_to_idx, np.stack(w)


def concepts_to_word_vectors(concept_dict, vocab, emb_size=50):
    num_concepts = len(concept_dict)
    vocab_map, v_embed = get_emb_matrix(vocab, 'data/glove.6B.50d.txt', emb_size)
    phrase_vectors = np.zeros(shape=(num_concepts, emb_size))
    for ct in concept_dict.values():
        _, words, idx = ct  # use the singular vocab words
        vector_value = 0
        for word in words:
            if 'wingbar' == word or 'wingbars' == word:
                widx = vocab_map['wing']
                widx2 = vocab_map['edge']
                vector_value = vector_value + v_embed[widx] + v_embed[widx2]
                continue
            if 'cheek-patch' == word:
                widx = vocab_map['cheek']
                widx2 = vocab_map['patch']
                vector_value = vector_value + v_embed[widx] + v_embed[widx2]
                continue
            if 'retrices' == word or 'tail-feathers' == word:
                widx = vocab_map['tail']
                widx2 = vocab_map['feather']
                vector_value = vector_value + v_embed[widx] + v_embed[widx2]
                continue
            vector_value = vector_value + v_embed[vocab_map[word]]
        phrase_vectors[idx] = vector_value
    np.save('data/concept_word_phrase_vectors.npy', phrase_vectors)
    return phrase_vectors


if __name__ == '__main__':
    config = config.Production if 'PRODUCTION' in os.environ else config.Debug
    db_client = MongoClient(config.MONGODB_DATABASE_URI).xplaindb
    selected_concepts_mapping, extracted_concepts, vocab_words, class_dict = extract_simple_concepts(db_client)
    top_concepts_per_image(db_client, selected_concepts_mapping, extracted_concepts, class_dict)
    concepts_to_word_vectors(selected_concepts_mapping, vocab_words)
