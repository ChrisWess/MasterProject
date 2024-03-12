from abc import abstractmethod
from enum import Enum

import inflect
from spacy.symbols import ADJ, NOUN, PROPN

from app.autoxplain.base.tokenize import tokenizer


class WordType(Enum):
    OTHER = 0
    ADJECTIVE = 1
    NOUN = 2


class LabelPreprocesser:
    def __init__(self):
        self.toknizr = tokenizer
        self._inflector = inflect.engine()

    def tokenize(self, text):
        return self.toknizr(text)

    @abstractmethod
    def analyze_label(self, text):
        pass

    @abstractmethod
    def preprocess_category(self, category):
        pass


class DefaultLabelPreprocesser(LabelPreprocesser):
    def analyze_label(self, text):
        for t in self.toknizr.analyze(text):
            pos = t.pos
            if pos == NOUN or pos == PROPN:
                yield t.lower_, t.lemma_, WordType.NOUN
            elif pos == ADJ:
                yield t.lower_, t.lemma_, WordType.ADJECTIVE
            else:
                yield t.lower_, t.lemma_, WordType.OTHER

    def preprocess_category(self, category):
        category = category.lower()
        if self.toknizr.has_tokens(category):
            result = []
            for token in self.toknizr.analyze(category):
                pos = token.pos
                if pos == NOUN or pos == PROPN:
                    singular = self._inflector.singular_noun(token.text)
                    if singular:
                        result.append(singular)
                    else:
                        result.append(token.text)
                else:
                    result.append(token.text)
            if result:
                # TODO: join hyphens without spaces around it
                return ' '.join(result), result
            else:
                return category
        else:
            singular = self._inflector.singular_noun(category)
            if singular:
                return singular
            else:
                return category
