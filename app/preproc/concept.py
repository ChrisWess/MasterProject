from abc import abstractmethod

from spacy.symbols import ADJ, ADV, VERB, NOUN, PROPN, PRON

from app.autoxplain.base.tokenize import tokenizer
from app.preproc.annotation import NounPhrase, MyToken


class ConceptPreprocesser:
    def __init__(self):
        self.toknizr = tokenizer

    def tokenize(self, text):
        return self.toknizr(text)

    @abstractmethod
    def as_noun_phrase(self, text):
        pass


class DefaultConceptPreprocesser(ConceptPreprocesser):
    def __init__(self):
        super().__init__()
        self.adjs = []
        self.nouns = []

    def as_noun_phrase(self, text, allow_non_ascii=True):
        tokenized = self.toknizr.analyze(text, allow_non_ascii)
        start, end = 0, len(tokenized) - 1
        split_token = prev = None
        for token in tokenized:
            if split_token:
                split_pos = split_token.pos
                if split_pos == ADJ or split_pos == ADV or split_pos == VERB:
                    word_list = self.adjs
                else:
                    word_list = self.nouns
                token = MyToken(word_list.pop().text + prev.text + token.text, split_token.pos, token.i)
                split_token = None
                word_list.append(token)
            else:
                curr_pos = token.pos
                if token.lower_ == '-' and prev:
                    split_token = prev
                elif curr_pos == ADJ or curr_pos == ADV or curr_pos == VERB:
                    self.adjs.append(token)
                elif curr_pos == NOUN or curr_pos == PROPN or curr_pos == PRON:
                    self.nouns.append(token)
            prev = token
        if not self.adjs:
            return None
        adjs = tuple(self.adjs)
        self.adjs.clear()
        if len(self.nouns) > 1:
            nouns = tuple(self.nouns)
            self.nouns.clear()
            try:
                root = next(tokenized.noun_chunks).root
            except StopIteration:
                root = nouns[-1]
            return NounPhrase(start=start, end=end, root_noun=root, nouns=nouns, adjs=adjs)
        else:
            noun = self.nouns[0] if self.nouns else MyToken('subject', NOUN, end)
            self.nouns.clear()
            return NounPhrase(start=start, end=end, root_noun=noun, adjs=adjs)
