from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING

from app import mdb, application
from app.db.daos.base import BaseDAO
from app.db.daos.corpus_dao import CorpusDAO
from app.db.daos.manage_index import LabelIndexManager
from app.db.models.category import Category
from app.db.models.label import Label
from app.db.models.payloads.label import LabelPayload
from app.preproc.label import WordType, DefaultLabelPreprocesser


class LabelDAO(BaseDAO):
    __slots__ = "categories", "_category_set", "_lookup_pipeline", "_label_lookup", "preproc"

    def __init__(self):
        # Initialize mongodb collection of documents
        super().__init__("labels", Label, LabelPayload)
        self.create_index('name_index', ("name", ASCENDING), unique=True)
        self.create_index('label_index', ("labelIdx", ASCENDING), unique=True)

        self.categories = mdb.categories
        self._category_set = set()
        self._lookup_pipeline = []
        self._label_lookup = {"$lookup": {"from": "labels", "localField": 'labelIdxRefs',
                                          "foreignField": "labelIdx", "as": 'labels'}}

        self.preproc = DefaultLabelPreprocesser()

    def find_by_index(self, label_idx, projection=None, generate_response=False, db_session=None):
        """
        Find the Label with the given unique index
        :param label_idx: the index of the label
        :param projection:
        :param generate_response:
        :param db_session:
        :return: Label object at the given index
        """
        return self.simple_match("labelIdx", label_idx, projection, generate_response, db_session, find_many=False)

    def find_by_name(self, name, projection=None, generate_response=False, db_session=None):
        """
        Find the Label with the given name
        :param name: name of the entity behind the label
        :param projection:
        :param generate_response:
        :param db_session:
        :return: Label object with the given name
        """
        return self.simple_match("name", name, projection, generate_response, db_session, find_many=False)

    def find_dynamic(self, label, projection=None, generate_response=False, db_session=None):
        """
        Find the Label with the given name
        :param label: name of the entity behind the label
        :param projection:
        :param generate_response:
        :param db_session:
        :return: Label object with the given name
        """
        if isinstance(label, int):
            return self.find_by_index(label, projection=projection,
                                      generate_response=generate_response, db_session=db_session)
        else:
            try:
                result = self.find_by_id(ObjectId(label), projection=projection,
                                         generate_response=generate_response, db_session=db_session)
                if result is None:
                    return self.find_by_name(label, projection=projection,
                                             generate_response=generate_response, db_session=db_session)
                return result
            except InvalidId:
                return self.find_by_name(label, projection=projection,
                                         generate_response=generate_response, db_session=db_session)

    def _process_category(self, category, db_session=None):
        category = self.preproc.preprocess_category(category)
        if isinstance(category, tuple):
            category, tokens = category
            corpus = CorpusDAO()
            for token in tokens:
                corpus.find_doc_or_add(token, True, db_session=db_session)
        return category

    def _process_label_name(self, name, db_session=None):
        if self.preproc.toknizr.has_tokens(name):
            tokens = []
            for data in self.preproc.analyze_label(name):
                tokens.append(data)
            name = ' '.join(t[0] for t in tokens)
            self._query_matcher['name'] = name
            try:
                self.collection.find(self._query_matcher, session=db_session).next()
                self._query_matcher.clear()
                raise ValueError(f'Label with name "{name}" does already exist!')
            except StopIteration:
                self._query_matcher.clear()

            txt_idxs = []
            corpus = CorpusDAO()
            for i, (token, lemma, wtype) in enumerate(tokens):
                is_noun = wtype is not WordType.ADJECTIVE
                # TODO: When encountering multiple nouns, save them as noun chunks. Since a label represents
                #  one object, save the entire label tokens also as a noun chunk (marked as proper noun)
                txt_idxs.append(corpus.find_doc_or_add(token, is_noun, lemma, db_session=db_session)[1]['index'])
                tokens[i] = token
        else:
            name = name.lower()
            self._query_matcher['name'] = name
            try:
                self.collection.find(self._query_matcher, session=db_session).next()
                self._query_matcher.clear()
                raise ValueError(f'Label with name "{name}" does already exist!')
            except StopIteration:
                self._query_matcher.clear()
            word = CorpusDAO().find_doc_or_add(name, True, db_session=db_session)[1]
            txt_idxs = [word['index']]
            tokens = [name]
        return tokens, txt_idxs

    # @transaction
    def add(self, name, categories, generate_response=False, db_session=None):
        # creates a new label in the labels collection
        tokens, txt_idxs = self._process_label_name(name, db_session)
        if categories is None:
            categories = self._helper_list
        elif type(categories) is list:
            for c in categories:
                self._category_set.add(self._process_category(c, db_session))
            categories.clear()
            for category in self._category_set:
                categories.append(category)
        elif isinstance(categories, str):
            self._helper_list.append(self._process_category(categories, db_session))
            categories = self._helper_list
        else:
            raise ValueError('Categories are neither one string nor a list of such: ' + categories)
        label_idx = LabelIndexManager().get_incremented_index(db_session)
        label = Label(label_idx=label_idx, name=name, name_tokens=tokens, token_idxs=txt_idxs, categories=categories)
        response = self.insert_doc(label, generate_response=generate_response, db_session=db_session)
        for category in categories:
            try:
                self._add_category(category, label_idx, db_session)
                application.logger.info(f'New category "{category}" has been added!')
            except ValueError:
                self._add_label_ref_to_category(category, label_idx, db_session)
        self._helper_list.clear()
        self._category_set.clear()
        return response

    # @transaction
    def add_many(self, names, categories, generate_response=False, db_session=None):
        # creates multiple new labels in the labels collection
        num_new_docs = len(names)
        assert num_new_docs == len(categories)
        start_idx = LabelIndexManager().multi_increment_index(num_new_docs, db_session)
        for i, (name, categors) in enumerate(zip(names, categories)):
            tokens, txt_idxs = self._process_label_name(name, db_session)
            assert type(categors) is list
            for c in categors:
                self._category_set.add(self._process_category(c, db_session))
            categors.clear()
            for category in self._category_set:
                categors.append(category)
            self._category_set.clear()
            label_idx = start_idx + i
            self._helper_list.append(Label(label_idx=label_idx, name=name, name_tokens=tokens,
                                           token_idxs=txt_idxs, categories=categors))
        response = self.insert_docs(self._helper_list, generate_response=generate_response, db_session=db_session)
        self._helper_list.clear()
        for i, categors in enumerate(categories):
            label_idx = start_idx + i
            for category in categors:
                try:
                    self._add_category(category, label_idx, db_session)
                    application.logger.info(f'New category "{category}" has been added!')
                except ValueError:
                    self._add_label_ref_to_category(category, label_idx, db_session)
        return response

    def add_category_to_label(self, category, label, db_session=None):
        """
        Add the given category to the label's categories. If the category does not exist yet, create it.
        :param category: the string of the category
        :param label: Label index, ID or name
        :param db_session:
        :return: The category document, if it exists else None
        """
        label_idx = self.find_dynamic(label, projection='labelIdx', db_session=db_session)
        if label_idx is None:
            raise ValueError(f'No Label with information "{label}" could be found!')
        else:
            label_idx = label_idx['labelIdx']
        category = self._process_category(category, db_session)
        try:
            self._add_category(category, label_idx)
            application.logger.info(f'New category "{category}" has been added!')
        except ValueError:
            self._add_label_ref_to_category(category, label_idx, db_session)
        return category

    def remove_category_from_label(self, category, label, delete_if_unreferenced=False, db_session=None):
        """
        Remove the given category from the label's categories.
        :param category: the string of the category
        :param label: Either label index or the label ID
        :param delete_if_unreferenced: If True, when the category is not assigned to any labels
                                       after the removal, delete the category.
        :param db_session:
        :return: The category document, if it exists else None
        """
        self._query_matcher['categories'] = category
        if isinstance(label, int):
            self._query_matcher['labelIdx'] = label
        elif isinstance(label, str):
            self._query_matcher['name'] = label
        else:
            self._query_matcher['_id'] = label
        self._projection_dict['labelIdx'] = 1
        label_idx = self.collection.find_one(self._query_matcher, self._projection_dict, session=db_session)
        self._projection_dict.clear()
        self._query_matcher.clear()
        if label_idx is None:
            raise ValueError(f'No Label with identifier "{label}" and with category "{category}" could be found!')
        else:
            label_idx = label_idx['labelIdx']
        self.array_update('categories', category, ('labelIdx', label_idx), False, True, True, db_session)
        if delete_if_unreferenced:
            category_doc = self.find_category(category, db_session=db_session)
            if len(category_doc['labelIdxRefs']) == 1:
                self._query_matcher['_id'] = category
                self.categories.delete_one(self._query_matcher, session=db_session)
                self._query_matcher.clear()
                return category
        self._query_matcher['_id'] = category
        self._pull_op['labelIdxRefs'] = label_idx
        self._update_commands['$pull'] = self._pull_op
        self.categories.update_one(self._query_matcher, self._update_commands, session=db_session)
        self._pull_op.clear()
        self._update_commands.clear()
        self._query_matcher.clear()

    def find_all_categories(self, unroll_labels=False, generate_response=False, db_session=None):
        if unroll_labels:
            self._lookup_pipeline.append(self._label_lookup)
            if self._sort_list:
                self._agg_sorter.clear()
                self._agg_sorter.update(self._sort_list)
                self._lookup_pipeline.append(self._agg_sort)
            if self._limit_results:
                self._lookup_pipeline.append(self._limit_agg)
            result = list(self.categories.aggregate(self._lookup_pipeline, session=db_session))
            for category in result:
                labels = category['labels']
                for i, label in enumerate(labels):
                    labels[i] = self.payload_model(**label).to_dict()
            self._lookup_pipeline.clear()
            self._sort_list.clear()
            self._limit_results = None
        else:
            result = list(self._apply_sort_limit(self.categories.find(session=db_session)))
        if generate_response:
            return {"result": result, "numResults": len(result), "status": 200,
                    'model': 'Category', 'isComplete': True}
        else:
            return result

    def find_category(self, category, unroll_labels=False, generate_response=False, db_session=None):
        """
        Find the Category with the given name
        :param category: the string of the category
        :param unroll_labels:
        :param generate_response:
        :param db_session:
        :return: The category document, if it exists else None
        """
        if unroll_labels:
            self._query_matcher['_id'] = category
            self._agg_query = self._query_matcher
            self._lookup_pipeline.append(self._match_agg_clause)
            result = self.find_all_categories(True, False, db_session)
            self._query_matcher.clear()
            if result:
                result = result[0]
                labels = result['labels']
                for i, label in enumerate(labels):
                    labels[i] = self.payload_model(**label).to_dict()
            else:
                result = None
        else:
            self._query_matcher['_id'] = category
            result = self.categories.find_one(self._query_matcher, session=db_session)
            self._query_matcher.clear()
        if generate_response and result:
            return {"result": result, "numResults": 1, "status": 200,
                    'model': 'Category', 'isComplete': True}
        else:
            return result

    def find_by_category(self, category, projection=None, generate_response=False, db_session=None):
        """
        Find all labels that belong to the given category
        :param category: category of the label
        :param projection:
        :param generate_response:
        :param db_session:
        :return: Labels with the given category
        """
        self._query_matcher['_id'] = category
        category = self.categories.find_one(self._query_matcher, session=db_session)
        self._query_matcher.clear()
        self._in_query['$in'] = category['labelIdxRefs']
        self._query_matcher['labelIdx'] = self._in_query
        projection = self.build_projection(projection)
        result = list(self._apply_sort_limit(self.collection.find(self._query_matcher, projection, session=db_session)))
        self._in_query.clear()
        self._query_matcher.clear()
        return self.to_response(result) if generate_response else result

    def category_names(self, db_session=None):
        # TODO: this returned list should be presented as a dropdown menu in the frontend.
        #  After choosing a category from dropdown, only labels of that category are presented in
        #  the label-dropdown menu.
        # TODO: Usually sort in the Frontend (always a good idea to outsource as much functionality
        #  to the frontend as possible to relieve the server's utilization)
        self._projection_dict['_id'] = 1
        result = [doc['_id'] for doc in self._apply_sort_limit(self.categories.find(session=db_session))]
        self._projection_dict.clear()
        return result

    def _add_label_ref_to_category(self, category, label_idx, db_session=None):
        self._query_matcher['_id'] = category
        self._push_op['labelIdxRefs'] = label_idx
        self._update_commands['$push'] = self._push_op
        result = self.categories.update_one(self._query_matcher, self._update_commands, session=db_session)
        self._push_op.clear()
        self._update_commands.clear()
        self._query_matcher.clear()
        return result

    def _add_category(self, category, label_idx=None, db_session=None):
        self._query_matcher['_id'] = category
        try:
            self.categories.find(self._query_matcher, session=db_session).next()
            self._query_matcher.clear()
            raise ValueError(f'A category with name "{category}" does already exist!')
        except StopIteration:
            self._query_matcher.clear()
        self._query_matcher.clear()
        CorpusDAO().find_doc_or_add(category, True, db_session=db_session)
        if label_idx is None:
            category = Category(id=category).to_dict()
            self.categories.insert_one(category, session=db_session)
        else:
            category = Category(id=category, assigned_labels=[label_idx]).to_dict()
            self.categories.insert_one(category, session=db_session)
        return category

    def add_category(self, category, generate_response=False, db_session=None):
        if generate_response:
            return {"result": self._add_category(category, db_session=db_session),
                    "numInserted": 1, "status": 201, 'model': 'Category'}
        else:
            return self._add_category(category, db_session=db_session)
