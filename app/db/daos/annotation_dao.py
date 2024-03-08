import string
from datetime import datetime

from bson import ObjectId
from pydantic import ValidationError
from pymongo import ASCENDING

from app import application
from app.db.daos.base import JoinableDAO, dao_update, dao_query, BaseDAO
from app.db.daos.concept_dao import ConceptDAO
from app.db.daos.label_dao import LabelDAO
from app.db.daos.user_dao import UserDAO
from app.db.models.annotation import Annotation
from app.db.models.payloads.annotation import AnnotationPayload
from app.db.stats.daos.image_prios import PrioStatsDAO
from app.db.stats.daos.image_stats import ImageStatsDAO
from app.preproc.annotation import DefaultAnnotationPreprocesser

punct_set = set(string.punctuation)


class AnnotationDAO(JoinableDAO):
    __slots__ = "preproc"

    def __init__(self):
        super().__init__("images", Annotation, AnnotationPayload, "objects.annotations")
        self.references = {
            'conceptIds': ('concepts', ConceptDAO, True),
            'createdBy': ('creator', UserDAO, False)
        }
        self.stat_references = ((ImageStatsDAO, PrioStatsDAO), None, None)

        self.create_index('anno_id_index', ('_id', ASCENDING))
        self.create_index('anno_concept_index', ('conceptIds', ASCENDING))

        self.preproc = DefaultAnnotationPreprocesser()

    def match_concepts(self, annotation, label_tokens, db_session):
        concept_ids = []
        concept_spans = []
        label_occurs = []
        for nouph in self.preproc.extract_noun_phrases(annotation, label_tokens):
            if isinstance(nouph, tuple):
                label_occurs.append(nouph[1])
                nouph = nouph[0]
                if nouph is None:
                    continue
            concept_ids.append(nouph)
            concept_spans.append((nouph.start, nouph.end))
        if concept_ids:
            if len(concept_ids) == 1:
                concept_ids[0] = ConceptDAO().find_doc_or_add(concept_ids[0], db_session=db_session)[1]['_id']
            else:
                for i, concept in enumerate(ConceptDAO().find_concepts_or_add(concept_ids, db_session=db_session)):
                    concept_ids[i] = concept['_id']
        return self.preproc.curr_tokens.copy(), concept_ids, concept_spans, label_occurs

    @staticmethod
    def create_token_mask(anno_tokens, label_idx, label_occurs, spans):
        """ Creates the mask that denotes the concept's positions in the list of tokens (of the annotation) """
        token_mask = [-1] * len(anno_tokens)
        # Add concept markers to the empty mask
        if spans:
            for i, (start, end) in enumerate(spans):
                # validate concept positions first
                token_mask[start:end] = (i for _ in range(start, end))
        # Add label markers to the mask
        if label_occurs:
            label_idx = - label_idx - 2
            for start, end in label_occurs:
                token_mask[start:end] = (label_idx for _ in range(start, end))
        return token_mask

    def prepare_annotation(self, annotation, label_idx, label_tokens, user_id=None, db_session=None):
        if not user_id:
            user_id = UserDAO().get_current_user_id()
        tokens, concept_ids, concept_spans, label_occurs = self.match_concepts(annotation, label_tokens, db_session)
        mask = self.create_token_mask(tokens, label_idx, label_occurs, concept_spans)
        return Annotation(id=ObjectId(), text=annotation, tokens=tokens, concept_mask=mask,
                          concept_ids=concept_ids, created_by=user_id)

    def _next_line(self, nouph, concept_ids, concept_spans):
        curr_concepts = concept_ids[-1]
        if curr_concepts or curr_concepts is None:
            if nouph is None:
                concept_ids.append([])
                concept_spans.append([])
            else:
                self._helper_list.append(nouph)
                concept_ids.append([nouph])
                concept_spans.append([(nouph.start, nouph.end)])
        else:
            curr_spans = concept_spans[-1]
            concept_ids[-1] = None
            concept_spans[-1] = None
            if nouph is not None:
                self._helper_list.append(nouph)
                curr_concepts.append(nouph)
                curr_spans.append((nouph.start, nouph.end))
            concept_ids.append(curr_concepts)
            concept_spans.append(curr_spans)

    def match_concepts_multi_annos(self, annotations, label_tokens, db_session):
        # multi-line annotation preprocessing: inputting a single larger doc to spacy is more efficient.
        concept_ids = [[]]
        concept_spans = [[]]
        label_occurs = [[]]
        joined_annos = annotations[0].strip()
        last_char = joined_annos[-1]
        if last_char == '.':
            annotations[0] = joined_annos
        else:
            if last_char in punct_set:
                joined_annos = joined_annos[:-1]
            joined_annos = joined_annos + '.'
            annotations[0] = joined_annos
        for i in range(1, len(annotations)):
            curr_anno = annotations[i].strip()
            last_char = curr_anno[-1]
            if last_char == '.':
                annotations[i] = curr_anno
            else:
                if last_char in punct_set:
                    curr_anno = curr_anno[:-1]
                curr_anno = curr_anno + '.'
                annotations[i] = curr_anno
            joined_annos = joined_annos + '\n' + curr_anno
        for nouph in self.preproc.extract_phrases_multi_line(joined_annos, label_tokens):
            if len(nouph) == 3:
                nouph, is_new_line, occur_idx = nouph
                if is_new_line:
                    label_occurs.append([occur_idx])
                else:
                    label_occurs[-1].append(occur_idx)
                if nouph is None:
                    if is_new_line:
                        self._next_line(nouph, concept_ids, concept_spans)
                    continue
            else:
                nouph, is_new_line = nouph
            if is_new_line:
                curr_occurs = label_occurs[-1]
                if curr_occurs or curr_occurs is None:
                    label_occurs.append([])
                else:
                    label_occurs[-1] = None
                    label_occurs.append(curr_occurs)
                self._next_line(nouph, concept_ids, concept_spans)
            else:
                self._helper_list.append(nouph)
                concept_ids[-1].append(nouph)
                concept_spans[-1].append((nouph.start, nouph.end))
        if self._helper_list:
            if len(self._helper_list) == 1:
                cid = ConceptDAO().find_doc_or_add(self._helper_list[0], db_session=db_session)[1]['_id']
                for cl in concept_ids:
                    if cl:
                        cl[0] = cid
                        break
            else:
                iidx = oidx = 0
                cl = concept_ids[oidx]
                for i, concept in enumerate(
                        ConceptDAO().find_concepts_or_add(self._helper_list, db_session=db_session)):
                    while not cl or iidx == len(cl):
                        oidx += 1
                        iidx = 0
                        cl = concept_ids[oidx]
                    cl[iidx] = concept['_id']
                    iidx += 1
            self._helper_list.clear()
        if len(annotations) > len(concept_ids):
            for _ in range(len(annotations) - len(concept_ids)):
                concept_ids.append(None)
                concept_spans.append(None)
                label_occurs.append(None)
        return self.preproc.curr_tokens.copy(), concept_ids, concept_spans, label_occurs

    def prepare_annotations(self, annotations, label_idx, label_tokens,
                            user_id=None, skip_val_errors=False, db_session=None):
        # TODO: create the option to delay processing of annotations in favor of the responsiveness towards
        #  clients (the frontend) or put the annotation processing into a separate module that works
        #  through a queue of incoming raw annotations.
        # TODO: collect concepts over all annotations and find_or_add all these concepts in one step
        #  (need to keep order of concepts in order to correctly assign concept IDs to annos)
        if not user_id:
            user_id = UserDAO().get_current_user_id()
        if annotations:
            if len(annotations) == 1:
                annotation = annotations[0]
                try:
                    annotations[0] = self.prepare_annotation(annotation, label_idx, label_tokens, user_id, db_session)
                except ValidationError as e:
                    if skip_val_errors:
                        application.logger.error(
                            f'Annotation skipped upon error: {e} ! Skipped annotation: "{annotation}"')
                        annotations.clear()
                    else:
                        raise e
            else:
                i = 0
                tokens, concept_ids, concept_spans, label_occurs = self.match_concepts_multi_annos(
                    annotations, label_tokens, db_session)
                for anno, toks, cids, spans, occurs in zip(tuple(annotations), tokens, concept_ids, concept_spans,
                                                           label_occurs):
                    if cids is None:
                        cids = self._helper_list
                    mask = self.create_token_mask(toks, label_idx, occurs, spans)
                    try:
                        annotations[i] = Annotation(id=ObjectId(), text=anno, tokens=toks, concept_mask=mask,
                                                    concept_ids=cids, created_by=user_id)
                    except ValidationError as e:
                        if skip_val_errors:
                            application.logger.error(
                                f'Annotation skipped upon error: {e} ! Skipped annotation: "{anno}"')
                            del annotations[i]
                            continue
                        else:
                            raise e
                    i += 1
        return annotations

    @dao_query()
    def unrolled(self):
        # TODO: could aggregate adjectives and nouns for each concept into one array for each type:
        #  https://www.mongodb.com/docs/manual/reference/operator/aggregation/lookup/#perform-an-uncorrelated-subquery-with--lookup
        self.join(unroll_depth=2)

    def find_by_annotator(self, user_id, projection=None, generate_response=False, db_session=None):
        """
        Find `Annotation`s that were created by user with given Id
        :param user_id: Id of the annotator user
        :param projection:
        :param generate_response:
        :param db_session:
        :return: List of annotations if found
        """
        return self.simple_match("createdBy", user_id, projection, generate_response, db_session)

    def find_by_concept(self, concept_id, projection=None, generate_response=False, db_session=None):
        """
        Find `Annotation`s that contain the given concept
        :param concept_id: Id of the concept
        :param projection:
        :param generate_response:
        :param db_session:
        :return: List of annotations if found
        """
        # field is an array, but mongodb knows to query a document, if the array contains user_id
        return self.simple_match("conceptIds", concept_id, projection, generate_response, db_session)

    @dao_query()
    def search_annotations(self, search_str):
        """
        Find `DetectedObject`s assigned to the image with the given Id
        :param search_str: string that must be contained in any annotation of the object
        :return: List of objects where string is in
        """
        self.unwind_nested_docs()
        self.add_agg_match('text', {"$regex": search_str})
        # self.add_text_search(search_str)
        # TODO: the above apparently only works on a hosted server? Try to make use of the TEXT index by
        #  implementing a text search query with $text but some things to consider:
        #  https://www.mongodb.com/basics/full-text-search

    def delete_all_by_annotator(self, user_id, generate_response=False, db_session=None):
        return self.delete_nested_doc_by_match('createdBy', user_id, generate_response, db_session)

    # @transaction
    def add(self, obj_id, annotation, doc_id, label_id, proj_id=None, generate_response=False, db_session=None):
        # TODO: automatically move old annotations of an image (append the image and object _id to these annotations)
        #  into an "archived" collection, if the image document reaches the limit of 16MB => however unlikely to be
        #  reached, since images are saved separately with gridfs
        user_id = UserDAO().get_current_user_id()
        label = LabelDAO().find_by_id(label_id, projection=('labelIdx', 'nameTokens'), db_session=db_session)
        label_idx, label_tokens = label['labelIdx'], label['nameTokens']
        from app.db.daos.work_history_dao import WorkHistoryDAO
        WorkHistoryDAO().update_or_add(doc_id, user_id, proj_id, db_session=db_session)
        anno = self.prepare_annotation(annotation, label_idx, label_tokens, user_id, db_session=db_session)
        return self.insert_doc(anno, (doc_id, obj_id), generate_response=generate_response, db_session=db_session)

    # @transaction
    def add_many(self, obj_id, annotations, doc_id, label_id, proj_id=None, generate_response=False, db_session=None):
        user_id = UserDAO().get_current_user_id()
        label = LabelDAO().find_by_id(label_id, projection=('labelIdx', 'nameTokens'), db_session=db_session)
        label_idx, label_tokens = label['labelIdx'], label['nameTokens']
        from app.db.daos.work_history_dao import WorkHistoryDAO
        WorkHistoryDAO().update_or_add(doc_id, user_id, proj_id, db_session=db_session)
        for i, annotation in enumerate(annotations):
            annotations[i] = self.prepare_annotation(annotation, label_idx, label_tokens,
                                                     user_id, db_session=db_session)
        return self.insert_docs(annotations, (doc_id, obj_id),
                                generate_response=generate_response, db_session=db_session)

    # @transaction
    def add_with_concepts(self, obj_id, annotation, label_id, concept_ids, concept_spans,
                          generate_response=False, db_session=None):
        # creates a new explanation annotation for the given object
        if len(concept_ids) == len(concept_spans):
            raise ValueError('The number of concepts does not match the concept starting indices!')
        user_id = UserDAO().get_current_user_id()
        label = LabelDAO().find_by_id(label_id, projection=('labelIdx', 'nameTokens'), db_session=db_session)
        concepts = ConceptDAO().find_many(concept_ids, projection=('_id', 'phraseWords'), db_session=db_session)
        label_idx, label_tokens = label['labelIdx'], label['nameTokens']
        tokens = self.preproc.tokenize(annotation)
        # TODO: also make user input the label occurrences?
        mask = self.create_token_mask(tokens, label_idx, label_tokens, concept_spans)
        concept_ids = [con['_id'] for con in concepts]
        anno = Annotation(obj_id=obj_id, text=annotation, tokens=tokens, concept_mask=mask,
                          concept_ids=concept_ids, created_by=user_id)
        return self.insert_doc(anno, obj_id, generate_response=generate_response, db_session=db_session)

    @dao_update(update_many=False)
    def update_text(self, anno_id, new_text):
        # TODO: recreate tokens, mask and concepts
        self.add_query("_id", anno_id)
        self.add_update('text', new_text)

    @staticmethod
    def _reconstruct_sentence_from_tokens(tokens, start, stop):
        concept_text, split = '', False
        for i in range(start, stop):
            tok = tokens[i]
            if split or (len(tok) == 1 and tok in punct_set):
                split = tok == '-'
            else:
                tok = ' ' + tok
            concept_text = concept_text + tok
        return concept_text

    @staticmethod
    def _update_concept_mask(new_cid, concepts, mask, start, stop):
        if concepts:
            last_overridden_idx = None
            curr_cidx = mask[start]  # concept idx at start
            if curr_cidx >= 0:
                # remove intersecting concept at start
                for i in range(start - 1, -1, -1):
                    if mask[i] == curr_cidx:
                        mask[i] = -1
                    else:
                        break
                last_overridden_idx = curr_cidx + 1
            else:
                if curr_cidx < -1:
                    # remove intersecting label marker at start, if present
                    is_intersecting = True
                    for i in range(start - 1, -1, -1):
                        val = mask[i]
                        if is_intersecting:
                            if val == curr_cidx:
                                mask[i] = -1
                            else:
                                is_intersecting = False
                        elif val >= 0:
                            last_overridden_idx = val + 1
                            break
                # retrieve first upcoming concept after start
                for i in range(start, len(mask)):
                    val = mask[i]
                    if val >= 0:
                        curr_cidx = val
                        last_overridden_idx = val if i >= stop else val + 1
                        break
                else:
                    curr_cidx = len(concepts)
            for i in range(start, stop):
                val = mask[i]
                if val > curr_cidx:
                    last_overridden_idx = val + 1
                mask[i] = curr_cidx
            if last_overridden_idx is None:
                concepts.append(new_cid)
            else:
                for i in range(curr_cidx, last_overridden_idx):
                    del concepts[i]
                concepts.insert(curr_cidx, new_cid)
                diff = last_overridden_idx - curr_cidx - 1
                is_intersecting = True
                for i in range(stop, len(mask)):
                    val = mask[i]
                    if val >= 0:
                        if is_intersecting and val == last_overridden_idx:
                            mask[i] = -1
                            continue
                        else:
                            mask[i] = val - diff
                    is_intersecting = False
        else:
            concepts.append(new_cid)
            # remove intersecting label markers at start and end
            rmv_val = mask[start]
            if rmv_val != -1:
                for i in range(start - 1, -1, -1):
                    if mask[i] == rmv_val:
                        mask[i] = -1
                    else:
                        break
            rmv_val = mask[stop]
            if rmv_val != -1:
                for i in range(stop, len(mask)):
                    if mask[i] == rmv_val:
                        mask[i] = -1
                    else:
                        break
            for i in range(start, stop):
                mask[i] = 0

    def add_or_update_concept_at_range(self, anno_id, token_range, generate_response=False, db_session=None):
        """
        Add a `Concept` with the given key or Id to the specified `Annotation` at the given range of tokens
        :param anno_id: Id of the annotation
        :param token_range: tuple of (start, stop) integers corresponding to token indices
        :param generate_response:
        :param db_session:
        :return: Update result
        """
        start = token_range[0]
        stop = token_range[1] + 1
        assert 0 <= start < stop
        anno = self.find_by_nested_id(anno_id, projection=('tokens', 'conceptMask', 'conceptIds'))
        tokens = anno.pop('tokens')
        concept_text = self._reconstruct_sentence_from_tokens(tokens, start, stop)
        concept_dao = ConceptDAO()
        np = concept_dao.preproc.as_noun_phrase(concept_text)
        if np is None:
            return None
        cid = concept_dao.find_doc_or_add(np, db_session)[1]['_id']
        mask = anno['conceptMask']
        assert stop <= len(mask)
        concepts = anno['conceptIds']
        self._update_concept_mask(cid, concepts, mask, start, stop)
        self._query_matcher['objects.annotations._id'] = anno_id
        self._set_field_op['objects.$[].annotations.$[x].conceptMask'] = mask
        self._set_field_op['objects.$[].annotations.$[x].conceptIds'] = concepts
        self._set_field_op['objects.$[].annotations.$[x].updatedAt'] = datetime.now()
        self._update_commands['$set'] = self._set_field_op
        self._field_check['x._id'] = anno_id
        self._array_filters.append(self._field_check)
        result = self.collection.update_one(self._query_matcher, self._update_commands,
                                            array_filters=self._array_filters, session=db_session)
        self._array_filters.clear()
        self._field_check.clear()
        self._update_commands.clear()
        self._set_field_op.clear()
        self._query_matcher.clear()
        return self.to_response(result, BaseDAO.UPDATE) if generate_response else result

    @dao_update(update_many=False)
    def add_concept_nouns_specified(self, anno_id, token_range, noun_token_idxs):
        """
        Add a `Concept` with the given key or Id to the specified `Annotation` at the given range of tokens
        :param anno_id: Id of the annotation
        :param token_range: Id of the annotation
        :param noun_token_idxs: Id or key of the concept
        :return: Update result
        """
        # TODO: add all words that are not stop words and not marked as nouns as adjectives
        return {"_id": anno_id}

    def delete_all(self, generate_response=False, db_session=None):
        raise NotImplementedError

    def delete_by_id(self, entity_id, generate_response=False, db_session=None):
        from app.db.daos.image_doc_dao import ImgDocDAO
        return ImgDocDAO().delete_by_id(entity_id, generate_response, db_session)

    def delete_many(self, ids, generate_response=False, db_session=None):
        from app.db.daos.image_doc_dao import ImgDocDAO
        return ImgDocDAO().delete_many(ids, generate_response, db_session)

    def simple_delete(self, key, value, generate_response=False, delete_many=True, db_session=None):
        # Attention: this deletes the entire image matching the query
        from app.db.daos.image_doc_dao import ImgDocDAO
        return ImgDocDAO().simple_delete(self._loc_prefix + key, value, generate_response, db_session, delete_many)
