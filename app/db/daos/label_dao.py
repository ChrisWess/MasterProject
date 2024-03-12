from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING

from app import mdb, application
from app.db.daos.base import BaseDAO, dao_query
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
        self.create_index('name_index', ("lower", ASCENDING), unique=True)
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
        return self.simple_match("lower", name.lower(), projection, generate_response, db_session, find_many=False)

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

    @dao_query()
    def search_labels(self, query):
        """
        Find the Label with the given substring query
        :param query: substring that is used to search for labels
        :return: Label object with the given name
        """
        self.add_query("lower", '^' + query.lower(), '$regex')
        self.regex_options(True)

    def perform_label_search(self, query):
        """
        Find the Label with the given substring query
        :param query: substring that is used to search for labels
        :return: Label object with the given name
        """
        result = self.search_labels(query, projection='name', get_cursor=True)
        result = [(str(res['_id']), res['name']) for res in result]
        return {'status': 200, 'result': result, 'numResults': len(result)}

    def _push_new_categories_to_label(self, lid, categories, prev_categories, db_session):
        if type(categories) is list:
            category_tuples = tuple(categories)
            categories.clear()
            for c in category_tuples:
                if c not in prev_categories:
                    category = self._process_category(c, db_session)
                    if type(category) is tuple:
                        category, ctoks = category
                    else:
                        ctoks = None
                    if category not in self._category_set:
                        self._category_set.add(category)
                        if ctoks:
                            categories.append((category, ctoks))
                        else:
                            categories.append(category)
        elif isinstance(categories, str):
            if categories not in prev_categories:
                self._helper_list.append(self._process_category(categories, db_session))
                self._category_set.add(categories)
            categories = self._helper_list
        else:
            raise ValueError('Categories are neither one string nor a list of such: ' + categories)
        if categories:
            for category in categories:
                try:
                    self._add_category(category, lid, db_session)
                except ValueError:
                    self._add_label_ref_to_category(category, lid, db_session)
            self._helper_list.clear()
        for category in self._category_set:
            self._helper_list.append(category)
        result = self.array_push_many('categories', self._helper_list, ('_id', lid), False, True, db_session)
        self._helper_list.clear()
        self._category_set.clear()
        return result

    def find_or_add(self, label, categories=None, projection=None, generate_response=False, db_session=None):
        """
        Find the Label with the given name
        :param label: name of the entity behind the label
        :param categories: names of the categories that describe the label
        :param projection:
        :param generate_response:
        :param db_session:
        :return: Label object with the given name
        """
        init_proj = ('_id', 'categories')
        existing_label = self.find_by_name(label, projection=init_proj, db_session=db_session)
        if existing_label is None:
            if not categories:
                return None
            result = self.add(label, categories, generate_response, db_session=db_session)
            if not generate_response:
                result = result[1]
            return result
        else:
            lid = existing_label['_id']
            prev_categories = existing_label['categories']
            if projection == '_id' or projection == 'categories' or projection == init_proj:
                result = existing_label
            else:
                result = self.find_by_id(lid, projection, False, db_session)
            if categories:
                self._push_new_categories_to_label(lid, categories, prev_categories, db_session)
            return self.to_response(result) if generate_response else result

    def add_categories_to_label(self, label_id, categories, generate_response=False, db_session=None):
        """
        Find the Label with the given name
        :param label_id: ID of the label
        :param categories: names of the categories that describe the label
        :param generate_response:
        :param db_session:
        :return: Label object with the given name
        """
        existing_label = self.find_by_id(label_id, projection=('_id', 'categories'), db_session=db_session)
        if existing_label is None:
            return None
        result = self._push_new_categories_to_label(existing_label['_id'], categories,
                                                    existing_label['categories'], db_session)
        return self.to_response(result, BaseDAO.UPDATE) if generate_response else result

    def _process_category(self, category, db_session=None):
        category = self.preproc.preprocess_category(category)
        if isinstance(category, tuple):
            tokens = category[1]
            corpus = CorpusDAO()
            for token in tokens:
                corpus.find_doc_or_add(token, True, db_session=db_session)
        return category

    def _process_unique_category(self, category, db_session=None):
        category = self._process_category(category, db_session)
        if type(category) is tuple:
            category, ctoks = category
        else:
            ctoks = None
        if category not in self._category_set:
            self._category_set.add(category)
            if ctoks:
                self._helper_list.append((category, ctoks))
            else:
                self._helper_list.append(category)

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
        if not categories:
            return None
        elif type(categories) is list:
            for c in categories:
                self._process_unique_category(c, db_session)
            category_info = self._helper_list
            categories.clear()
            for category in self._category_set:
                categories.append(category)
        elif isinstance(categories, str):
            category_info = self._process_category(categories, db_session)
            if type(category_info) is tuple:
                self._helper_list.append(category_info[0])
            else:
                self._helper_list.append(category_info)
            categories = self._helper_list
            category_info = (category_info,)
        else:
            raise ValueError('Categories are neither one string nor a list of such: ' + categories)
        label_idx = LabelIndexManager().get_incremented_index(db_session)
        name = ' '.join(n.capitalize() for n in name.split(' '))
        label = Label(label_idx=label_idx, name=name, name_tokens=tokens,
                      token_idxs=txt_idxs, categories=categories)
        response = self.insert_doc(label, generate_response=generate_response, db_session=db_session)
        if category_info:
            for category in category_info:
                try:
                    self._add_category(category, label_idx, db_session)
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
        if any(not categ for categ in categories):
            return None
        start_idx = LabelIndexManager().multi_increment_index(num_new_docs, db_session)
        for i, (name, categors) in enumerate(zip(names, categories)):
            tokens, txt_idxs = self._process_label_name(name, db_session)
            assert type(categors) is list
            for c in categors:
                self._process_unique_category(c, db_session)
            categors.clear()
            for category in self._category_set:
                categors.append(category)
            label_idx = start_idx + i
            for category in self._helper_list:
                try:
                    self._add_category(category, label_idx, db_session)
                except ValueError:
                    self._add_label_ref_to_category(category, label_idx, db_session)
            self._category_set.clear()
            self._helper_list.clear()
            name = ' '.join(n.capitalize() for n in name.split(' '))
            self._or_list.append(Label(label_idx=label_idx, name=name, name_tokens=tokens,
                                       token_idxs=txt_idxs, categories=categors))
        response = self.insert_docs(self._or_list, generate_response=generate_response, db_session=db_session)
        self._or_list.clear()
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
        result = self.array_update('categories', category, ('labelIdx', label_idx), True, False, True, db_session)
        category = self._process_category(category, db_session)
        try:
            self._add_category(category, label_idx)
        except ValueError:
            self._add_label_ref_to_category(category, label_idx, db_session)
        return category

    def remove_category_from_label(self, category, label, delete_if_unreferenced=False,
                                   generate_response=False, db_session=None):
        """
        Remove the given category from the label's categories.
        :param category: the string of the category
        :param label: Either label index or the label ID
        :param delete_if_unreferenced: If True, when the category is not assigned to any labels
                                       after the removal, delete the category.
        :param generate_response:
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
        result = self.array_update('categories', category, ('labelIdx', label_idx), False, False, True, db_session)
        if delete_if_unreferenced:
            category_doc = self.find_category(category, db_session=db_session)
            if len(category_doc['labelIdxRefs']) == 1:
                self._query_matcher['_id'] = category
                self.categories.delete_one(self._query_matcher, session=db_session)
                self._query_matcher.clear()
                return self.to_response(result, operation=BaseDAO.DELETE) if generate_response else result
        self._query_matcher['_id'] = category
        self._pull_op['labelIdxRefs'] = label_idx
        self._update_commands['$pull'] = self._pull_op
        self.categories.update_one(self._query_matcher, self._update_commands, session=db_session)
        self._pull_op.clear()
        self._update_commands.clear()
        self._query_matcher.clear()
        return self.to_response(result, operation=BaseDAO.DELETE) if generate_response else result

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
        :param category: the string of the category (also allows list of strings => $in query)
        :param unroll_labels:
        :param generate_response:
        :param db_session:
        :return: The category document, if it exists else None
        """
        in_query = type(category) is list
        if unroll_labels:
            if in_query:
                self._in_query['$in'] = category
                category = self._in_query
            self._query_matcher['_id'] = category
            self._match_agg_clause['$match'] = self._query_matcher
            self._lookup_pipeline.append(self._match_agg_clause)
            result = self.find_all_categories(True, False, db_session)
            self._match_agg_clause.clear()
            self._lookup_pipeline.clear()
            if result:
                result = result[0]
                labels = result['labels']
                for i, label in enumerate(labels):
                    labels[i] = self.payload_model(**label).to_dict()
            else:
                result = None
        elif in_query:
            self._in_query['$in'] = category
            self._query_matcher['_id'] = self._in_query
            result = self.categories.find(self._query_matcher, session=db_session)
        else:
            self._query_matcher['_id'] = category
            result = self.categories.find_one(self._query_matcher, session=db_session)
        self._query_matcher.clear()
        if in_query:
            self._in_query.clear()
            if generate_response:
                return {"result": list(result), "numResults": len(result), "status": 200,
                        'model': 'Category', 'isComplete': True}
        elif generate_response and result:
            return {"result": result, "numResults": 1, "status": 200,
                    'model': 'Category', 'isComplete': True}
        return result

    def find_categories_by_label(self, label_id, generate_response=False, db_session=None):
        categories = self.find_by_id(label_id, projection='categories')
        if categories is None:
            return None
        return self.find_category(categories['categories'], False, generate_response, db_session)

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

    def category_names(self, generate_response=False, db_session=None):
        # TODO: this returned list should be presented as a dropdown menu in the frontend.
        #  After choosing a category from dropdown, only labels of that category are presented in
        #  the label-dropdown menu.
        # TODO: Usually sort in the Frontend (always a good idea to outsource as much functionality
        #  to the frontend as possible to relieve the server's utilization)
        self._projection_dict['_id'] = 1
        result = [doc['_id'] for doc in self._apply_sort_limit(self.categories.find(self._query_matcher,
                                                                                    self._projection_dict,
                                                                                    session=db_session))]
        self._projection_dict.clear()
        return {'status': 200, 'result': result, 'numResults': len(result)} if generate_response else result

    def _add_label_ref_to_category(self, category, label_idx, db_session=None):
        if type(category) is tuple:
            category = category[0]
        self._query_matcher['_id'] = category
        self._push_op['labelIdxRefs'] = label_idx
        self._update_commands['$push'] = self._push_op
        result = self.categories.update_one(self._query_matcher, self._update_commands, session=db_session)
        self._push_op.clear()
        self._update_commands.clear()
        self._query_matcher.clear()
        return result

    def _add_category(self, category, label_idx=None, db_session=None):
        if type(category) is tuple:
            category, ctoks = category
        else:
            self._nor_list.append(category)
            ctoks = self._nor_list
        self._query_matcher['_id'] = category
        try:
            self.categories.find(self._query_matcher, session=db_session).next()
            self._query_matcher.clear()
            raise ValueError(f'A category with name "{category}" does already exist!')
        except StopIteration:
            self._query_matcher.clear()
        CorpusDAO().find_doc_or_add(category, True, db_session=db_session)
        if label_idx is None:
            category_doc = Category(id=category, tokens=ctoks).to_dict()
        else:
            category_doc = Category(id=category, tokens=ctoks, assigned_labels=[label_idx]).to_dict()
        self.categories.insert_one(category_doc, session=db_session)
        if ctoks == self._nor_list:
            self._nor_list.clear()
        application.logger.info(f'New category "{category}" has been added!')
        return category_doc

    def add_category(self, category, generate_response=False, db_session=None):
        category = self._process_category(category, db_session)
        if generate_response:
            return {"result": self._add_category(category, db_session=db_session),
                    "numInserted": 1, "status": 201, 'model': 'Category'}
        else:
            return self._add_category(category, db_session=db_session)
