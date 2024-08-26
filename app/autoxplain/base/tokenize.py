import re
import string

import spacy
from textblob import Word


def remove_punct(text):
    regex = re.compile('[' + re.escape(string.punctuation) + '0-9\\r\\t\\n]')  # Remove punctuation and numbers
    return regex.sub(" ", text)


def remove_non_ascii(text):
    return re.sub(r"[^\x00-\x7F]+", " ", text)  # Remove all words with any non-ASCII chars


class Tokenizer:
    def __init__(self, toknizr_id=None, keep_punct=True, uncased=True, ascii_hex_conversion=True):
        self.toknizr_id = toknizr_id
        self.keep_punct = keep_punct
        self.uncased = uncased
        self.convert_hex = ascii_hex_conversion
        self.toknizr = None

    @staticmethod
    def convert_ascii_hex(hex_repr):
        return bytes.fromhex(hex_repr[1:]).decode("ASCII")

    @staticmethod
    def has_tokens(text):
        # checks if the given string consists of multiple tokens (False if less-equal 1 token)
        return any(char.isspace() for char in text.strip())

    @staticmethod
    def lemmatize_token(text):
        # download the corpus with: python -m textblob.download_corpora
        return Word(text).lemmatize()

    def tokenize(self, text):
        if self.uncased:
            text = text.lower()
        text = remove_non_ascii(text)
        if self.convert_hex:
            ascii_hex_matches = re.findall(r"%[0-9A-F]{2}", text)
            for match in ascii_hex_matches:
                try:
                    text = re.sub(match, self.convert_ascii_hex(match), text)  # substitute ascii hex with ascii
                except UnicodeDecodeError:
                    text = re.sub(match, "", text)
        if not self.keep_punct:
            text = remove_punct(text)
        return text

    def __call__(self, text):
        return self.tokenize(text)


class SpacyTokenizer(Tokenizer):
    def __init__(self, toknizr_id='spacy', keep_punct=True, uncased=True):
        super().__init__(toknizr_id, keep_punct, uncased, False)
        if toknizr_id == 'spacy':
            # in case of OSError, in your python venv, execute this:-> python -m spacy download en_core_web_sm
            lang_model = 'en_core_web_sm'
        else:
            lang_model = toknizr_id.split('=')[1]
        self.toknizr = spacy.load(lang_model)

    def tokenize(self, text):
        text = super().tokenize(text)
        text = [token.text for token in self.toknizr.tokenizer(text)]
        return list(filter(lambda f: not re.match(r"\s+|^[^ia]$", f), text))

    def analyze(self, text, allow_non_ascii=False):
        if not allow_non_ascii:
            text = remove_non_ascii(text)
        return self.toknizr(text)

    @staticmethod
    def get_num_tokens(out):
        return len(out)


tokenizer = SpacyTokenizer(uncased=False)
