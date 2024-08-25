import threading
from copy import deepcopy
from enum import Enum
from functools import wraps
from importlib import import_module
from json import dumps, loads
from typing import Iterable

from bson import ObjectId
from pymongo import ASCENDING, DESCENDING
from pymongo.client_session import ClientSession
from werkzeug.datastructures.structures import ImmutableMultiDict, ImmutableDict

from app import mdb, client, config
from app.db.daos.dao_config import daos_path_prefix, dao_module_class_dict
from app.db.util import deprecated


class SafeDelete(Enum):
    # TODO: make a safe-delete function, where account is just being hidden.
    VISIBLE = 0
    HIDDEN = 1


class DAOWorker:
    def __init__(self, instance):
        self.instance = instance
        self.thread = None
        self.lock = threading.Lock()


class MetaDAO(type):
    """ metaclass for DAOs in order to achieve singletons """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        # Note: use of (simple) singletons is not thread-safe (only multiprocess-safe, because multiple
        #       processes each keep their own set "instances", that is not shared between processes).
        if cls not in cls._instances:
            cls._instances[cls] = ([DAOWorker(super(MetaDAO, cls).__call__(
                *args, **kwargs)) for _ in range(config.NUM_DAO_WORKERS)], {})
        this_thread = threading.current_thread()
        thread_id = this_thread.native_id
        workers, thread_idx_map = cls._instances[cls]
        if thread_id in thread_idx_map:
            return workers[thread_idx_map[thread_id]].instance
        else:
            while True:
                # TODO: Could add some dynamic load balancing here
                for i, worker in enumerate(workers):
                    lock = worker.lock
                    lock.acquire()
                    thread = worker.thread
                    if thread is None or not thread.is_alive():
                        worker.thread = this_thread
                        thread_idx_map[thread_id] = i
                        if thread is not None:
                            del thread_idx_map[thread.native_id]
                        lock.release()
                        return worker.instance
                    else:
                        lock.release()


class AbstractDAO(metaclass=MetaDAO):
    __slots__ = "collection", "collection_name"

    def __init__(self, collection):
        self.collection = getattr(mdb, collection)
        self.collection_name = collection


class BaseDAO(AbstractDAO):
    __slots__ = (
        "location", "_loc_prefix", "_nested_id_filter", "_nested_as_root_agg", "_is_unwound", "_loc_filter",
        "_nested_path", "_push_loc", "_pull_loc", "_parent_prefix", "model", "payload_model", "_example_model",
        "_key_set", "references", "_extended_schema", "stat_references", "_num_docs_per_export_file", "_or_list",
        "_nor_list", "_or_list", "_nor_list", "_eq_list", "_wrapping_ops_map", "_negation", "_gte_query", "_lte_query",
        "_ne_query", "_in_query", "_nin_query", "_all_query", "_exists_query", "_field_ops_map", "_regex_search",
        "_regex_search_flag", "_query_matcher", "_limit_results", "_limit_agg", "_skip_results", "_skip_agg",
        "_search_instructions", "_text_search", "_apply_search_flag", "_set_field_op", "_unset_field_op", "_push_op",
        "_push_each", "_pull_op", "_upd_ops_map", "_update_commands", "_helper_list", "_field_check",
        "_text_score_sorter", "_sort_list", "_projection_dict", "_match_agg_clause", "_group_by_agg", "_agg_group",
        "_grouping_flag", "_agg_sorter", "_agg_sort", "_agg_projection", "_agg_pipeline", "_index_definitions",
        "_nested_get", "_array_filters", "_increment_op", "_nested_upd_loc"
    )

    GET = 0
    CREATE = 1
    UPDATE = 2
    DELETE = 3

    def __init__(self, collection, model, payload_model, nested_loc=None):
        super().__init__(collection)
        # TODO: make a method that checks each DB collection for data consistency! Make this method an optional
        #  server starting configuration that should be enabled when a server crash occurred.
        self.model = model
        self.payload_model = payload_model
        self._example_model = self._key_set = self.references = self._extended_schema = None
        self.stat_references = None
        self._num_docs_per_export_file = 500
        self._or_list = []
        self._nor_list = []
        self._eq_list = []
        self._wrapping_ops_map = {
            '$or': self._or_list,
            '$nor': self._nor_list,
            '$eq': self._eq_list,
        }
        self._negation = {}
        self._gte_query = {}
        self._lte_query = {}
        self._ne_query = {}
        self._in_query = {}
        self._nin_query = {}
        self._all_query = {}
        self._exists_query = {}
        self._field_ops_map = {
            'lte': self._lte_query,
            'gte': self._gte_query,
            '$ne': self._ne_query,
            '$in': self._in_query,
            '$nin': self._nin_query,
            '$all': self._all_query,
            '$exists': self._exists_query,
        }
        self._regex_search = {"$regex": None, "$options": ""}
        self._regex_search_flag = False
        self._query_matcher = {}
        self._limit_results = None
        self._limit_agg = {'$limit': self._limit_results}
        self._skip_results = None
        self._skip_agg = {'$skip': self._limit_results}
        self._search_instructions = {"$search": None, "$language": "en", '$caseSensitive': False}
        self._text_search = {"$text": self._search_instructions}
        self._apply_search_flag = False

        self._set_field_op = {}
        self._unset_field_op = {}
        self._push_op = {}
        self._pull_op = {}
        self._increment_op = {}
        self._push_each = {}
        self._upd_ops_map = {
            '$set': self._set_field_op,
            '$unset': self._unset_field_op,
            '$push': self._push_op,
            '$pull': self._pull_op,
            '$inc': self._increment_op,
        }
        self._update_commands = {}

        self._field_check = {}
        self._helper_list = []

        self._text_score_sorter = {"$meta": "textScore"}
        self._sort_list = []
        self._projection_dict = {}

        self._match_agg_clause = {'$match': None}
        self._group_by_agg = {}
        self._agg_group = {"$group": self._group_by_agg}
        self._grouping_flag = False
        self._agg_sorter = {}
        self._agg_sort = {"$sort": self._agg_sorter}
        self._agg_projection = {'$project': self._projection_dict}
        self._agg_pipeline = []
        self._index_definitions = []

        self.location = nested_loc
        self._is_unwound = False
        if nested_loc:
            self._loc_prefix = nested_loc + '.'
            self._nested_path = nested_loc.split('.')
            self._array_filters = []
            # TODO: nested_get could keep track of all IDs at each level an then add them to each result document
            #  (however data schema/validators will not be able to recognize them)
            if len(self._nested_path) == 1:
                self._nested_path = None
                self._nested_upd_loc = self._loc_prefix + '$[].'
                self._push_loc = self._pull_loc = self.location
                self._parent_prefix = ''
                self._nested_get = self._dummy_nested_get
                nested_key = "$" + self.location
                unwnd = {"$unwind": nested_key}
                self._nested_as_root_agg = [
                    {"$group": {
                        "_id": "$_id",
                        self.location: {
                            "$push": nested_key
                        }
                    }},
                    unwnd, unwnd,
                    {"$replaceRoot": {"newRoot": nested_key}},
                ]
                path_increments = ({"$unwind": "$" + self.location},)
            else:
                self._parent_prefix = '.'.join(self._nested_path[:-1]) + '.'
                self._nested_path = tuple(self._nested_path)
                self._nested_upd_loc = '.$[].'.join(self._nested_path) + '.$[x].'
                self._push_loc = self._parent_prefix + '$.' + self._nested_path[-1]
                self._pull_loc = self._parent_prefix + '$[].' + self._nested_path[-1]
                self._nested_get = self._true_nested_get
                nested_key = "$" + self._nested_path[-1]
                unwnd = {"$unwind": nested_key}
                self._nested_as_root_agg = [
                    {"$group": {
                        "_id": "$_id",
                        self._nested_path[-1]: {
                            "$push": "$" + self.location
                        }
                    }},
                    {"$unwind": nested_key},
                    *(unwnd for _ in range(2 * (len(self._nested_path) - 1))),
                    {"$replaceRoot": {"newRoot": nested_key}},
                ]
                path_increments, curr = [], '$'
                for p in self._nested_path:
                    curr += p
                    path_increments.append({"$unwind": curr})
                    curr += '.'
            self._nested_id_filter = {"$match": {self._loc_prefix + "_id": None}}
            self._loc_filter = [
                self._nested_id_filter,
                *path_increments,
                self._nested_id_filter,
                self._agg_projection
            ]
        else:
            self._nested_path = self._nested_id_filter = self._nested_as_root_agg = self._nested_get = None
            self._loc_filter = self._push_loc = self._pull_loc = self._array_filters = None
            self._loc_prefix = self._parent_prefix = ''

    @property
    def example_schema(self):
        if self._example_model is None:
            self._example_model = self.model.model_json_schema()['example']
        return self._example_model

    @property
    def key_set(self):
        if self._key_set is None:
            self._key_set = set(self.example_schema)
        return self._key_set

    @property
    def extended_schema(self):
        if self.references is not None and self._extended_schema is None:
            self._extended_schema = {val[0] for val in self.references.values() if type(val) is tuple}
        return self._extended_schema

    def _dummy_nested_get(self, doc):
        return doc[self.location]

    def _recurse_get(self, doc, key_idx):
        # recursively increase the key_idx
        key = self._nested_path[key_idx]
        doc = doc[key]
        if key_idx >= len(self._nested_path) - 1:
            if type(doc) is list:
                self._helper_list += doc
            else:
                self._helper_list.append(doc)
        elif type(doc) is list:
            for d in doc:
                self._recurse_get(d, key_idx + 1)
        else:
            self._recurse_get(doc, key_idx + 1)

    def _true_nested_get(self, doc):
        self._helper_list.clear()
        self._recurse_get(doc, 0)
        return self._helper_list

    def create_index(self, index_name, *index_definitions, **kwargs):
        """
        Create an index in the database with the given index orders. Creating the same index
        multiple times will be ignored after the first successful call.
        :param index_name: the name of the index
        :param index_definitions: list of 2-tuples that define how the index is structured. The first value
                                  in a tuple is the field name and the second one is the index order type ID.
        """
        if index_definitions:
            if self.location:
                for idef in index_definitions:
                    self._index_definitions.append((self._loc_prefix + idef[0], idef[1]))
            else:
                for idef in index_definitions:
                    self._index_definitions.append(idef)
            self.collection.create_index(self._index_definitions, name=index_name, **kwargs)
            self._index_definitions.clear()

    def _prepare_doc_import(self, doc):
        return self.model(**loads(doc)).model_dump(by_alias=True)

    def import_into(self, data_export_file):
        num_imported = 0
        file = loads(data_export_file)
        for i, doc in enumerate(file):
            file[i] = self._prepare_doc_import(doc)
        result = self.collection.insert_many(file)  # bulk insert
        if self.stat_references:
            from app.db.stats.daos.base import BaseStatsDAO
            for sdao in self.stat_references:
                if issubclass(sdao, BaseStatsDAO):
                    sdao().invalidate_cache(None)
        num_imported += len(result.inserted_ids)
        return num_imported

    def export(self, fail_safe=False):
        fdata = []
        file_idx = 0
        for i, doc in enumerate(self.collection.find()):
            doc = self.payload_model(**doc).to_json()
            if fail_safe:
                # search and replace all |-| and ->> occurrences in the doc's json string
                # TODO: check if %%1%% and %%2%% exist in the doc, if they do, then increment the numbers until
                #  they do are unique to the doc. Save the info at the start of the doc
                doc = doc.replace("|-|", "%%1%%").replace("->>", "%%2%%")
            fdata.append(doc)
            if i % 500 == 0:
                if i == 0:
                    yield f'{self.collection_name}_{file_idx}->> {dumps(fdata)}'
                else:
                    yield f'|-|{self.collection_name}_{file_idx}->> {dumps(fdata)}'
                fdata.clear()
                file_idx += 1
        if fdata:
            if file_idx == 0:
                yield f'{self.collection_name}_{file_idx}->> {dumps(fdata)}'
            else:
                yield f'|-|{self.collection_name}_{file_idx}->> {dumps(fdata)}'

    @deprecated('this method was dropped in favor of pydantic model dumping')
    def serialize_reference(self, doc, references=True):
        """
        Serialization of a single dict-model that simply turns all ids (bson.ObjectID objects) into
        strings. ID fields must either be listed in the references-attr or be the _id field.
        """
        if references is True:
            references = self.references
        if references:
            for reference, ref_data in references.items():
                if reference in doc:
                    curr_ref = doc[reference]
                    if type(curr_ref) is list:
                        for i, ref in enumerate(curr_ref):
                            curr_ref[i] = str(ref)
                    else:
                        doc[reference] = str(curr_ref)
                if type(ref_data) is tuple:
                    joined_key, scope, _ = ref_data
                    if joined_key in doc and issubclass(scope, BaseDAO):
                        # recursive call
                        self.serialize_references(doc[joined_key], scope().references)
        if '_id' in doc:
            doc['_id'] = str(doc['_id'])

    @deprecated('this method was dropped in favor of pydantic model dumping')
    def serialize_references(self, docs, references=True):
        """ Dynamic ID Serialization of a single dict or a list of dict models. """
        if type(docs) is list:
            for doc in docs:
                self.serialize_reference(doc, references)
        else:
            self.serialize_reference(docs, references)

    def is_model_complete(self, item):
        return all(key in item for key in self.key_set)

    def validate_doc(self, item, check_complete=True, to_json_string=False, force=False):
        # force=True ensures that each item is validated exactly once here
        if not isinstance(item, (self.model, self.payload_model)) or force:
            item = self.payload_model(**item)
        item = item.to_json() if to_json_string else item.to_dict()
        if check_complete:
            return item, self.is_model_complete(item)
        else:
            return item, False

    def list_response(self, result_list, validate=True):
        is_complete = bool(result_list)
        if validate:
            for i, model in enumerate(result_list):
                result_list[i], is_complete = self.validate_doc(model, is_complete)
        else:
            is_complete = all(self.is_model_complete(model) for model in result_list)
        return {"result": result_list, "numResults": len(result_list),
                "status": 200, 'model': self.model.__name__, 'isComplete': is_complete}

    def to_response(self, result, operation=GET, validate=True):
        assert result is not None
        is_list = isinstance(result, list)
        if operation == BaseDAO.GET:
            if is_list:
                return self.list_response(result, validate)
            elif not isinstance(result, (dict, self.model, self.payload_model)):
                result = list(result)
            if validate:
                result, is_complete = self.validate_doc(result)
            else:
                is_complete = self.is_model_complete(result)
            return {"result": result, "numResults": 1, "status": 200,
                    'model': self.model.__name__, 'isComplete': is_complete}
        elif operation == BaseDAO.CREATE:
            if is_list:
                num_inserted = len(result)
                if validate:
                    for i, model in enumerate(result):
                        if not isinstance(result, self.model):
                            self.model(**model)
                for i in range(num_inserted):
                    result[i] = result[i]['_id']
            else:
                num_inserted = 1
                if validate and not isinstance(result, self.model):
                    self.model(**result)
                result = result['_id']
            return {"result": result, "numInserted": num_inserted, "status": 201, 'model': self.model.__name__}
        elif operation == BaseDAO.UPDATE:
            response = {"status": 200, 'model': self.model.__name__}
            if is_list:
                response["numUpdated"] = len(result)
                response["result"] = {'locations': result}
            else:
                if isinstance(result, str):
                    response["numUpdated"] = 1
                    response["result"] = {'locations': [result]}
                elif isinstance(result, (dict, self.payload_model)):
                    response["numUpdated"] = 1
                    response["result"] = result
                else:
                    response["numUpdated"] = result.modified_count
            return response
        elif operation == BaseDAO.DELETE:
            num_deleted = "unknown" if self.location else result.deleted_count
            return {"numDeleted": num_deleted, "status": 200, 'model': self.model.__name__}
        else:
            raise ValueError(f"Operation {operation} does not exist!")

    def _wrap_by_negation(self, doc_key, query_to_wrap):
        if self._negation:
            self._query_matcher[doc_key] = {'not': query_to_wrap}
        else:
            self._negation['not'] = query_to_wrap
            self._query_matcher[doc_key] = self._negation

    def _set_field(self, qdict, doc_key, query, op_key, negate):
        if qdict:
            query = {op_key: query}
        else:
            qdict[op_key] = query
            query = qdict
        if negate:
            self._wrap_by_negation(doc_key, query)
        else:
            self._query_matcher[doc_key] = query

    def add_query(self, doc_key, query, op_key=None, negate=False):
        """
        op_key=None equals search by value matching (i.e. the value in variable "query").
        Make sure to not use a dict as "query" that contains an operation at the front, but
        make sure to put that operation ID into op_key.
        """
        if self.location:
            doc_key = self._loc_prefix + doc_key
        if op_key is None:
            if negate:
                self._wrap_by_negation(doc_key, query)
            else:
                self._query_matcher[doc_key] = query
        elif op_key in self._wrapping_ops_map:
            qlist = self._wrapping_ops_map[op_key]
            if isinstance(query, Iterable):
                if isinstance(query, dict):
                    qlist.append(query)
                else:
                    qlist += query
            else:
                qlist.append({doc_key: query})
            if op_key not in self._query_matcher:
                self._query_matcher[op_key] = qlist
        elif op_key in self._field_ops_map:
            if not negate and doc_key in self._query_matcher:
                self._query_matcher[doc_key][op_key] = query
            else:
                qdict = self._field_ops_map[op_key]
                self._set_field(qdict, doc_key, query, op_key, negate)
        elif op_key == '$regex':
            if not negate and doc_key in self._query_matcher:
                self._query_matcher[doc_key][op_key] = query
            else:
                self._set_field(self._regex_search, doc_key, query, op_key, negate)
            self._regex_search_flag = True
        else:
            self._query_matcher[doc_key] = {op_key: query}
        return self._query_matcher

    def add_agg_match(self, doc_key, query, op_key=None):
        # TODO: this might contain errors (was adapted from add_query())
        matcher = {}
        if op_key is None:
            matcher[doc_key] = query
        elif op_key in self._wrapping_ops_map:
            qlist = self._wrapping_ops_map[op_key]
            if isinstance(query, Iterable):
                if isinstance(query, dict):
                    qlist.append(query)
                else:
                    qlist += query
            else:
                qlist.append({doc_key: query})
            if op_key not in matcher:
                matcher[op_key] = qlist
        elif op_key in self._field_ops_map:
            if doc_key in matcher:
                matcher[doc_key][op_key] = query
            else:
                qdict = self._field_ops_map[op_key]
                if qdict:
                    query = {op_key: query}
                else:
                    qdict[op_key] = query
                    query = qdict
                matcher[doc_key] = query
        elif op_key == '$regex':
            if doc_key in matcher:
                matcher[doc_key][op_key] = query
            else:
                if self._regex_search:
                    query = {op_key: query}
                else:
                    self._regex_search[op_key] = query
                    query = self._regex_search
                matcher[doc_key] = query
            self._regex_search_flag = True
        else:
            matcher[doc_key] = {op_key: query}
        self._agg_pipeline.append({'$match': matcher})

    def regex_options(self, case_insensitive=False, multiline_anchors=False, ignore_white_spaces=False,
                      dot_wildcard=False, at_field=None):
        # https://www.mongodb.com/docs/manual/reference/operator/query/regex/
        if self._regex_search:
            if at_field is None:
                regex_query = self._regex_search
            elif '$regex' in self._query_matcher[at_field]:
                regex_query = self._query_matcher[at_field]
            elif '$not' in self._query_matcher[at_field] and '$regex' in self._query_matcher[at_field]['$not']:
                regex_query = self._query_matcher[at_field]['$not']
            else:
                raise ValueError(f'The query field "{at_field}" does not seem to contain a $regex search!')
            options = ""
            if case_insensitive:
                options += "i"
            if multiline_anchors:
                options += "m"
            if ignore_white_spaces:
                options += "x"
            if dot_wildcard:
                options += "s"
            regex_query['$options'] = options
        else:
            raise ValueError("Regex search instruction is not defined yet! Call add_query with $regex operation first!")

    def add_text_search(self, search_text, case_sensitive=False):
        """ Adds text search over all full (root) documents in the collection """
        self._search_instructions['$search'] = search_text
        if case_sensitive is True:
            self._search_instructions['$caseSensitive'] = True
            # $diacriticSensitive=False by default and should never be relevant for English texts
        self._apply_search_flag = True

    def clear_query_augmentation(self):
        self._skip_results = None
        self._limit_results = None
        self._sort_list.clear()

    def clear_query(self):
        for templ in self._wrapping_ops_map.values():
            templ.clear()
        for templ in self._field_ops_map.values():
            templ.clear()
        if self._regex_search_flag:
            self._regex_search['$regex'] = None
            self._regex_search['$options'] = ''
            self._regex_search_flag = False
        if self._apply_search_flag:
            self._search_instructions['$search'] = None
            self._search_instructions['$caseSensitive'] = False
            self._apply_search_flag = False
        self._negation.clear()
        self._query_matcher.clear()
        self.clear_query_augmentation()

    def limit(self, num_docs):
        self._limit_results = num_docs

    def skip(self, num_docs):
        self._skip_results = num_docs

    def sort_by(self, field, desc=True):
        # https://stackoverflow.com/questions/32645617/why-aggregatesort-is-faster-than-findsort-in-mongo
        self._sort_list.append((field, DESCENDING if desc else ASCENDING))

    def add_text_score_sort(self):
        self._sort_list.append(('score', self._text_score_sorter))

    def _apply_sort_limit(self, docs, detach_sort=False):
        if self._sort_list:
            if len(self._sort_list) == 1:
                docs = docs.sort(*self._sort_list[0])
            else:
                sorting = deepcopy(self._sort_list) if detach_sort else self._sort_list
                docs = docs.sort(sorting)
        if self._skip_results:
            docs = docs.skip(self._skip_results)
        if self._limit_results:
            docs = docs.limit(self._limit_results)
        return docs

    def group_by(self, acc_field_name, accumulator=None, group_at_id=None):
        # TODO: add special ID values
        # TODO: add accumulator dicts for most common group-operations
        # https://www.mongodb.com/docs/manual/reference/operator/aggregation/group/#mongodb-pipeline-pipe.-group
        if not self._group_by_agg['_id']:
            self._group_by_agg['_id'] = group_at_id
        self._group_by_agg[acc_field_name] = accumulator

    def add_update(self, doc_key, val, op_key="$set"):
        if self.location:
            doc_key = self._nested_upd_loc + doc_key
        if op_key in self._update_commands:
            upd_map = self._update_commands[op_key]
            upd_map[doc_key] = val
        elif op_key in self._upd_ops_map:
            upd_map = self._upd_ops_map[op_key]
            if op_key == "$unset":
                val = bool(val)  # should only be true or false
            elif op_key == "$push" and type(val) is list:
                if self._push_each:
                    val = {'$each': val}
                else:
                    self._push_each['$each'] = val
                    val = self._push_each
            upd_map[doc_key] = val
            if op_key not in self._update_commands:
                self._update_commands[op_key] = upd_map
        else:
            self._update_commands[op_key] = {doc_key: val}
        return self._update_commands

    def clear_update(self):
        for upd in self._upd_ops_map.values():
            upd.clear()
        self._push_each.clear()
        self._update_commands.clear()

    def unwind_nested_docs(self):
        if self._nested_as_root_agg is None:
            return None
        self._agg_pipeline.extend(self._nested_as_root_agg)
        self._is_unwound = True

    def add_aggregation(self, aggregation_op):
        self._agg_pipeline.append(aggregation_op)

    def build_projection(self, projection):
        """ Better to not use this for aggregations, create a custom projection or use @dao_query decorator instead """
        if not projection:
            if not self._is_unwound and self.location:
                self._projection_dict[self.location] = 1
            return self._projection_dict
        elif projection == self._projection_dict:
            return self._projection_dict
        if isinstance(projection, str):
            prefix = '' if self._is_unwound else self._loc_prefix
            self._projection_dict[prefix + projection] = 1
        elif isinstance(projection, (list, tuple, set)):
            prefix = '' if self._is_unwound else self._loc_prefix
            for key in projection:
                self._projection_dict[prefix + key] = 1
        else:  # here: projection should be a sort of dict (key-value mapping) => needs items-method (iterator).
            is_inclusion = False  # can not mix inclusion with exclusion (either only 0 or only 1)
            schema = self.example_schema if isinstance(projection, (ImmutableDict, ImmutableMultiDict)) else None
            prefix = '' if self._is_unwound else self._loc_prefix
            for key, val in projection.items():
                if schema:
                    if key not in schema:
                        continue
                try:
                    val = int(val)
                    # prioritize inclusion: if any value is 1,
                    # then clear all exclusions=0 & keep only inclusions=1
                    if val == 1:
                        if not is_inclusion:
                            is_inclusion = True
                            self._projection_dict.clear()
                        self._projection_dict[prefix + key] = val
                    elif val == 0:
                        if is_inclusion:
                            continue
                        else:
                            self._projection_dict[prefix + key] = val
                except ValueError:
                    pass
        if not self._projection_dict and not self._is_unwound and self.location:
            self._projection_dict[self.location] = 1
        return self._projection_dict

    def _insert_into_list(self, obj, *locs_id, db_session=None):
        insert_info = obj.model_dump(exclude_none=True, by_alias=True)
        try:
            self._query_matcher[self._parent_prefix + '_id'] = locs_id[-1]
            self._push_op[self._push_loc] = insert_info
            self._update_commands['$push'] = self._push_op
            result = self.collection.update_one(self._query_matcher, self._update_commands, upsert=True,
                                                session=db_session)
        finally:
            self._push_op.clear()
            self._update_commands.clear()
            self._query_matcher.clear()
        new_id = insert_info['_id']
        if self.stat_references:
            for ids, refs in zip((*locs_id, new_id), self.stat_references):
                if refs is not None:
                    for sdao in refs:
                        sdao().invalidate_cache(ids, db_session)
        return insert_info, new_id

    def insert_doc(self, obj, locs_id=None, update_stats=True, generate_response=True, db_session=None):
        if self.location:
            insert_info, new_id = self._insert_into_list(obj, *locs_id)
        else:
            if locs_id:
                obj.id = locs_id
            insert_info = obj.model_dump(exclude_none=True, by_alias=True)
            result = self.collection.insert_one(insert_info, session=db_session)  # save object
            new_id = result.inserted_id
            if self.stat_references and update_stats:
                from app.db.stats.daos.base import BaseStatsDAO
                for sdao in self.stat_references:
                    if issubclass(sdao, BaseStatsDAO):
                        sdao().invalidate_cache(None, db_session)
        if generate_response:
            insert_info = self.model.postprocess_insert_response(insert_info, new_id)
            return self.to_response(insert_info, BaseDAO.CREATE, validate=False)
        else:
            obj.id = new_id
            insert_info['_id'] = new_id
            return obj, insert_info

    def _insert_many_into_list(self, objs, *locs_id, db_session=None):
        try:
            if objs == self._helper_list:
                for i, obj in enumerate(objs):
                    self._helper_list[i] = obj.model_dump(exclude_none=True, by_alias=True)
            else:
                for obj in objs:
                    self._helper_list.append(obj.model_dump(exclude_none=True, by_alias=True))
            self._query_matcher[self._parent_prefix + '_id'] = locs_id[-1]
            self._push_each['$each'] = self._helper_list
            self._push_op[self._push_loc] = self._push_each
            self._update_commands['$push'] = self._push_op
            result = self.collection.update_one(self._query_matcher, self._update_commands,
                                                upsert=True, session=db_session)
        finally:
            self._push_op.clear()
            self._push_each.clear()
            self._update_commands.clear()
            self._query_matcher.clear()
        new_ids = [doc['_id'] for doc in self._helper_list]
        if self.stat_references:
            for ids, refs in zip((*locs_id, new_ids), self.stat_references):
                if refs is not None:
                    for sdao in refs:
                        sdao().invalidate_cache(ids, db_session)
        return self._helper_list, new_ids

    def insert_docs(self, objs, locs_id=None, update_stats=True, generate_response=True, db_session=None):
        in_helper_list = objs == self._helper_list
        try:
            if self.location:
                objs, new_ids = self._insert_many_into_list(objs, *locs_id)
            else:
                if in_helper_list:
                    for i, obj in enumerate(objs):
                        self._helper_list[i] = obj.model_dump(exclude_none=True, by_alias=True)
                else:
                    for obj in objs:
                        self._helper_list.append(obj.model_dump(exclude_none=True, by_alias=True))
                result = self.collection.insert_many(self._helper_list, ordered=False,
                                                     session=db_session)  # save objects
                new_ids = result.inserted_ids
                if self.stat_references and update_stats:
                    from app.db.stats.daos.base import BaseStatsDAO
                    for sdao in self.stat_references:
                        if issubclass(sdao, BaseStatsDAO):
                            sdao().invalidate_cache(None, db_session)
            if generate_response:
                # TODO: there might be the case when not all objects could be inserted
                insert_info = [self.model.postprocess_insert_response(insi, id_) for insi, id_ in zip(
                    self._helper_list, new_ids)]
                self._helper_list.clear()
                return self.to_response(insert_info, BaseDAO.CREATE, validate=False)
            elif in_helper_list:
                for obj, id_ in zip(objs, new_ids):
                    obj['_id'] = id_
            else:
                for i, id_ in enumerate(new_ids):
                    obj = self._helper_list[i]
                    obj['_id'] = id_
                    objs[i] = obj
                self._helper_list.clear()
        except Exception as e:
            self._helper_list.clear()
            raise e
        return objs

    def insert(self, obj, *objs, locs_id=None, update_stats=True, generate_response=True, db_session=None):
        if len(objs) == 0:
            return self.insert_doc(obj, locs_id, update_stats, generate_response, db_session)
        else:
            return self.insert_docs([obj, *objs], locs_id, update_stats, generate_response, db_session)

    def _do_aggregate(self):
        return self._grouping_flag or self._agg_pipeline

    def does_value_exist(self, field_name, value, db_session=None):
        try:
            self._query_matcher[field_name] = value
            result = self.collection.count_documents(self._query_matcher, limit=1, session=db_session)
        finally:
            self._query_matcher.clear()
        return bool(result)

    def _execute_aggregation(self, query, projection, get_cursor, db_session):
        try:
            if query:
                self._match_agg_clause['$match'] = query
                self._agg_pipeline.insert(0, self._match_agg_clause)
            if self._apply_search_flag:
                # TODO: text search in aggregations possible?
                self._agg_pipeline.append(self._text_search)
            if self._group_by_agg:
                self._agg_pipeline.append(self._agg_group)
            projection = self.build_projection(projection)
            if projection:
                self._agg_pipeline.append(self._agg_projection)
            if self._sort_list:
                self._agg_sorter.clear()
                self._agg_sorter.update(self._sort_list)
                self._agg_pipeline.append(self._agg_sort)
            if self._skip_results:
                self._agg_pipeline.append(self._skip_agg)
            if self._limit_results:
                self._agg_pipeline.append(self._limit_agg)
            # print("Executing aggregation:", cls._agg_pipeline)
            if get_cursor:
                result = self.collection.aggregate(deepcopy(self._agg_pipeline), session=db_session)
            else:
                result = self.collection.aggregate(self._agg_pipeline, session=db_session)
                if not self._is_unwound and self.location:
                    res = []
                    for doc in result:
                        res += self._nested_get(doc)
                    result = res
                    self._helper_list.clear()
                else:
                    result = list(result)
        finally:
            self._agg_pipeline.clear()
        return result, projection

    def find(self, find_many=True, projection=None, custom_query=None, get_cursor=False, db_session=None):
        """
        Execute the currently configured query, if custom_query=None.
        Otherwise, this simply executes the query from custom_query.
        """
        query = self._query_matcher if custom_query is None else custom_query
        try:
            if self._do_aggregate():
                # joins should already be in the aggregation pipeline
                result, projection = self._execute_aggregation(query, projection, get_cursor, db_session)
            else:
                # print("Executing query:", query)
                projection = self.build_projection(projection)
                if find_many:
                    if self._apply_search_flag:
                        query['$text'] = self._search_instructions
                    if get_cursor:
                        query = deepcopy(query)
                        projection_copy = deepcopy(projection) if projection else projection
                        result = self.collection.find(query, projection_copy, session=db_session)
                        result = self._apply_sort_limit(result, True)
                    else:
                        result = self.collection.find(query, projection, session=db_session)
                        if not self._is_unwound and self.location:
                            res = []
                            for doc in self._apply_sort_limit(result):
                                res += self._nested_get(doc)
                            result = res
                            self._helper_list.clear()
                        else:
                            result = list(self._apply_sort_limit(result))
                else:
                    sorting = self._sort_list if self._sort_list else None
                    result = self.collection.find_one(query, projection, sort=sorting, session=db_session)
                    if not self._is_unwound and self.location:
                        result = self._nested_get(result).copy()
                        self._helper_list.clear()
        except Exception as e:
            self._helper_list.clear()
            raise e
        finally:
            if projection:
                projection.clear()
            self._is_unwound = False
            self.clear_query()
        return result

    def find_all(self, projection=None, generate_response=False, get_cursor=False, db_session=None):
        """
        Find all DB entities in the collection
        :param projection:
        :param generate_response:
        :param get_cursor:
        :param db_session:
        :return: List of all DB entity model objects
        """
        try:
            projection = self.build_projection(projection)
            if get_cursor:
                projection_copy = deepcopy(projection) if projection else projection
                result = self.collection.find(self._query_matcher, projection_copy, session=db_session)
                result = self._apply_sort_limit(result, True)
            elif self.location:
                result = self.collection.find(self._query_matcher, projection, session=db_session)
                res = []
                for doc in self._apply_sort_limit(result):
                    res += self._nested_get(doc)
                result = res
                self._helper_list.clear()
            else:
                result = self.collection.find(session=db_session)
                result = list(self._apply_sort_limit(result))
        except Exception as e:
            self._helper_list.clear()
            raise e
        finally:
            self.clear_query_augmentation()  # TODO: check if I need this in other queries
            if projection:
                projection.clear()
        return self.to_response(result) if generate_response else result

    def find_many(self, ids, projection=None, generate_response=False, get_cursor=False, db_session=None):
        """
        Find all DB entities that match an id in array "ids".
        :param projection:
        :param generate_response:
        :param get_cursor:
        :param db_session:
        :param ids: Ids of DB entities to find
        :return: List of DB entity model objects that match the provided IDs
        """
        try:
            if type(ids) is not list:
                if self._nested_path:
                    ids = list(ids)
                else:
                    for i in ids:
                        self._helper_list.append(i)
                    ids = self._helper_list
            self._in_query['$in'] = ids
            self._query_matcher["_id"] = self._in_query
            if get_cursor:
                projection = self.build_projection(projection)
                projection_copy = deepcopy(projection) if projection else projection
                result = self.collection.find(deepcopy(self._query_matcher), projection_copy, session=db_session)
                result = self._apply_sort_limit(result, True)
            elif self.location:
                projection = self.build_projection(projection)
                result = self.collection.find(self._query_matcher, projection, session=db_session)
                res = []
                for doc in self._apply_sort_limit(result):
                    res += self._nested_get(doc)
                result = res
                if ids == self._helper_list:
                    self._helper_list.clear()
            else:
                if projection:
                    projection = self.build_projection(projection)
                    result = self.collection.find(self._query_matcher, projection, session=db_session)
                else:
                    result = self.collection.find(self._query_matcher, session=db_session)
                result = list(self._apply_sort_limit(result))
                if ids == self._helper_list:
                    self._helper_list.clear()
        except Exception as e:
            self._helper_list.clear()
            raise e
        finally:
            self._in_query.clear()
            self._query_matcher.clear()
            if projection:
                projection.clear()
        return self.to_response(result) if generate_response else result

    def find_many_retain_order(self, ids, custom_sort=None, projection=None, generate_response=False,
                               get_cursor=False, db_session=None):
        """
        Find all DB entities that match an id in array "ids".
        :param ids: Ids of DB entities to find
        :param custom_sort: (optional) sorting criteria that is known to guarantee to retain the order
        :param projection:
        :param generate_response:
        :param get_cursor:
        :param db_session:
        :return: List of DB entity model objects that match the provided IDs
        """
        if custom_sort:
            try:
                if type(custom_sort[0]) is tuple:
                    for field, order in custom_sort:
                        self.sort_by(field, order)
                elif type(custom_sort) is str:
                    self.sort_by(custom_sort)
                else:
                    self.sort_by(*custom_sort)
                result = self.find_many(ids, projection, False, get_cursor, db_session)
            finally:
                self._sort_list.clear()
        else:
            # Retain the original order without any additional sorting input from the user
            # TODO: adjust this for usage on nested docs
            has_projection = bool(projection)
            try:
                if type(ids) is not list:
                    for i in ids:
                        self._helper_list.append(i)
                    ids = self._helper_list
                self._agg_sorter['__order'] = 1
                self._in_query['$in'] = ids
                self._query_matcher["_id"] = self._in_query
                self._match_agg_clause['$match'] = self._query_matcher
                self._agg_pipeline.append(self._match_agg_clause)
                self._agg_pipeline.append({'$addFields': {"__order": {'$indexOfArray': [ids, "$_id"]}}})
                self._agg_pipeline.append(self._agg_sort)
                if has_projection:
                    self.build_projection(projection)
                    self._agg_pipeline.append(self._agg_projection)
                if get_cursor:
                    result = self.collection.aggregate(deepcopy(self._agg_pipeline), session=db_session)
                else:
                    result = list(self.collection.aggregate(self._agg_pipeline, session=db_session))
                if ids == self._helper_list:
                    self._helper_list.clear()
            except Exception as e:
                self._helper_list.clear()
                raise e
            finally:
                if has_projection:
                    self._projection_dict.clear()
                self._agg_pipeline.clear()
                self._match_agg_clause['$match'] = None
                self._query_matcher.clear()
                self._in_query.clear()
                self._agg_sorter.clear()
        return self.to_response(result) if generate_response else result

    def find_by_id(self, entity_id, projection=None, generate_response=False, db_session=None):
        """
        Find DB entity with given id
        :param projection:
        :param generate_response:
        :param db_session:
        :param entity_id: Id of DB entity to find
        :return: DB entity model object if found, None otherwise
        """
        try:
            self._query_matcher["_id"] = entity_id
            if projection or self.location:
                projection = self.build_projection(projection)
                result = self.collection.find_one(self._query_matcher, projection, session=db_session)
            else:
                result = self.collection.find_one(self._query_matcher, session=db_session)
            if result and self.location:
                result = self._nested_get(result).copy()
                self._helper_list.clear()
        except Exception as e:
            self._helper_list.clear()
            raise e
        finally:
            self._query_matcher.clear()
            if projection:
                projection.clear()
        return self.to_response(result) if generate_response and result is not None else result

    def simple_match(self, key, value, projection_includes=None, generate_response=False,
                     db_session=None, find_many=True, get_cursor=False):
        key = self._loc_prefix + key
        self._query_matcher[key] = value
        has_projection = bool(projection_includes)
        try:
            if has_projection:
                if isinstance(projection_includes, str):
                    self._projection_dict[self._loc_prefix + projection_includes] = 1
                else:
                    for proj in projection_includes:
                        self._projection_dict[self._loc_prefix + proj] = 1
            if find_many:
                if get_cursor:
                    projection_copy = deepcopy(self._projection_dict) if has_projection else None
                    result = self.collection.find(deepcopy(self._query_matcher), projection_copy, session=db_session)
                    result = self._apply_sort_limit(result, True)
                elif self.location:
                    result = self.collection.find(self._query_matcher, self._projection_dict, session=db_session)
                    if find_many:
                        res = []
                        for doc in self._apply_sort_limit(result):
                            res += self._nested_get(doc)
                        result = res
                        self._helper_list.clear()
                    else:
                        result = self._nested_get(result)[0]
                        self._helper_list.clear()
                else:
                    result = self.collection.find(self._query_matcher, self._projection_dict, session=db_session)
                    result = list(self._apply_sort_limit(result))
                return self.to_response(result) if generate_response else result
            else:
                sorting = self._sort_list if self._sort_list else None
                result = self.collection.find_one(self._query_matcher, self._projection_dict,
                                                  sort=sorting, session=db_session)
                return self.to_response(result) if generate_response and result is not None else result
        except Exception as e:
            self._helper_list.clear()
            raise e
        finally:
            if has_projection:
                self._projection_dict.clear()
            self._query_matcher.clear()

    def list_nested_ids(self, entity_id, generate_response=False, db_session=None):
        """
        List all nested IDs of the corresponding nesting level of the entity with given id
        :param generate_response:
        :param db_session:
        :param entity_id: Id of DB entity to find
        :return: list of nested IDs if found, None otherwise
        """
        if self.location:
            id_key = '_id'
            projection = self.build_projection(id_key)
            try:
                self._query_matcher[id_key] = entity_id
                result = self.collection.find(self._query_matcher, projection, session=db_session)
                if generate_response:
                    result = self.to_response([str(obj[id_key]) for obj in self._nested_get(next(result))],
                                              validate=False)
                    result['model'] += ' IDs'
                    return result
                else:
                    return [obj[id_key] for obj in self._nested_get(next(result))]
            finally:
                self._query_matcher.clear()
                self._helper_list.clear()
                projection.clear()
        else:
            raise NotImplementedError('This is only possible for DAOs referring to nested documents!')

    def find_many_nested(self, ids, projection=None, generate_response=False, db_session=None):
        """
        Find all nested DB documents that match an id in array "ids".
        :param projection:
        :param generate_response:
        :param db_session:
        :param ids: Ids of DB entities to find
        :return: List of DB entity model objects that match the provided IDs
        """
        if self.location:
            try:
                if type(ids) is not list:
                    ids = list(ids)
                self._in_query['$in'] = ids
                self._query_matcher[self._loc_prefix + "_id"] = self._in_query
                projection = self.build_projection(projection)
                # TODO: get only the nested documents with those IDs:
                #  https://stackoverflow.com/questions/29026662/mongodb-elemmatch-multiple-elements-in-array
                result = self.collection.find(self._query_matcher, projection, session=db_session)
                result = [obj for doc in self._apply_sort_limit(result) for obj in self._nested_get(doc)]
            finally:
                self._in_query.clear()
                self._query_matcher.clear()
                self._helper_list.clear()
            if projection:
                projection.clear()
            return self.to_response(result) if generate_response else result
        else:
            raise NotImplementedError('This is only possible for DAOs referring to nested documents!')

    def find_by_nested_id(self, entity_id, get_root=False, projection=None, generate_response=False, db_session=None):
        """
        Find nested DB document with given nested id
        :param entity_id: Id of DB entity to find
        :param get_root: Get the full root document that contains the entity with the given ID, if this is True,
                         otherwise, get the nested document only.
        :param projection:
        :param generate_response:
        :param db_session:
        :return: DB entity model object if found, None otherwise
        """
        if self.location:
            try:
                projection = self.build_projection(projection)
                self._nested_id_filter["$match"][self._loc_prefix + "_id"] = entity_id
                result = self.collection.aggregate(self._loc_filter, session=db_session)
                try:
                    result = result.next()
                except StopIteration:
                    return None
                if not get_root:
                    result = self._nested_get(result)
                    if type(result) is list:
                        result = result[0]
                    self._helper_list.clear()
            except Exception as e:
                self._helper_list.clear()
                raise e
            finally:
                if projection:
                    projection.clear()
            return self.to_response(result) if generate_response and result is not None else result
        else:
            raise NotImplementedError('This is only possible for DAOs referring to nested documents!')

    def total_doc_count(self, generate_response=False, db_session=None):
        """ Count all documents in the collection or all documents in the nesting level for nested documents. """
        if self.location:
            try:
                self._agg_pipeline.extend(self._nested_as_root_agg)
                self._field_check['$count'] = 'count'
                self._agg_pipeline.append(self._field_check)
                result = next(self.collection.aggregate(self._agg_pipeline, session=db_session))
                return {"result": result['count'], "numResults": 1, "status": 200,
                        'model': 'count', 'isComplete': True} if generate_response else result
            finally:
                self._field_check.clear()
                self._agg_pipeline.clear()
        else:
            result = self.collection.count_documents(self._query_matcher, session=db_session)
            return {"result": result, "numResults": 1, "status": 200,
                    'model': 'count', 'isComplete': True} if generate_response else result

    def _recurse_get_ids(self, doc, idx, until_idx):
        if idx <= until_idx:
            doc = doc[self._nested_path[idx]]
            for child in doc:
                id_list = self._helper_list[idx + 1]
                if id_list is not None:
                    id_list.append(child['_id'])
                self._recurse_get_ids(child, idx + 1, until_idx)

    def _collect_ids(self, query, db_session):
        if self.location:
            idx = -1
            if self.stat_references[0] is None:
                self._helper_list.append(None)
            else:
                self._projection_dict['_id'] = 1
                self._helper_list.append([])
            if self._nested_path:
                for i, path in enumerate(self._nested_path):
                    path = self._nested_path[i] + '.'
                    if self.stat_references[i + 1] is None:
                        self._helper_list.append(None)
                    else:
                        self._projection_dict[path + '_id'] = 1
                        self._helper_list.append([])
                        idx = i
            else:
                if self.stat_references[1] is None:
                    self._helper_list.append(None)
                else:
                    self._projection_dict[self._loc_prefix + '_id'] = 1
                    self._helper_list.append([])
                    idx = 0
            docs = self.collection.find(query, self._projection_dict, session=db_session)
            for doc in docs:
                if self._helper_list[0] is not None:
                    self._helper_list[0].append(doc['_id'])
                self._recurse_get_ids(doc, 0, idx)
        else:
            self._projection_dict['_id'] = 1
            docs = self.collection.find(query, self._projection_dict, session=db_session)
            for doc in docs:
                self._helper_list.append(doc['_id'])

    def _invalidate_stats(self, query, db_session=None):
        try:
            self._collect_ids(query, db_session)
            if self.location:
                for id_list, sdaos in zip(self._helper_list, self.stat_references):
                    if sdaos is not None:
                        for sdao in sdaos:
                            sdao().invalidate_cache(id_list, db_session)
            else:
                for sdao in self.stat_references:
                    sdao().invalidate_cache(self._helper_list, db_session)
        finally:
            self._projection_dict.clear()
            self._helper_list.clear()

    def update(self, update_many=True, custom_query=None, custom_update=None,
               notify_stats=True, generate_response=False, db_session=None):
        """
        Execute the currently configured query, if custom_query=None.
        Otherwise, this simply executes the query from custom_query.
        """
        query = self._query_matcher if custom_query is None else custom_query
        upd_cmd = self._update_commands if custom_update is None else custom_update
        try:
            if update_many:
                result = self.collection.update_many(query, upd_cmd, session=db_session)
                if result.matched_count == 0:
                    return None
            else:
                result = self.collection.update_one(query, upd_cmd, session=db_session)
                if result.matched_count == 0:
                    return None
                result = {'at': {}, 'updatedTo': {}}
                if generate_response:
                    for qfield, qval in query.items():
                        result['at'][qfield] = str(qval)
                    for updop, updvals in upd_cmd.items():
                        upd_res_field = result['updatedTo'][updop[1:]] = {}
                        for updfield, val in updvals.items():
                            if self.location:
                                try:
                                    dot_idx = updfield.rindex('.')
                                    updfield = updfield[dot_idx + 1:]
                                except ValueError:
                                    pass
                            if isinstance(val, ObjectId):
                                val = str(val)
                            upd_res_field[updfield] = val
                else:
                    result['at'] = deepcopy(query)
                    result['updatedTo'] = deepcopy(upd_cmd)
            if notify_stats and self.stat_references:
                self._invalidate_stats(query, db_session)
        finally:
            self.clear_query()
            self.clear_update()
        return result

    def array_update(self, array_key, val, where=None, push=True, update_many=True, notify_stats=True, db_session=None):
        # if where=None, then push the value val into every array
        try:
            if where is not None:
                self._query_matcher[where[0]] = where[1]
            self._push_op[array_key] = val
            op_key = '$push' if push else '$pull'
            self._update_commands[op_key] = self._push_op
            if update_many:
                result = self.collection.update_many(self._query_matcher, self._update_commands, session=db_session)
            else:
                result = self.collection.update_one(self._query_matcher, self._update_commands, session=db_session)
            if notify_stats and self.stat_references:
                self._invalidate_stats(self._query_matcher, db_session)
        finally:
            self._push_op.clear()
            self._update_commands.clear()
            self._query_matcher.clear()
        return result

    def array_push_many(self, array_key, vals, where=None, update_many=True, notify_stats=True, db_session=None):
        try:
            self._push_each['$each'] = vals
            result = self.array_update(array_key, self._push_each, where, True,
                                       update_many, notify_stats, db_session)
        finally:
            self._push_each.clear()
        return result

    def _remove_stat_ids_from_helper(self, db_session):
        from app.db.stats.daos.base import BaseStatsDAO
        if self.location:
            for i, (id_list, sdaos) in enumerate(zip(self._helper_list, self.stat_references)):
                if sdaos is not None:
                    for sdao in sdaos:
                        if issubclass(sdao, BaseStatsDAO):
                            sdao().invalidate_cache(db_session=db_session)
                        elif i == len(self.stat_references):
                            sdao().remove_stats(id_list, db_session)
                        else:
                            sdao().invalidate_cache(id_list, db_session)
        else:
            for sdao in self.stat_references:
                if issubclass(sdao, BaseStatsDAO):
                    sdao().invalidate_cache(db_session=db_session)
                else:
                    sdao().remove_stats(self._helper_list, db_session)

    def _remove_stats(self, query, db_session=None):
        if self.stat_references:
            if query:
                try:
                    self._collect_ids(query, db_session)
                    self._remove_stat_ids_from_helper(db_session)
                finally:
                    self._projection_dict.clear()
                    self._helper_list.clear()
            else:
                from app.db.stats.daos.base import BaseStatsDAO
                if self.location:
                    for i, sdaos in enumerate(self.stat_references, start=1):
                        if sdaos is not None:
                            for sdao in sdaos:
                                if issubclass(sdao, BaseStatsDAO):
                                    sdao().invalidate_cache(db_session=db_session)
                                elif i == len(self.stat_references):
                                    sdao().remove_stats(None, db_session)
                                else:
                                    sdao().invalidate_cache(None, db_session)
                else:
                    for sdao in self.stat_references:
                        if issubclass(sdao, BaseStatsDAO):
                            sdao().invalidate_cache(db_session=db_session)
                        else:
                            sdao().remove_stats(None, db_session)

    def delete(self, delete_many=False, custom_query=None, db_session=None):
        """
        Execute the currently configured query, if custom_query=None.
        Otherwise this simply executes the query from custom_query.
        """
        query = self._query_matcher if custom_query is None else custom_query
        try:
            self._remove_stats(query, db_session)
            if self.location:
                self._set_field_op[self.location] = self._helper_list
                self._update_commands['$set'] = self._set_field_op
                if delete_many:
                    result = self.collection.update_many(query, self._update_commands, session=db_session)
                else:
                    result = self.collection.update_one(query, self._update_commands, session=db_session)
            else:
                result = self.collection.delete_many(
                    query, session=db_session) if delete_many else self.collection.delete_one(query, session=db_session)
        finally:
            self.clear_query()
            self._set_field_op.clear()
            self._update_commands.clear()
        return result

    def delete_all(self, generate_response=False, db_session=None):
        self._remove_stats(self._query_matcher, db_session)
        result = self.collection.delete_many(self._query_matcher, session=db_session)
        return self.to_response(result, operation=BaseDAO.DELETE) if generate_response else result

    def delete_by_id(self, entity_id, generate_response=False, db_session=None):
        self._query_matcher["_id"] = entity_id
        try:
            self._remove_stats(self._query_matcher, db_session)
            result = self.collection.delete_one(self._query_matcher, session=db_session)
        finally:
            self._query_matcher.clear()
        return self.to_response(result, operation=BaseDAO.DELETE) if generate_response else result

    def delete_many(self, ids, generate_response=False, db_session=None):
        try:
            if type(ids) is not list:
                for i in ids:
                    self._helper_list.append(i)
                ids = self._helper_list
            self._in_query['$in'] = ids
            self._query_matcher["_id"] = self._in_query
            self._remove_stats(self._query_matcher, db_session)
            result = self.collection.delete_many(self._query_matcher, session=db_session)
        finally:
            self._query_matcher.clear()
            self._in_query.clear()
            self._helper_list.clear()
        if generate_response:
            return self.to_response(result, operation=BaseDAO.DELETE)
        return result

    def simple_delete(self, key, value, generate_response=False, db_session=None, delete_many=True):
        self._query_matcher[key] = value
        try:
            self._remove_stats(self._query_matcher, db_session)
            if delete_many:
                result = self.collection.delete_many(self._query_matcher, session=db_session)
            else:
                result = self.collection.delete_one(self._query_matcher, session=db_session)
        finally:
            del self._query_matcher[key]
        return self.to_response(result) if generate_response else result

    def delete_all_nested(self, generate_response=False, db_session=None):
        """
        Regular deletes actually delete full documents from the (root) collection (except the dao_delete,
        which dynamically determines, if we try to do a true delete or a nested document removal)
        When, however, the DAO refers to nested documents in a collection, these documents
        must be removed with an update by removing the child document from its parent.
        """
        # These all assume that the nested documents are in an array. If this was not the case, we would
        # typically not really need an extra DAO for these nested 1-to-1 documents, but we would handle all
        # operations in the root/parent document. That's why this case is not explicitly supported (yet)
        if self.location:
            try:
                self._set_field_op[self._pull_loc] = self._helper_list
                self._update_commands['$set'] = self._set_field_op
                result = self.collection.update_many(self._query_matcher, self._update_commands, session=db_session)
            finally:
                self._set_field_op.clear()
                self._update_commands.clear()
            self._remove_stats(self._query_matcher, db_session)
            return self.to_response(result, operation=BaseDAO.DELETE) if generate_response else result
        else:
            raise NotImplementedError('This is only possible for DAOs referring to nested documents!')

    def delete_all_nested_at_id(self, entity_id, generate_response=False, db_session=None):
        try:
            self._query_matcher['_id'] = entity_id
            result = self.delete_all_nested(generate_response, db_session)
            return result
        finally:
            self._query_matcher.clear()

    def delete_all_nested_at_ids(self, ids, generate_response=False, db_session=None):
        try:
            if type(ids) is not list:
                for i in ids:
                    self._helper_list.append(i)
                ids = self._helper_list
            self._in_query['$in'] = ids
            self._query_matcher["_id"] = self._in_query
            result = self.delete_all_nested(generate_response, db_session)
            return result
        finally:
            self._in_query.clear()
            self._query_matcher.clear()
            self._helper_list.clear()

    def _delete_nested_docs(self, generate_response=False, db_session=None):
        if self.location:
            try:
                self._pull_op[self._pull_loc] = self._field_check
                self._update_commands['$pull'] = self._pull_op
                self._remove_stats(self._query_matcher, db_session)
                result = self.collection.update_one(self._query_matcher, self._update_commands, session=db_session)
            finally:
                self._pull_op.clear()
                self._update_commands.clear()
            return self.to_response(result, operation=BaseDAO.DELETE) if generate_response else result
        else:
            raise NotImplementedError('This is only possible for DAOs referring to nested documents!')

    def delete_nested_doc_by_id(self, entity_id, generate_response=False, db_session=None):
        """ Remove the nested DB document with the given ID from the array that contains this document """
        try:
            self._query_matcher[self._loc_prefix + '_id'] = entity_id
            self._field_check['_id'] = entity_id
            return self._delete_nested_docs(generate_response, db_session)
        finally:
            self._query_matcher.clear()
            self._field_check.clear()

    def delete_many_nested_in_doc(self, root_doc_id, ids_to_delete, generate_response=False, db_session=None):
        try:
            if type(ids_to_delete) is not list:
                for i in ids_to_delete:
                    self._helper_list.append(i)
                ids_to_delete = self._helper_list
            self._query_matcher['_id'] = root_doc_id
            self._in_query['$in'] = ids_to_delete
            self._field_check['_id'] = self._in_query
            return self._delete_nested_docs(generate_response, db_session)
        finally:
            self._query_matcher.clear()
            self._in_query.clear()
            self._field_check.clear()

    def delete_nested_doc_by_match(self, key, match_val, generate_response=False, db_session=None):
        if self.location:
            try:
                self._field_check[key] = match_val
                self._pull_op[self._pull_loc] = self._field_check
                self._update_commands['$pull'] = self._pull_op
                self._remove_stats(self._query_matcher, db_session)
                result = self.collection.update_many(self._query_matcher, self._update_commands, session=db_session)
            finally:
                self._field_check.clear()
                self._pull_op.clear()
                self._update_commands.clear()
            return self.to_response(result, operation=BaseDAO.DELETE) if generate_response else result
        else:
            raise NotImplementedError('This is only possible for DAOs referring to nested documents!')


class JoinableDAO(BaseDAO):
    __slots__ = ("_join_args", "_curr_joins", "_prev_joins", "join_queries", "_pipe_idx_map", "_join_id_template",
                 "_id_lookup_op", "_join_pipe", "_join_pipe_template", "_id_lookup_pipe", "_recurse_into_prefix",
                 "_nest_ref_prefix", "_join_let", "_join_expr", "_join_match", "_join_pipeline", "_join_subquery",
                 "_ids_lookup_op", "_user_proj", '_image_proj')

    def __init__(self, collection, model, payload_model, nested_loc=None):
        super().__init__(collection, model, payload_model, nested_loc)
        self._join_args = {}
        self._curr_joins = {}
        self._prev_joins = set()
        self.join_queries = {}
        self._pipe_idx_map = {}  # maps pipelines to its current index, if needed (for nested docs)
        self._join_id_template = {"from": None, "localField": None, "foreignField": "_id", "as": None}
        self._id_lookup_op = {"$lookup": self._join_id_template}
        self._join_pipe = []
        self._join_pipe_template = {"from": None, "localField": None, "pipeline": self._join_pipe,
                                    "foreignField": "_id", "as": None}
        self._id_lookup_pipe = {"$lookup": self._join_pipe_template}
        self._recurse_into_prefix = "into_"
        self._nest_ref_prefix = "nest_ref_"
        # $match is used to fire a query in an aggregation.
        # $expr is used to include aggregation expressions in a $match.
        self._join_let = {}  # TODO
        self._join_expr = {"$expr": None}
        self._join_match = {"$match": None}
        self._join_pipeline = []
        self._join_subquery = {"from": None, "let": self._join_let, "pipeline": self._join_pipeline, "as": None}
        self._ids_lookup_op = {"$lookup": self._join_subquery}
        # TODO: maybe add graphLookup, too
        self._user_proj = {'$project': {"hashedPass": 0}}
        self._image_proj = {'$project': {"thumbnail": 0, "image": 0}}
        # TODO: Maybe could use mongodb View as an additional alternative to join collections:
        #  https://www.mongodb.com/docs/manual/core/views/

    def __validate_refs(self, refd=None, keys=None):
        if self.location:
            return ''
        elif refd is None:
            refd = self
            keys = self.key_set.copy()
        else:
            refd = refd()
        res = None
        if refd._nested_path:
            nest_key = refd._nested_path[-1]
            nest_ids_key = nest_key + 'Parents'
            if nest_key in keys or nest_ids_key in keys:
                res = refd.location
            else:
                keys.add(nest_key)
                keys.add(nest_ids_key)
        if refd.references:
            for ref in refd.references.values():
                if type(ref) is not tuple:
                    if res is None:
                        res = self.__validate_refs(ref, keys)
                    else:
                        res += ' ' + self.__validate_refs(ref, keys)
        return res

    def _create_leaf_join(self, dao, as_field, address, is_array):
        if self.location is None:
            prefixes = (None,)
        elif self._nested_path is None:
            prefixes = (None, self._loc_prefix)
        else:
            prefixes = (None, *tuple('.'.join(self._nested_path[i:]) + '.' for i in range(len(self._nested_path))))
        for prefix in prefixes:
            if prefix is None:
                addr = address
                asf = as_field
            else:
                addr = prefix + address
                asf = prefix + as_field
            if dao.references is not None:
                lookup = deepcopy(self._id_lookup_pipe)
                lookup_templ = lookup["$lookup"]
                lookup_templ["localField"] = addr
                lookup_templ["from"] = dao.collection_name
                lookup_templ["as"] = asf
                self.join_queries[self._recurse_into_prefix + addr] = lookup
            lookup = deepcopy(self._id_lookup_op)
            lookup_templ = lookup["$lookup"]
            lookup_templ["localField"] = addr
            lookup_templ["from"] = dao.collection_name
            lookup_templ["as"] = asf
            self.join_queries[addr] = lookup
            if dao.collection_name == 'users':
                self.join_queries['u_p_' + addr] = self._user_proj
            elif dao.collection_name == 'images' and dao.location is None:
                self.join_queries['i_p_' + addr] = self._image_proj
            if not is_array:
                self.join_queries['uw_' + addr] = {'$unwind': {"path": '$' + asf,
                                                               "preserveNullAndEmptyArrays": True}}

    def __prepare_leaf_join(self, dao, as_field, address, is_array):
        if dao.location is not None:
            id_var = address + "Var"
            nested_key = "$" + as_field
            unwind = {"$unwind": nested_key}
            nest_pipe = [
                {"$group": {
                    "_id": "$_id",
                    as_field: {
                        "$push": "$" + dao.location
                    }
                }},
                unwind
            ]
            if dao._nested_path is not None:
                for _ in range(len(dao._nested_path) - 1):
                    nest_pipe.append(unwind)
                    nest_pipe.append(unwind)
            nest_pipe = nest_pipe + [
                {"$replaceRoot": {"newRoot": nested_key}},
                {"$project": {"root": "$$ROOT", "sameId": {"$eq": ["$$" + id_var, "$_id"]}}},
                {"$match": {"sameId": True}},
                {"$replaceRoot": {"newRoot": '$root'}},
            ]
            self.join_queries[self._nest_ref_prefix + address] = nest_pipe
            lookup_templ = {"localField": address, "from": dao.collection_name, "as": as_field,
                            "foreignField": dao.location + '._id', "let": {id_var: "$" + address},
                            "pipeline": []}
            lookup = {"$lookup": lookup_templ}
            self.join_queries[address] = lookup
            if not is_array:
                self.join_queries['uw_' + address] = {'$unwind': {"path": '$' + as_field,
                                                                  "preserveNullAndEmptyArrays": True}}
        else:
            self._create_leaf_join(dao, as_field, address, is_array)

    def __prepare_joins(self, dao, nested_loc=None):
        assert not self.__validate_refs(), (f'The names of nested keys "{self.__validate_refs()}" must also be unique '
                                            f'in the root level of the document schema!')
        for address, reference in dao.references.items():
            if isinstance(reference, tuple):
                as_field, dao, is_array = reference
                self.__prepare_leaf_join(dao(), as_field, address, is_array)
            else:
                new_address = nested_loc + '.' + address if nested_loc else address
                group_id = '$_id'
                if nested_loc:
                    group_id = [group_id, '$' + nested_loc + '._id']
                    merged_field = {address: '$' + address, address + "Parents": '$_id'}
                else:
                    merged_field = {address: '$' + address}
                address_key = '$' + new_address
                dao.join_queries['nested_' + new_address] = (
                    {'$unwind': {"path": address_key, "preserveNullAndEmptyArrays": True}},
                    {"$group": {
                        "_id": group_id,
                        address: {
                            "$push": address_key
                        },
                        "data": {"$first": '$$ROOT'},
                    }},
                    {"$replaceRoot": {"newRoot": {"$mergeObjects": ["$data", merged_field]}}}
                )

    def __prepare_nested_start(self):
        init_agg = []
        init_agg.extend(self._nested_as_root_agg)
        self.join_queries['init_nested'] = init_agg
        self.__prepare_joins(self)

    def _insert_stage_into_pipe(self, stage, pipeline):
        pipe_id = id(pipeline)
        if pipe_id in self._pipe_idx_map:
            idx = self._pipe_idx_map[pipe_id]
            pipeline.insert(idx, stage)
            self._pipe_idx_map[pipe_id] = idx + 1
        else:
            pipeline.append(stage)

    @staticmethod
    def _pipe_projection(pipeline):
        for agg in pipeline:
            if '$project' in agg:
                project = agg['$project']
                if 'root' not in project and 'sameId' not in project:
                    return project
        return None

    def should_traverse(self, hist):
        for p in self._curr_joins:
            if p.startswith(hist):
                return True
        return False

    def __join_field(self, address, reference, query, pipeline, path, path_cache, path_hist, unroll_depth, nest_lvl=0):
        new_path = f'{path}.{address}' if path else address
        if isinstance(reference, tuple):
            address, reference, is_array = reference
            reference = reference()
            path_hist = path_hist + '.' + address if path_hist else address
            for p in self._curr_joins:
                if p == path_hist:
                    unroll = self._curr_joins[p]
                    if unroll > unroll_depth:
                        unroll_depth = unroll
                elif 2 > unroll_depth and p.startswith(path_hist):
                    unroll_depth = 2
            if unroll_depth > 0:
                # reset path, because in the pipeline, we have to specify only the single joining field
                unwnd = new_pipe = None
                nest_ref_query = self._nest_ref_prefix + new_path
                nest_ref_id = path_hist + '-' + nest_ref_query
                if nest_lvl == 0 and nest_ref_id in self._prev_joins:
                    new_pipe = next(iter(query[new_path].values()))['pipeline']
                    self.__recurse_join(reference, reference.join_queries, new_pipe, None,
                                        path_cache, path_hist, unroll_depth - 1, 1)
                else:
                    ext_join_query = self._recurse_into_prefix + new_path
                    ext_query_id = path_hist + '-' + ext_join_query
                    query_id = path_hist + '-' + new_path
                    if query_id in self._prev_joins:
                        if unroll_depth > 1 and ext_join_query in query:
                            self._prev_joins.remove(query_id)
                            self._prev_joins.add(ext_query_id)
                            lookup = query[ext_join_query]
                            idx = pipeline.index(query[new_path])
                            pipeline[idx] = lookup
                            new_pipe = next(iter(lookup.values()))['pipeline']
                            self.__recurse_join(reference, reference.join_queries, new_pipe, None,
                                                path_cache, path_hist, unroll_depth - 1, nest_lvl)
                    elif ext_query_id in self._prev_joins:
                        new_pipe = next(iter(query[new_path].values()))['pipeline']
                        self.__recurse_join(reference, reference.join_queries, new_pipe, None,
                                            path_cache, path_hist, unroll_depth - 1, nest_lvl)
                    else:
                        if nest_lvl == 0 and nest_ref_query in query:
                            self._prev_joins.add(nest_ref_id)
                            do_recurse = unroll_depth > 1
                            lookup = query[new_path]
                            new_pipe = next(iter(lookup.values()))['pipeline']
                            new_pipe.clear()
                            new_pipe.extend(query[nest_ref_query])
                            nest_lvl = 1
                        else:
                            do_recurse = unroll_depth > 1 if ext_join_query in query else False
                            if do_recurse:
                                self._prev_joins.add(ext_query_id)
                                lookup = query[ext_join_query]
                                new_pipe = next(iter(lookup.values()))['pipeline']
                            else:
                                self._prev_joins.add(query_id)
                                lookup = query[new_path]
                        projection = 'u_p_' + new_path
                        if projection in query:
                            projection = deepcopy(query[projection])
                        else:
                            projection = 'i' + projection[1:]
                            if projection in query:
                                projection = deepcopy(query[projection])
                            else:
                                projection = None
                        if not is_array:
                            unwnd = query['uw_' + new_path]
                        if do_recurse:
                            self._insert_stage_into_pipe(lookup, pipeline)
                            query = reference.join_queries
                            path_cache = address if path is None else f'{path_cache}.{path}.{address}'
                            self.__recurse_join(reference, query, new_pipe, None,
                                                path_cache, path_hist, unroll_depth - 1, nest_lvl)  # reset nest level
                        else:
                            self._insert_stage_into_pipe(lookup, pipeline)
                        # handle projections
                        if unwnd is not None:
                            self._insert_stage_into_pipe(unwnd, pipeline)
                        if projection is not None:
                            if pipeline == self._agg_pipeline:
                                projection_ = self._projection_dict
                            else:
                                projection_ = self._pipe_projection(pipeline)
                            new_path = lookup['$lookup']['as']
                            if nest_lvl >= 2:
                                new_path = new_path[new_path.index(path.split('.')[-1]):]
                            if projection_ is None:
                                inner = projection['$project']
                                for proj, val in tuple(inner.items()):
                                    del inner[proj]
                                    inner[f'{new_path}.{proj}'] = val
                                pipeline.append(projection)
                            else:
                                for proj in projection['$project']:
                                    proj = f'{new_path}.{proj}'
                                    if proj not in projection_:
                                        projection_[proj] = 0
        else:
            path_hist = path_hist + '.' + address if path_hist else address
            if unroll_depth > 0 or self.should_traverse(path_hist):
                query_key = 'nested_' + new_path
                query_id = path_hist + '-' + query_key
                if query_id not in self._prev_joins:
                    self._prev_joins.add(query_id)
                    unwind, group, merge = query[query_key]
                    pipe_id = id(pipeline)
                    if pipe_id in self._pipe_idx_map:
                        idx = self._pipe_idx_map[pipe_id]
                        pipeline.insert(idx, unwind)
                        self._pipe_idx_map[pipe_id] = idx + 1  # add 1, because of the added unwind
                        if nest_lvl >= 1:
                            if path_cache in self._pipe_idx_map:
                                old_val = self._pipe_idx_map[path_cache]
                                if isinstance(old_val, str):
                                    self._pipe_idx_map[path_cache] = [new_path, old_val]
                                else:
                                    self._pipe_idx_map[path_cache].append(new_path)
                            else:
                                self._pipe_idx_map[path_cache] = new_path
                            if pipeline == self._agg_pipeline:
                                projection = self._projection_dict
                            else:
                                projection = self._pipe_projection(pipeline)
                            if projection is None:
                                projection = {'$project': {new_path: 0}}
                                pipeline.append(projection)
                            else:
                                for proj, val in tuple(projection.items()):
                                    if proj.startswith(new_path):
                                        del projection[proj]
                                        proj = proj.replace(new_path, address)
                                        projection[proj] = val
                                projection[new_path] = 0
                    else:
                        pipeline.append(unwind)
                        self._pipe_idx_map[pipe_id] = len(pipeline)
                    if self._pipe_projection(pipeline) is None:
                        pipeline.append(group)  # group and merge always close to the end
                        pipeline.append(merge)
                    else:
                        idx = len(pipeline) - 1
                        pipeline.insert(idx, merge)
                        pipeline.insert(idx, group)
                reference = reference()
                self.__recurse_join(reference, reference.join_queries, pipeline, new_path,
                                    path_cache, path_hist, unroll_depth, nest_lvl + 1)

    def __recurse_join(self, dao, query, pipeline, path, path_cache, path_hist, unroll_depth, nest_lvl=0):
        # decrement unroll_depth only here, if a step into a nested document should count as a further depth level
        if not dao.join_queries:
            dao.__prepare_joins(dao, path)
        if dao.references:
            if self._agg_pipeline != pipeline and nest_lvl == 0:
                pipeline.clear()
            for address, reference in dao.references.items():
                self.__join_field(address, reference, query, pipeline, path,
                                  path_cache, path_hist, unroll_depth, nest_lvl)

    def _perform_joins(self):
        # TODO: if fields of the references are non-included/excluded, then skip the corresponding lookup.
        #  Check the top-level projection (_projection_dict) only (perhaps by comparison to "path_hist")
        # if addressing_field=None then we join all fields
        try:
            nest_lvl = 0 if self.location is None else len(self._nested_path)
            if nest_lvl > 0:
                if 'init_nested' not in self.join_queries:
                    self.__prepare_nested_start()
                init_agg = self.join_queries['init_nested']
                for stage in init_agg:
                    self._agg_pipeline.append(stage)
            if None in self._join_args:
                self.__recurse_join(self, self.join_queries, self._agg_pipeline, None, '', '', self._join_args[None])
            if self._join_args:
                if not self.join_queries:
                    self.__prepare_joins(self)
                for address, refs in self.references.items():
                    self._curr_joins.clear()
                    ref_address = refs[0] if type(refs) is tuple else address
                    for path in self._join_args:
                        if path is None:
                            continue
                        if path == ref_address:
                            self.__join_field(address, refs, self.join_queries, self._agg_pipeline,
                                              None, '', '', self._join_args[ref_address])
                        elif path.startswith(ref_address):
                            self._curr_joins[path] = self._join_args[path]
                    if self._curr_joins:
                        self.__join_field(address, refs, self.join_queries, self._agg_pipeline,
                                          None, '', '', 0)
        finally:
            self._curr_joins.clear()
            self._prev_joins.clear()
        # clean up base projection
        if self._projection_dict:
            val = next(iter(self._projection_dict.values()))
            if any(p != val for p in self._projection_dict.values()):
                for key, val in tuple(self._projection_dict.items()):
                    if not val:
                        del self._projection_dict[key]
                for path in self._pipe_idx_map.values():
                    if isinstance(path, str):
                        self._projection_dict[path[path.rfind('.') + 1:] + 'Parents'] = 1

    def _add_address(self, address_path, unroll_depth):
        refs = self
        parts = address_path.split('.')
        for i, part in enumerate(parts):
            if part in refs.references:
                refs = refs.references[part]
                if type(refs) is tuple:
                    parts[i] = refs[0]
                    refs = refs[1]()
            elif part in refs.extended_schema:
                for ref in refs.references.values():
                    if type(ref) is tuple and part == ref[0]:
                        refs = ref[1]()
                        break
            else:
                raise ValueError(f"Field {part} is not a registered foreign key!")
        self._join_args['.'.join(parts)] = unroll_depth

    def join(self, addressing_fields=None, unroll_depth=1):
        if unroll_depth < 1:
            raise ValueError('The depth to join must be a positive integer!')
        if addressing_fields is None:
            self._join_args[addressing_fields] = unroll_depth
        else:
            if isinstance(addressing_fields, str):
                self._add_address(addressing_fields, unroll_depth)
            else:
                for field in addressing_fields:
                    self._add_address(field, unroll_depth)

    def _reconstruct_nested_docs(self, dao, doc, pimap, path=''):
        """
        Joined data of deeply nested documents are aggregated to the first/root level.
        This method puts the joined fields into the correct place, to where the nested doc belongs.
        """
        for address, reference in dao.references.items():
            if isinstance(reference, tuple):
                address, reference, _ = reference
                reference = reference()
                root = reference
            else:
                reference = reference()
                to_path = pimap.get(path, None)
                if to_path:
                    path_parts = to_path.split('.')
                    assert len(path_parts) >= 2, "should have at least 2 parts"
                    target = path_parts[-1]
                    id_str = target + 'Parents'
                    parents = doc[id_str][-1]
                    if parents:
                        data = doc[target]
                        if data:
                            prev_nest = None
                            parent_depth = len(path_parts) - 1
                            parent_idx_path = self._join_pipe
                            for i in range(len(path_parts)):
                                parent_idx_path.append(0)
                            done = False
                            nested = data[0]
                            prev_idx = 0
                            while not done:
                                trgt_doc = doc
                                for i, (field, idx) in enumerate(zip(path_parts, parent_idx_path)):
                                    if i == parent_depth:  # i.e. field == target
                                        start_idx = idx
                                        curr_id = parents[idx]
                                        for _ in range(len(parents)):
                                            idx += 1
                                            if idx >= len(parents):
                                                if start_idx > 0:
                                                    del nested[:start_idx]
                                                trgt_doc = prev_nest[prev_idx]
                                                trgt_doc[field] = nested
                                                if len(nested) == 1 and '_id' not in nested[0]:
                                                    nested.clear()
                                                done = True
                                                break
                                            elif parents[idx] == curr_id:
                                                del prev_nest[prev_idx]
                                            else:
                                                trgt_doc = prev_nest[prev_idx]
                                                doc_slice = nested[start_idx:idx]
                                                trgt_doc[field] = doc_slice
                                                if len(doc_slice) == 1 and '_id' not in doc_slice[0]:
                                                    doc_slice.clear()
                                                prev_idx += 1
                                                break
                                        if done:
                                            break
                                        parent_idx_path[i] = idx
                                    else:
                                        prev_nest = trgt_doc[field]
                                        if idx >= len(prev_nest):
                                            idx = 0
                                        trgt_doc = prev_nest[idx]
                                        parent_idx_path[i] = idx + 1
                            parent_idx_path.clear()
                        else:
                            pass
                    else:
                        doc[path_parts[0]] = parents
                    del doc[id_str]
                    del doc[target]
                root = self
            if isinstance(root, JoinableDAO) and address in doc:
                doc = doc[address]
                path = f'{path}.{address}' if path else address
                if type(doc) is list:
                    for d in doc:
                        self._reconstruct_nested_docs(reference, d, pimap, path)
                else:
                    self._reconstruct_nested_docs(reference, doc, pimap, path)

    def _cursor_generator(self, result, pipe_idx_map):
        for doc in result:
            self._reconstruct_nested_docs(self, doc, pipe_idx_map)
            yield doc

    def _is_reference_nested(self, key):
        # The following conditional does not filter out wrongly defined projections to nested fields
        # that do not exist, but this is not an issue, because mongodb will simply ignore them.
        # This method simply checks, if the key accesses a key from the extended schema.
        return self.extended_schema and any(key.startswith(nk) for nk in self.extended_schema)

    def _do_aggregate(self):
        return self._grouping_flag or self._agg_pipeline or self._join_args

    def _execute_aggregation(self, query, projection, get_cursor, db_session):
        try:
            if query:
                self._match_agg_clause['$match'] = query
                self._agg_pipeline.insert(0, self._match_agg_clause)
            if self._group_by_agg:
                self._agg_pipeline.append(self._agg_group)
            if self._join_args:
                self._is_unwound = True
                projection = self.build_projection(projection)
                self._perform_joins()
            else:
                projection = self.build_projection(projection)
            if projection:
                self._agg_pipeline.append(self._agg_projection)
            if self._sort_list:
                self._agg_sorter.clear()
                self._agg_sorter.update(self._sort_list)
                self._agg_pipeline.append(self._agg_sort)
            if self._skip_results:
                self._agg_pipeline.append(self._skip_agg)
            if self._limit_results:
                self._agg_pipeline.append(self._limit_agg)
            # print("Executing aggregation:", cls._agg_pipeline)
            if get_cursor:
                result = self.collection.aggregate(deepcopy(self._agg_pipeline), session=db_session)
            else:
                result = self.collection.aggregate(self._agg_pipeline, session=db_session)
                if not self._is_unwound and self.location:
                    res = []
                    for doc in result:
                        res += self._nested_get(doc)
                    result = res
                    self._helper_list.clear()
                else:
                    result = list(result)
            if self._pipe_idx_map:
                if get_cursor:
                    result = self._cursor_generator(result, self._pipe_idx_map.copy())
                else:
                    for doc in result:
                        self._reconstruct_nested_docs(self, doc, self._pipe_idx_map)
                self._pipe_idx_map.clear()
        except Exception as e:
            self._pipe_idx_map.clear()
            self._helper_list.clear()
            raise e
        finally:
            self._agg_pipeline.clear()
            self._join_args.clear()
        return result, projection


def transaction(method):
    # TODO: using transactions requires a mongodb replica set instance instead of a standalone server:
    #  https://stackoverflow.com/questions/51461952/mongodb-v4-0-transaction-mongoerror-transaction-numbers-are-only-allowed-on-a
    @wraps(method)
    def wrapper(*args, **kwargs):
        db_session = None
        if 'db_session' in kwargs:
            db_session = kwargs['db_session']
        elif args:
            db_session = args[-1]
            if not isinstance(db_session, ClientSession):
                db_session = None
        if db_session is None:
            db_session = client.cx.start_session()
            kwargs['db_session'] = db_session
            with db_session.start_transaction():
                result = method(*args, **kwargs)
            db_session.end_session()
        else:
            with db_session.start_transaction():
                result = method(*args, **kwargs)
        return result

    return wrapper


def get_dao_module_and_class_of_method(method):
    module = method.__module__
    imported = import_module(module)
    dao_classname = dao_module_class_dict[module[len(daos_path_prefix):]]
    return imported, dao_classname


def dao_query(find_many=True):
    def decorator(method):
        module, dao_classname = get_dao_module_and_class_of_method(method)

        @wraps(method)
        def query_wrapper(*args, **kwargs):
            dao = getattr(module, dao_classname)()
            query = method(*args)
            projection = kwargs.get('projection', None)
            result = dao.find(find_many, projection, query, kwargs.get('get_cursor', False),
                              kwargs.get('db_session', None))
            if kwargs.get('generate_response', False) and result is not None:
                return dao.to_response(result)
            return result

        return query_wrapper

    return decorator


def dao_delete(delete_many=True):
    def decorator(method):
        module, dao_classname = get_dao_module_and_class_of_method(method)

        @wraps(method)
        def delete_wrapper(*args, **kwargs):
            dao = getattr(module, dao_classname)()
            query = method(*args)
            result = dao.delete(delete_many, query, kwargs.get('db_session', None))
            if kwargs.get('generate_response', False):
                return dao.to_response(result, BaseDAO.DELETE)
            return result

        return delete_wrapper

    return decorator


def dao_update(update_many=True, update_stats=True):
    def decorator(method):
        module, dao_classname = get_dao_module_and_class_of_method(method)

        @wraps(method)
        def update_wrapper(*args, **kwargs):
            dao = getattr(module, dao_classname)()
            ops = method(*args)
            generate_response = kwargs.get('generate_response', False)
            if ops is None or not isinstance(ops, Iterable):
                result = dao.update(update_many, None, None, update_stats,
                                    generate_response, kwargs.get('db_session', None))
            else:
                query, upd_cmd = ops
                result = dao.update(update_many, query, upd_cmd, update_stats,
                                    generate_response, kwargs.get('db_session', None))
            if generate_response and result is not None:
                return dao.to_response(result, BaseDAO.UPDATE)
            return result

        return update_wrapper

    return decorator
