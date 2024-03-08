from abc import abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Union

from spacy.symbols import *
from spacy.tokens import Token

from app.autoxplain.base.tokenize import tokenizer

np_pos_labels = {ADJ, NOUN, PROPN, PRON, NUM, CCONJ, PUNCT}


@dataclass
class MyToken:
    token: str
    pos: int
    i: int
    lower: str = field(init=False)

    def __post_init__(self) -> None:
        self.lower = self.token.lower()

    @property
    def lemma_(self) -> str:
        return self.lower

    @property
    def lower_(self) -> str:
        return self.lower

    @property
    def text(self) -> str:
        return self.token


@dataclass(slots=True)
class NounPhrase:
    start: int
    end: int
    adjs: tuple[Union[Token, MyToken]]
    root_noun: Union[Token, MyToken] = "subject"
    nouns: Optional[tuple[Union[Token, MyToken]]] = None
    size: int = field(init=False)

    def __post_init__(self) -> None:
        self.size = 1 + len(self.adjs) if self.nouns is None else len(self.nouns) + len(self.adjs)


class AnnotationPreprocesser:
    def __init__(self):
        self.toknizr = tokenizer
        self.curr_tokens = []
        self.noun_phrase_chunks = []

    def tokenize(self, annotation):
        return self.toknizr(annotation)

    @abstractmethod
    def extract_noun_phrases(self, text, label_tokens):
        pass

    @abstractmethod
    def extract_phrases_multi_line(self, lines, label_tokens):
        pass


class DefaultAnnotationPreprocesser(AnnotationPreprocesser):
    """
    The Default Preprocessers all contain a lot of hand-crafted rule-based procedures.
    A lot of work could be put into creating more effective Preprocessers, which might use
    very sophisticated NN models to extract the concepts with a much higher reliability.
    """

    def __init__(self):
        super().__init__()
        self.adjs = []
        self.nouns = []

    def extract_noun_phrases(self, text, label_tokens):
        # https://towardsdatascience.com/enhancing-keybert-keyword-extraction-results-with-keyphrasevectorizers-3796fa93f4db
        # https://stackoverflow.com/questions/57049737/how-can-i-extract-all-phrases-from-a-sentence
        label_tokset = set(label_tokens)
        self.curr_tokens.clear()
        tokenized = self.toknizr.analyze(text)
        skip = False
        for np in tokenized.noun_chunks:
            # Noun chunks are spacy spans
            if len(np) == 1:
                continue
            root_noun = np.root
            # TODO: Join noun phrases if they belong to each other (with e.g. "and/or" => "white belly and breast")
            #  => should also be able to handle enumerations (e.g. black wings, beak, back and head): make adj and
            #  noun pairs from this like (black wings), (black beak) etc.
            #  "beak" should be able to refer to the concept "black beak", although it takes up only 1 token
            #  in the annotation text.
            start_idx = end_idx = label_span = split_token = prev = None
            filtered_nouph = []
            for word in np:
                if np.end == word.i + 1 and not self.adjs and not self.nouns:
                    skip = True
                    break
                if split_token:
                    assert start_idx is not None
                    replace_root = False
                    if split_token.pos == ADJ:
                        word_list = self.adjs
                    else:
                        replace_root = split_token == root_noun or word == root_noun
                        word_list = self.nouns
                    end_idx = word.i
                    word = MyToken(word_list.pop().text + prev.text + word.text, split_token.pos, end_idx)
                    if replace_root:
                        root_noun = word
                    split_token = None
                    word_list.append(word)
                else:
                    curr_pos = word.pos
                    # TODO: if an adverb is in front of an adjective (e.g. "very"), is it worth to include?
                    #  Processes more information, but disadvantage is that concepts get more complex
                    #  => it would be nice to identify very similar concepts as the same concepts.
                    if curr_pos in np_pos_labels:
                        found = False
                        # TODO: https://stackoverflow.com/questions/3788870/how-to-check-if-a-word-is-an-english-word-with-python
                        #  Try to enforce spell checking as much as possible in the frontend, but just use a suggest()
                        #  function like shown in the link and select the top suggestion in the backend as a last resort,
                        #  when encountering a spelling error.
                        if word.lower_ == '-':
                            if prev and (prev.pos == ADJ or prev.pos == NOUN or prev.pos == PROPN):
                                split_token = prev
                        elif curr_pos == ADJ:
                            # TODO: Adjectives are often mistaken for Verbs (and in consequence, other adjectives
                            #  are then often mistaken for Adverbs). How to fix this? Best way would be to check
                            #  a noun phrase with verbs and adverbs again, if it is more likely that they are
                            #  actually adjectives or if the NLP model is certain that it must be a verb.
                            #  But what tool to use to achieve this?
                            found = True
                            if start_idx is not None:
                                end_idx = word.i
                            self.adjs.append(word)
                        elif curr_pos == NOUN or curr_pos == PROPN or curr_pos == PRON:
                            found = True
                            if start_idx is not None:
                                end_idx = word.i
                            self.nouns.append(word)
                        if found and start_idx is None:
                            start_idx = word.i
                        filtered_nouph.append(word.text)
                prev = word
            if skip:
                skip = False
                continue
            if end_idx:
                end_idx += 1
            if self.nouns:
                # TODO: if we find a label and it has additional adjectives assigned, then return
                #  label idx and noun phrase with default noun ("subject")
                # TODO: also check retrospectively, if any adjectives were left out (do not belong to noun phrases),
                #  because in this work, they almost always refer to the object in question!
                #  => Can spacy show to which noun an adjective refers to?
                curr_token_set = {tok.lower() for tok in filtered_nouph}
                # check if the noun did equal or partly equal the label
                if label_tokset.issubset(curr_token_set):
                    label_span = (self.nouns[0].i, self.nouns[-1].i + 1)
            filt_adjs = tuple(adj for adj in self.adjs if len(adj.text) > 1)
            if len(filt_adjs) == 0:
                if label_span is not None:
                    yield None, label_span
                self.adjs.clear()
                self.nouns.clear()
                continue
            self.noun_phrase_chunks.append(filtered_nouph)
            if len(self.nouns) > 1:
                np = NounPhrase(start=start_idx, end=end_idx, root_noun=root_noun,
                                nouns=tuple(self.nouns), adjs=filt_adjs)
            elif len(self.nouns) == 1:
                # TODO: noun phrase should contain something like "it has/is ..." or "which has/is ...", then the
                #  adjectives clearly refer to the subject and a noun might be omitted, however the latter case
                #  might not be a noun phrase (maybe save these edge cases and try to analyze them separately/manually).
                #  Cases like "it is blue" typically means that its body/fur/outer color is blue.
                #  Exchange all cases like "it/which" with the default string "subject", if this has
                #  adjectives assigned and save them for later analysis.
                assert self.nouns[0] == root_noun, \
                    f'Noun "{self.nouns[0]}" in the noun list should be the root "{root_noun}"!'
                np = NounPhrase(start=start_idx, end=end_idx, root_noun=root_noun, adjs=filt_adjs)
            else:
                np = NounPhrase(start=start_idx, end=end_idx,
                                root_noun=MyToken('subject', NOUN, end_idx), adjs=filt_adjs)
            if label_span:
                yield np, label_span
            else:
                yield np
            self.adjs.clear()
            self.nouns.clear()
        for tok in tokenized:
            self.curr_tokens.append(tok.lower_)

    def extract_phrases_multi_line(self, lines, label_tokens):
        label_tokset = set(label_tokens)
        self.curr_tokens.clear()
        tokenized = self.toknizr.analyze(lines)
        filtered_nouph, line_idxs = [], deque()
        self.curr_tokens.append([])
        for tok in tokenized:
            t = tok.lower_
            if t == '\n':
                line_idxs.append(tok.i)
                self.curr_tokens.append([])
            else:
                self.curr_tokens[-1].append(t)
        line_start = 0
        line_end = line_idxs.popleft() if line_idxs else None
        skip = line_ended = False
        for np in tokenized.noun_chunks:
            if len(np) == 1:
                continue
            root_noun = np.root
            start_idx = end_idx = label_span = split_token = prev = None
            filtered_nouph.clear()
            for word in np:
                if np.end == word.i + 1 and not self.adjs and not self.nouns:
                    skip = True
                    break
                if word.i > line_end:
                    if line_ended:
                        yield None, line_ended
                    else:
                        line_ended = True
                    while line_idxs:
                        line_start = line_end + 1
                        line_end = line_idxs.popleft()
                        if word.i > line_end:
                            yield None, line_ended
                        else:
                            break
                    else:
                        line_start = line_end + 1
                        line_end = len(tokenized)
                if split_token:
                    assert start_idx is not None
                    replace_root = False
                    if split_token.pos == ADJ:
                        word_list = self.adjs
                    else:
                        replace_root = split_token == root_noun or word == root_noun
                        word_list = self.nouns
                    end_idx = word.i
                    word = MyToken(word_list.pop().text + prev.text + word.text, split_token.pos, end_idx)
                    if replace_root:
                        root_noun = word
                    split_token = None
                    word_list.append(word)
                else:
                    curr_pos = word.pos
                    if curr_pos in np_pos_labels:
                        found = False
                        if word.lower_ == '-':
                            if prev and (prev.pos == ADJ or prev.pos == NOUN or prev.pos == PROPN):
                                split_token = prev
                        elif curr_pos == ADJ:
                            found = True
                            if start_idx is not None:
                                end_idx = word.i
                            self.adjs.append(word)
                        elif curr_pos == NOUN or curr_pos == PROPN or curr_pos == PRON:
                            found = True
                            if start_idx is not None:
                                end_idx = word.i
                            self.nouns.append(word)
                        if found and start_idx is None:
                            start_idx = word.i
                        filtered_nouph.append(word.text)
                prev = word
            if skip:
                skip = False
                continue
            if end_idx:
                end_idx += 1
            if self.nouns:
                curr_token_set = {tok.lower() for tok in filtered_nouph}
                if label_tokset.issubset(curr_token_set):
                    label_span = (self.nouns[0].i - line_start, self.nouns[-1].i - line_start + 1)
            filt_adjs = tuple(adj for adj in self.adjs if len(adj.text) > 1)
            if len(filt_adjs) == 0:
                if label_span is not None:
                    yield None, line_ended, label_span
                    line_ended = False
                self.adjs.clear()
                self.nouns.clear()
                continue
            if len(self.nouns) > 1:
                np = NounPhrase(start=start_idx - line_start, end=end_idx - line_start, root_noun=root_noun,
                                nouns=tuple(self.nouns), adjs=filt_adjs)
            elif len(self.nouns) == 1:
                assert self.nouns[0] == root_noun, \
                    f'Noun "{self.nouns[0]}" in the noun list should be the root "{root_noun}"!'
                np = NounPhrase(start=start_idx - line_start, end=end_idx - line_start,
                                root_noun=root_noun, adjs=filt_adjs)
            else:
                np = NounPhrase(start=start_idx - line_start, end=end_idx - line_start,
                                root_noun=MyToken('subject', NOUN, end_idx), adjs=filt_adjs)
            if label_span:
                yield np, line_ended, label_span
            else:
                yield np, line_ended
            line_ended = False
            self.adjs.clear()
            self.nouns.clear()
