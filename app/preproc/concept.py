from abc import abstractmethod

from spacy.symbols import ADJ, NOUN, PROPN

from app.autoxplain.base.tokenize import tokenizer
from app.preproc.annotation import NounPhrase


class ConceptPreprocesser:
    def __init__(self):
        self.toknizr = tokenizer

    def tokenize(self, text):
        return self.toknizr(text)

    @abstractmethod
    def as_noun_phrase(self, text):
        pass


class DefaultConceptPreprocesser(ConceptPreprocesser):
    def as_noun_phrase(self, text):
        np = next(self.toknizr.analyze(text).noun_chunks)
        adjs, nouns = [], []
        for tok in np:
            curr_pos = tok.pos
            if curr_pos == ADJ:
                adjs.append(tok)
            elif curr_pos == NOUN or curr_pos == PROPN:
                nouns.append(tok)
        if not adjs:
            return None
        end_idx = len(adjs) + len(nouns)
        return NounPhrase(start=0, end=end_idx, root_noun=np.root, nouns=tuple(nouns), adjs=tuple(adjs))
