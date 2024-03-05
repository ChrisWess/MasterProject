import io
import itertools
import logging
from collections import defaultdict

import torch
from transformers import BertTokenizer

from app.autoxplain.base import util
from app.autoxplain.base.preprocess import get_document

# from transformers.models.bert import BasicTokenizer

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
logger = logging.getLogger()

SENTENCE_ENDERS = "!.?"
SUBSCRIPT = str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉")

DOC_NAME = "<document_name>"

MODEL_NAME = 'droc_incremental_no_segment_distance'
WINDOW_SIZE = 384


class ProdAnnotater:
    def __init__(self, model_path, gpu_id=0, seed=None):
        if torch.cuda.is_available():
            self.gpu_id = gpu_id
            self.device = torch.device('cpu' if gpu_id is None else f'cuda:{gpu_id}')
        else:
            self.gpu_id = None
            self.device = torch.device('cpu')

        self.seed = seed
        if seed:
            util.set_seed(seed)

        self.config = util.initialize_config(MODEL_NAME, create_dirs=False)
        self.model = IncrementalCorefModel(self.config, self.device)
        self.model.to(self.device)
        self.tensorizer = Tensorizer(self.config)
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        logger.info(f'Loaded model from {model_path}')
        self.model.eval()
        # python -m spacy download de_core_news_md
        self.spacy_tok = spacy.load("de_core_news_md")
        # cls.basic_tokenizer = BasicTokenizer(do_lower_case=False)
        self.tokenizer = BertTokenizer.from_pretrained(self.config['bert_tokenizer_name'])
        self.tensorizer.long_doc_strategy = "keep"

    def preprocess(self, data):
        """
        Transform raw input into model input data.
        """
        # Take the input data and make it inference ready
        if isinstance(data, str):
            data = self.text_to_token_list(data)
        document = get_document('_', data, 'german', WINDOW_SIZE, self.tokenizer, 'nested_list')
        _, example = self.tensorizer.tensorize_example(document, is_training=False)[0]
        token_map = self.tensorizer.stored_info['subtoken_maps']['_']
        # Remove gold
        tensorized = [torch.tensor(e) for e in example[:7]]
        return tensorized, token_map, data

    @staticmethod
    def postprocess(results, token_map, tokenized_sentences, output_mode):
        # We only support a batch size of one!
        span_starts, span_ends, mention_to_cluster_id, predicted_clusters = results
        if output_mode == "raw":
            # TODO: not outputting the correct coreferences, even tho model worked correctly
            words = list(itertools.chain.from_iterable(tokenized_sentences))
            for cluster_id, cluster in enumerate(predicted_clusters):
                for pair in cluster:
                    words[pair[0]] = "[" + words[pair[0]]
                    words[pair[1]] = words[pair[1]] + "]" + str(cluster_id).translate(SUBSCRIPT)
            text = " ".join(words)
            # Pitiful attempt of fixing what whitespace tokenization removed
            # but its only meant for direct human usage, so it should be fine.
            for sentence_ender in SENTENCE_ENDERS + ",":
                text = text.replace(" " + sentence_ender, sentence_ender)
            return [text]
        elif output_mode == "conll":
            lines = [f"#begin document {DOC_NAME}"]
            for sentence_id, sentence in enumerate(tokenized_sentences, 1):
                for word_id, token in enumerate(sentence, 1):
                    line = ["memory_file", str(sentence_id), str(word_id), token] + ["-"] * 9
                    lines.append("\t".join(line))
                lines.append("\n")
            lines.append("#end document")
            input_file = io.StringIO(
                "\n".join(lines)
            )
            output_file = io.StringIO("")
            predictions = {
                DOC_NAME: predicted_clusters
            }
            token_maps = {
                DOC_NAME: token_map
            }
            output_conll(input_file, output_file, predictions, token_maps, False)
            return output_file.getvalue()
        elif output_mode == "json":
            # A lot of redundancy by the large amount of JSON keys
            # TODO: optimize format, could make another output_mode="json_small" (perhaps like the following):
            #   1) "tokens": list of all tokens
            #   2) "clusters": like predicted_clusters_words (list:cluster_ids of list:mentions of list:mention_range)
            cluster_member_ids = defaultdict(set)
            predicted_clusters_words = []
            for cluster_id, cluster in enumerate(predicted_clusters):
                current_cluster = []
                for pair in cluster:
                    token_from = token_map[pair[0]]
                    token_to = token_map[pair[1]]
                    current_cluster.append((token_from, token_to))
                    for i in range(token_from, token_to + 1):
                        cluster_member_ids[cluster_id].add(i)
                predicted_clusters_words.append(current_cluster)

            total_word_id = 0
            lines = []
            for sentence_id, sentence in enumerate(tokenized_sentences):
                for word_id, token in enumerate(sentence):
                    line = {'sentence': str(sentence_id + 1), 'word': str(word_id + 1), 'token': token}
                    for cluster_id, tok_id_set in cluster_member_ids.items():
                        if total_word_id in tok_id_set:
                            line['cluster_id'] = cluster_id
                            for mention_id, mention in enumerate(predicted_clusters_words[cluster_id]):
                                if mention[0] <= total_word_id <= mention[1]:
                                    line['mention_id'] = mention_id
                            break
                    lines.append(line)
                    total_word_id += 1
            return {'tokens': tokenized_sentences, 'clusters': lines}
        else:
            predicted_clusters_words = []
            for cluster in predicted_clusters:
                current_cluster = []
                for pair in cluster:
                    current_cluster.append((token_map[pair[0]], token_map[pair[1]]))
                predicted_clusters_words.append(current_cluster)
            if output_mode == "json_small":
                return {'tokens': tokenized_sentences, 'clusters': predicted_clusters_words}
            else:
                return predicted_clusters_words

    def predict(self, data, output_mode='raw', **kwargs):
        assert output_mode != "raw" or isinstance(data, str)
        in_data, token_map, tokenized_sentences = self.preprocess(data)
        marshalled_data = [d.to(self.device) for d in in_data]
        with torch.no_grad():
            results, probs = self.model(*marshalled_data, **kwargs)
        result = self.postprocess(results, token_map, tokenized_sentences, output_mode)
        if isinstance(result, dict):
            result['probs'] = probs
            return result
        else:
            return {'clusters': result, 'probs': probs}


model = ProdAnnotater("app/coref/base/model_saves/model_droc_incremental_no_segment_distance_May02_17-32-58_1800.bin")

if __name__ == '__main__':
    res = model.predict("TODO", "json")
    print(res)
