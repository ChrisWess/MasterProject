from abc import abstractmethod
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Union

from spacy.symbols import *
from spacy.tokens import Token

from app.autoxplain.base.tokenize import tokenizer

adj_candidates = {ADJ, VERB, ADV}
noun_candidates = {NOUN, PROPN}
conj_pos_labels = {CCONJ, PUNCT}
np_pos_labels = set()
np_pos_labels.update(adj_candidates, noun_candidates, (CCONJ,))
pos_fillers = {PART, DET, NUM, PUNCT}
final_punct = {'.', '!', '?'}


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
    def extract_noun_phrases(self, text, categories):
        pass

    @abstractmethod
    def extract_phrases_multi_line(self, lines, categories):
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

    def _process_np_token(self, root_noun, word, prev, start_idx, end_idx, split_token):
        if split_token:
            assert start_idx is not None
            replace_root = False
            if split_token.pos in adj_candidates:
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
                    if prev and prev.pos in adj_candidates or prev.pos in noun_candidates:
                        split_token = prev
                elif curr_pos in adj_candidates:
                    found = True
                    if start_idx is not None:
                        end_idx = word.i
                    self.adjs.append(word)
                elif curr_pos in noun_candidates:
                    found = True
                    if start_idx is not None:
                        end_idx = word.i
                    self.nouns.append(word)
                if found and start_idx is None:
                    start_idx = word.i
                self.noun_phrase_chunks.append(word)
        return root_noun, word, start_idx, end_idx, split_token

    def _process_phrase(self, np, root_noun, categories, real_start):
        start_idx = end_idx = split_token = prev = None
        for word in np[real_start:]:
            if np.end == word.i + 1 and not self.adjs:
                self.adjs.clear()
                self.nouns.clear()
                return None
            root_noun, word, start_idx, end_idx, split_token = self._process_np_token(
                root_noun, word, prev, start_idx, end_idx, split_token)
            prev = word
        if end_idx:
            end_idx += 1
        self.noun_phrase_chunks.clear()
        filt_adjs = tuple(adj for adj in self.adjs if len(adj.text) > 1)
        if len(filt_adjs) == 0:
            self.adjs.clear()
            self.nouns.clear()
            return None
        idx = 0
        while idx < len(self.nouns):
            noun = self.nouns[idx]
            if noun.lower_ in categories:
                if noun == root_noun:
                    root_noun = MyToken('subject', NOUN, noun.i)
                del self.nouns[idx]
            else:
                idx += 1
        return root_noun, filt_adjs, start_idx, end_idx

    def extract_noun_phrases(self, text, categories):
        # https://towardsdatascience.com/enhancing-keybert-keyword-extraction-results-with-keyphrasevectorizers-3796fa93f4db
        # https://stackoverflow.com/questions/57049737/how-can-i-extract-all-phrases-from-a-sentence
        self.curr_tokens.clear()
        tokenized = self.toknizr.analyze(text)
        # TODO: add the additional functionality from the multi-line version
        for np in tokenized.noun_chunks:
            # Noun chunks are spacy spans
            root_noun = np.root
            real_start = 0
            for token in np:
                if token.pos in pos_fillers:
                    real_start += 1
                else:
                    break
            np_size = len(np) - real_start
            if np_size <= 1:
                continue
            # TODO: also check retrospectively, if any adjectives were left out (do not belong to noun phrases),
            #  because in this work, they almost always refer to the object in question!
            #  => Can spacy show to which noun an adjective refers to?
            # TODO: Join noun phrases if they belong to each other (with e.g. "and/or" => "white belly and breast")
            #  => should also be able to handle enumerations (e.g. black wings, beak, back and head): make adj and
            #  noun pairs from this like (black wings), (black beak) etc.
            #  "beak" should be able to refer to the concept "black beak", although it takes up only 1 token
            #  in the annotation text.
            # TODO: if an adverb is in front of an adjective (e.g. "very"), is it worth to include?
            #  Processes more information, but disadvantage is that concepts get more complex
            #  => it would be nice to identify very similar concepts as the same concepts.
            # TODO: https://stackoverflow.com/questions/3788870/how-to-check-if-a-word-is-an-english-word-with-python
            #  Try to enforce spell checking as much as possible in the frontend, but just use a suggest()
            #  function like shown in the link and select the top suggestion in the backend as a last resort,
            #  when encountering a spelling error.
            proc_res = self._process_phrase(np, root_noun, categories, real_start)
            if proc_res is None:
                continue
            root_noun, filt_adjs, start_idx, end_idx = proc_res
            if len(self.nouns) > 1:
                np = NounPhrase(start=start_idx, end=end_idx, root_noun=root_noun,
                                nouns=tuple(self.nouns), adjs=filt_adjs)
            else:
                np = NounPhrase(start=start_idx, end=end_idx, root_noun=root_noun, adjs=filt_adjs)
            # TODO: noun phrase might contain something like "it has/is ..." or "which has/is ...", then the
            #  adjectives clearly refer to the subject and a noun might be omitted, however the latter case
            #  might not be a noun phrase (maybe save these edge cases and try to analyze them separately/manually).
            #  Cases like "it is blue" typically means that its body/fur/outer color is blue.
            #  Exchange all cases like "it/which" with the default string "subject", if this has
            #  adjectives assigned and save them for later analysis.
            yield np
            self.adjs.clear()
            self.nouns.clear()
        for tok in tokenized:
            self.curr_tokens.append(tok.lower_)

    def _check_noun_context_multi_line(self, doc, root_noun, prev_np, end_idx, line_start, line_end, no_skip_start):
        # Make sure to not stray to far away from the relevant words (nouns)
        if no_skip_start:
            # Check in front of the noun
            idx = root_noun.i - 1
            new_start = None
            is_at_start = False
            if end_idx is not None:
                until_idx = end_idx
            elif idx >= line_start:
                until_idx = line_start
                is_at_start = True
            else:
                until_idx = idx + 1
            while idx >= until_idx:
                word = doc[idx]
                curr_pos = word.pos
                if curr_pos in adj_candidates:
                    self.adjs.append(word)
                elif curr_pos not in conj_pos_labels or word.text in final_punct:
                    break
                idx -= 1
            else:
                if prev_np and not (self.adjs or is_at_start):
                    self.adjs.extend(prev_np.adjs)
                    new_start = root_noun.i
            if self.adjs:
                if new_start is None:
                    new_start = self.adjs[0].i
                self.nouns.append(root_noun)
                return new_start, root_noun.i + 1
        # Check behind the noun
        idx = root_noun.i + 1
        tnext = doc[idx].lower_
        if tnext == 'is':
            idx += 1
            while idx < line_end:
                word = doc[idx]
                curr_pos = word.pos
                if curr_pos == ADJ or curr_pos == ADV:
                    self.adjs.append(word)
                else:
                    break
                idx += 1
            if self.adjs:
                self.nouns.append(root_noun)
                return root_noun.i, self.adjs[-1].i + 1
        # elif type(root_noun) is not MyToken and tnext == 'has':
        return None

    def extract_phrases_multi_line(self, lines, categories):
        self.curr_tokens.clear()
        tokenized = self.toknizr.analyze(lines)
        line_idxs = deque()
        self.curr_tokens.append([])
        for tok in tokenized:
            t = tok.lower_
            if t == '\n':
                line_idxs.append(tok.i)
                self.curr_tokens.append([])
            else:
                self.curr_tokens[-1].append(t)
        end_idx = prev_np = None
        line_start = 0
        line_end = line_idxs.popleft() if line_idxs else None
        line_ended = False
        for np in tokenized.noun_chunks:
            root_noun = np.root
            if root_noun.i > line_end:
                if line_ended:
                    yield None, line_ended
                else:
                    line_ended = True
                while line_idxs:
                    line_start = line_end + 1
                    line_end = line_idxs.popleft()
                    if root_noun.i > line_end:
                        yield None, line_ended
                    else:
                        break
                else:
                    line_start = line_end + 1
                    line_end = len(tokenized)
            if end_idx and np.start <= end_idx:
                continue
            real_start = 0
            for token in np:
                if token.pos in pos_fillers:
                    real_start += 1
                else:
                    break
            np_size = len(np) - real_start
            if not np_size:
                continue
            if np_size == 1:
                if root_noun.lower_ in categories or root_noun.pos == PRON:
                    root_noun = MyToken('subject', NOUN, root_noun.i)
                context = self._check_noun_context_multi_line(tokenized, root_noun, prev_np, end_idx,
                                                              line_start, line_end, real_start == 0)
                if context is None:
                    continue
                filt_adjs = tuple(adj for adj in self.adjs if len(adj.text) > 1)
                if len(filt_adjs) == 0:
                    self.adjs.clear()
                    self.nouns.clear()
                    continue
                start_idx, end_idx = context
            else:
                proc_res = self._process_phrase(np, root_noun, categories, real_start)
                if proc_res is None:
                    continue
                root_noun, filt_adjs, start_idx, end_idx = proc_res
            if len(self.nouns) > 1:
                np = NounPhrase(start=start_idx - line_start, end=end_idx - line_start, root_noun=root_noun,
                                nouns=tuple(self.nouns), adjs=filt_adjs)
            else:
                np = NounPhrase(start=start_idx - line_start, end=end_idx - line_start,
                                root_noun=root_noun, adjs=filt_adjs)
            yield np, line_ended
            line_ended = False
            prev_np = np
            self.adjs.clear()
            self.nouns.clear()
