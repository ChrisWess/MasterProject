from abc import abstractmethod
from copy import deepcopy
from datetime import timedelta, datetime
from functools import wraps
from time import sleep

from bson import ObjectId
from pymongo import UpdateOne, DESCENDING, InsertOne

from app import mdb
from app.db.daos.base import AbstractDAO
from app.db.daos.user_dao import UserDAO
from app.db.models.user import UserRole


class AbstractStatsDAO(AbstractDAO):
    @abstractmethod
    def invalidate_cache(self, locs=None, db_session=None):
        pass


class AbstractCategoricalDocStatsDAO(AbstractStatsDAO):
    __slots__ = ("_conf_keys", "refer_coll_name", "data_coll", "model", "_fetch_stat_query", "_invalidate_cache",
                 "_in_ids_op", "_bulk_update", "_id_match_op", "_projection_dict")

    def __init__(self, stat_coll, data_coll, stat_model):
        super().__init__(stat_coll)
        self._conf_keys = {'_id', 'isValid', 'updatedAt'}
        self.refer_coll_name = data_coll
        self.data_coll = getattr(mdb, data_coll)
        self.model = stat_model
        self._fetch_stat_query = {}  # ID matches the referring document
        self._in_ids_op = {}
        self._invalidate_cache = {'$set': {'isValid': False}}

        self._bulk_update = []
        self._id_match_op = {'$match': self._fetch_stat_query}
        self._projection_dict = {}

    def stat_keys(self, stat_model):
        return set(stat_model.model_json_schema()['example']) - self._conf_keys

    def build_projection(self, projection):
        if not projection:
            self._projection_dict['isValid'] = 0
            self._projection_dict['updatedAt'] = 0
            return self._projection_dict
        if isinstance(projection, str):
            self._projection_dict[projection] = 1
        elif isinstance(projection, (list, tuple, set)):
            for key in projection:
                self._projection_dict[key] = 1
        else:  # here: projection should be a sort of dict (key-value mapping) => needs items-method (iterator).
            is_inclusion = False  # can not mix inclusion with exclusion (either only 0 or only 1)
            for key, val in projection.items():
                try:
                    val = int(val)
                    # prioritize inclusion: if any value is 1,
                    # then clear all exclusions=0 & keep only inclusions=1
                    if val == 1:
                        if not is_inclusion:
                            is_inclusion = True
                            self._projection_dict.clear()
                        self._projection_dict[key] = val
                    elif val == 0:
                        if is_inclusion:
                            continue
                        else:
                            self._projection_dict[key] = val
                except ValueError:
                    pass
            if not is_inclusion:
                self._projection_dict['isValid'] = 0
                self._projection_dict['updatedAt'] = 0
        return self._projection_dict

    def to_response(self, result):
        if isinstance(result, list):
            for res in result:
                if '_id' in res:
                    res['_id'] = str(res['_id'])
            return {"result": result, "numResults": len(result),
                    "status": 200, 'model': self.model.__name__, 'isComplete': True}
        if '_id' in result:
            result['_id'] = str(result['_id'])
        return {"result": result, "numResults": 1, "status": 200,
                'model': self.model.__name__, 'isComplete': True}

    @staticmethod
    def _sort_result(result, sorting, do_skip):
        if do_skip:
            sort_by_id_flag = False
            for key in sorting:
                if key == '_id' or (type(key) is tuple and key[0] == '_id'):
                    sort_by_id_flag = True
            if not sort_by_id_flag:
                sorting.append('_id')
        return result.sort(sorting)

    def find_all_stats(self, projection=None, generate_response=False, get_cursor=False, db_session=None, **kwargs):
        try:
            projection = self.build_projection(projection)
            if get_cursor and projection:
                projection_copy = deepcopy(projection)
                projection.clear()
                projection = projection_copy
            result = self.collection.find(self._fetch_stat_query, projection, session=db_session)
            skip = kwargs.get('skip', None)
            sort = kwargs.get('sort', None)
            if sort:
                result = self._sort_result(result, sort, skip is not None)
            if skip is not None:
                result = result.skip(skip)
            limit = kwargs.get('limit', None)
            if limit is not None:
                result = result.limit(limit)
            if not get_cursor:
                result = list(result)
                if projection:
                    projection.clear()
        except Exception as e:
            if projection:
                projection.clear()
            raise e
        return self.to_response(result) if not get_cursor and generate_response else result

    def find_stats_by_ids(self, doc_ids, projection=None, generate_response=False, get_cursor=False, db_session=None):
        assert doc_ids, 'Neither None nor empty list allowed!'
        try:
            projection = self.build_projection(projection)
            self._in_ids_op['$in'] = doc_ids
            self._fetch_stat_query['_id'] = self._in_ids_op
            if get_cursor:
                projection_copy = deepcopy(projection) if projection else projection
                result = self.collection.find(deepcopy(self._fetch_stat_query), projection_copy, session=db_session)
            else:
                result = list(self.collection.find(self._fetch_stat_query, projection, session=db_session))
        finally:
            del self._fetch_stat_query['_id']
            del self._in_ids_op['$in']
            if projection:
                projection.clear()
        return self.to_response(result) if not get_cursor and generate_response else result

    def find_stats_by_id(self, doc_id, projection=None, generate_response=False, db_session=None):
        try:
            projection = self.build_projection(projection)
            self._fetch_stat_query['_id'] = doc_id
            result = self.collection.find_one(self._fetch_stat_query, projection, session=db_session)
        finally:
            del self._fetch_stat_query['_id']
            if projection:
                projection.clear()
        return self.to_response(result) if generate_response else result

    def find_stats(self, doc_ids=None, projection=None, generate_response=False, get_cursor=False, db_session=None):
        if doc_ids is None:
            return self.find_all_stats(projection, generate_response, get_cursor, db_session)
        elif type(doc_ids) is list:
            return self.find_stats_by_ids(doc_ids, projection, generate_response, get_cursor, db_session)
        else:
            return self.find_stats_by_id(doc_ids, projection, generate_response, db_session)

    def remove_stats(self, doc_ids=None, db_session=None):
        if doc_ids is None:
            self.collection.delete_many(self._fetch_stat_query, session=db_session)
        else:
            try:
                if type(doc_ids) is list:
                    try:
                        self._in_ids_op['$in'] = doc_ids
                        self._fetch_stat_query['_id'] = self._in_ids_op
                        self.collection.delete_many(self._fetch_stat_query, session=db_session)
                    finally:
                        del self._in_ids_op['$in']
                else:
                    self._fetch_stat_query['_id'] = doc_ids
                    self.collection.delete_one(self._fetch_stat_query, session=db_session)
            finally:
                del self._fetch_stat_query['_id']

    def invalidate_cache(self, doc_ids=None, db_session=None):
        if doc_ids is None:
            self.collection.update_many(self._fetch_stat_query, self._invalidate_cache, session=db_session)
        else:
            try:
                if type(doc_ids) is list:
                    try:
                        self._in_ids_op['$in'] = doc_ids
                        self._fetch_stat_query['_id'] = self._in_ids_op
                        self.collection.update_many(self._fetch_stat_query, self._invalidate_cache, session=db_session)
                    finally:
                        del self._in_ids_op['$in']
                else:
                    self._fetch_stat_query['_id'] = doc_ids
                    self.collection.update_one(self._fetch_stat_query, self._invalidate_cache, session=db_session)
            finally:
                del self._fetch_stat_query['_id']


class CategoricalDocStatsDAO(AbstractCategoricalDocStatsDAO):
    __slots__ = "_stat_agg"

    def __init__(self, stat_coll, data_coll, stat_model, stat_agg):
        super().__init__(stat_coll, data_coll, stat_model)
        # aggregation operation to compute the desired stats of the schema "stat_model", which will
        # be inserted into the stat collection with the same ID as the corresponding queried document
        self._stat_agg = stat_agg

    def update(self, doc_ids=None, force_update=False, generate_response=False, db_session=None):
        if doc_ids is not None and not doc_ids:
            doc_ids = None
        try:
            if not force_update:
                docs = self.find_stats(doc_ids, 'isValid', False, True, db_session)
                if doc_ids is None:
                    doc_infos = [(doc['_id'], doc['isValid']) for doc in docs]
                    self._projection_dict['_id'] = 1
                    if doc_infos:
                        for doc in doc_infos:
                            self._bulk_update.append(doc[0])
                        self._in_ids_op['$nin'] = self._bulk_update
                        self._fetch_stat_query['_id'] = self._in_ids_op
                    result = self.data_coll.find(self._fetch_stat_query, self._projection_dict, session=db_session)
                    del self._projection_dict['_id']
                    self._bulk_update.clear()
                    doc_ids = [doc['_id'] for doc in result]
                    if doc_infos:
                        del self._in_ids_op['$nin']
                        self._fetch_stat_query.clear()
                        doc_ids.extend(did for did, is_val in doc_infos if not is_val)
                else:
                    id_set = set(doc_ids) if type(doc_ids) is list else {doc_ids}
                    for doc in docs:
                        did = doc['_id']
                        if doc['isValid'] and did in id_set:
                            id_set.remove(did)
                    doc_ids = list(id_set)
            if doc_ids is None:
                result = self.data_coll.aggregate(self._stat_agg, session=db_session)
            elif doc_ids:
                self._stat_agg.insert(0, self._id_match_op)
                if type(doc_ids) is list:
                    if len(doc_ids) == 1:
                        self._fetch_stat_query['_id'] = doc_ids[0]
                    else:
                        self._in_ids_op['$in'] = doc_ids
                        self._fetch_stat_query['_id'] = self._in_ids_op
                else:
                    self._fetch_stat_query['_id'] = doc_ids
                result = self.data_coll.aggregate(self._stat_agg, session=db_session)
            elif generate_response:
                return {'result': [], "numUpdated": 0, "status": 200,
                        'model': self.model.__name__, 'isComplete': False}
            else:
                return doc_ids
            # TODO: result may be too large, which will cause memory issues. If this happens, split the
            #  update into batches and bulk_write these batches to the DB (also in MultiDimDocStatsDAO).
            if generate_response:
                result = list(result)
                if result:
                    new_time = datetime.now()
                    try:
                        for res in result:
                            res = self.model(**res, updated_at_ts=new_time).model_dump(by_alias=True)
                            self._bulk_update.append(UpdateOne({'_id': res['_id']}, {'$set': res}, upsert=True))
                        self.collection.bulk_write(self._bulk_update, session=db_session)
                    finally:
                        self._bulk_update.clear()
                    for res in result:
                        res['_id'] = str(res['_id'])
                result = {'result': result, "numUpdated": len(result), "status": 200,
                          'model': self.model.__name__, 'isComplete': True}
            else:
                new_time = datetime.now()
                try:
                    for res in result:
                        res = self.model(**res, updatedAt=new_time).model_dump(by_alias=True)
                        self._bulk_update.append(UpdateOne({'_id': res['_id']}, {'$set': res}, upsert=True))
                    if self._bulk_update:
                        self.collection.bulk_write(self._bulk_update, session=db_session)
                finally:
                    self._bulk_update.clear()
                result = doc_ids
        finally:
            if self._stat_agg[0] == self._id_match_op:
                del self._stat_agg[0]
            self._fetch_stat_query.clear()
        return result

    def update_and_get(self, doc_id, projection=None, generate_response=False, db_session=None):
        self.update(doc_id, db_session=db_session)
        return self.find_stats_by_id(doc_id, projection, generate_response, db_session)


class CategoricalIntervalUpdateStatsDAO(AbstractCategoricalDocStatsDAO):
    __slots__ = ("invalidate_after", "_stat_pipe", "id_mapping", "_in_ids", "_or_queries", "_or_ids", "_validity_check",
                 "_time_check", "_match_queries", "_match", "_project_agg", "_sort_list", "_sort_defs", "_sorting",
                 "_skip", "_limiter", "_agg_pipe")

    def __init__(self, stat_coll, data_coll, stat_model, id_mapping=None, invalidate_after_sec=6000):
        super().__init__(stat_coll, data_coll, stat_model)
        # It is not always possible or very difficult to keep track which data dimension caused the invalidation
        # of a stat. Therefore, we only cache stats in a time-based manner here => Do not register these DAOs
        # in their corresponding base DAO.
        self.invalidate_after = invalidate_after_sec
        if id_mapping is None:
            self.id_mapping = self._lookups = self._in_ids = self._or_queries = self._or_ids = self._time_check = None
            self._validity_check = self._match_queries = self._match = self._project_agg = self._sort_defs = None
            self._sorting = self._skip = self._limiter = self._agg_pipe = None
        else:
            self.id_mapping = id_mapping
            lookups = {}
            for key, dao in id_mapping.items():
                if type(dao) is tuple:
                    as_name, dao = dao
                else:
                    as_name = key
                lookups[as_name] = {
                    "$lookup": {
                        "from": dao().collection_name,
                        "localField": "_id." + key,
                        "foreignField": "_id",
                        "as": as_name,
                    }
                }
            self._lookups = lookups
            self._in_ids = {'$in': None}
            self._or_queries = [{'_id.' + key: None} for key in id_mapping]
            self._or_ids = {'$or': self._or_queries}
            self._time_check = {'$lt': None}
            self._validity_check = {'$or': [{'isValid': False}, {'updatedAt': self._time_check}]}
            self._match_queries = {}
            self._match = {"$match": None}
            self._project_agg = {'$project': self._projection_dict}
            self._sort_defs = {}
            self._sorting = {'$sort': self._sort_defs}
            self._skip = {'$skip': None}
            self._limiter = {'$limit': None}
            self._agg_pipe = []

    def check_invalid(self, db_session=None):
        is_coll_filled = self.collection.count_documents(self._fetch_stat_query, limit=1, session=db_session)
        if not is_coll_filled:
            return True
        self._time_check['$lt'] = datetime.now() - timedelta(0, self.invalidate_after)
        return bool(self.collection.count_documents(self._validity_check, limit=1, session=db_session))

    def to_response(self, result):
        id_map = tuple((dao_cls[0], dao_cls[1]()) if type(dao_cls) is tuple else (key, dao_cls())
                       for key, dao_cls in self.id_mapping.items())
        if isinstance(result, list):
            for res in result:
                for key, dao in id_map:
                    if key in res:
                        res[key] = dao.payload_model(**res[key]).to_dict()
                if '_id' in res:
                    id_dims = res['_id']
                    for dim, val in id_dims.items():
                        if type(val) is ObjectId:
                            id_dims[dim] = str(val)
            return {"result": result, "numResults": len(result),
                    "status": 200, 'model': self.model.__name__, 'isComplete': True}
        if '_id' in result:
            for key, dao in id_map:
                if key in result:
                    result[key] = dao.payload_model(**result[key]).to_dict()
            id_dims = result['_id']
            for dim, val in id_dims.items():
                if type(val) is ObjectId:
                    id_dims[dim] = str(val)
        return {"result": result, "numResults": 1, "status": 200,
                'model': self.model.__name__, 'isComplete': True}

    def _build_query(self, sort, limit, skip, expand_dims, projection, generate_response, get_cursor, db_session):
        try:
            self.build_projection(projection)
            if sort is not None:
                self._sort_defs.clear()
                if type(sort) is str:
                    self._sort_defs[sort] = DESCENDING
                else:
                    self._sort_defs.update(sort)
                self._agg_pipe.append(self._sorting)
            if skip is not None:
                self._skip['$skip'] = skip
                self._agg_pipe.append(self._skip)
            if limit is not None:
                self._limiter['$limit'] = limit
                self._agg_pipe.append(self._limiter)
            if expand_dims is not None:
                if type(expand_dims) is str:
                    self._agg_pipe.append(self._lookups[expand_dims])
                    self._agg_pipe.append({'$unwind': '$' + expand_dims})
                else:
                    for dim in expand_dims:
                        self._agg_pipe.append(self._lookups[dim])
                        self._agg_pipe.append({'$unwind': '$' + dim})
            if self._projection_dict:
                self._agg_pipe.append(self._project_agg)
            if get_cursor:
                agg = deepcopy(self._agg_pipe)
                result = self.collection.aggregate(agg, session=db_session)
            else:
                result = list(self.collection.aggregate(self._agg_pipe, session=db_session))
        finally:
            self._agg_pipe.clear()
            self._projection_dict.clear()
        return self.to_response(result) if not get_cursor and generate_response else result

    def find_dim_stats(self, dim_query, sort=None, limit=None, skip=None, expand_dims=None,
                       projection=None, generate_response=False, get_cursor=False, db_session=None):
        self._match['$match'] = dim_query
        self._agg_pipe.append(self._match)
        return self._build_query(sort, limit, skip, expand_dims, projection, generate_response, get_cursor, db_session)

    def find_by_dim_val(self, dim_key, dim_val, sort=None, limit=None, skip=None, expand_dims=None,
                        projection=None, generate_response=False, get_cursor=False, db_session=None):
        self._match_queries['_id.' + dim_key] = dim_val
        self._match['$match'] = self._match_queries
        self._agg_pipe.append(self._match)
        return self._build_query(sort, limit, skip, expand_dims, projection, generate_response, get_cursor, db_session)

    def remove_stats(self, doc_ids=None, db_session=None):
        if doc_ids is None:
            self.collection.delete_many(self._fetch_stat_query, session=db_session)
        else:
            if type(doc_ids) is list:
                self._in_ids['$in'] = doc_ids
                for query in self._or_queries:
                    for key in query:
                        query[key] = self._in_ids
                self.collection.delete_many(self._or_ids, session=db_session)
                self._in_ids_op['$in'] = None
            else:
                for query in self._or_queries:
                    for key in query:
                        query[key] = doc_ids
                self.collection.delete_many(self._or_ids, session=db_session)

    def invalidate_cache(self, doc_ids=None, db_session=None):
        if doc_ids is None:
            self.collection.update_many(self._fetch_stat_query, self._invalidate_cache, session=db_session)
        else:
            # invalidate if any value in id_vals is a value in the _id dict
            if type(doc_ids) is list:
                self._in_ids['$in'] = doc_ids
                for query in self._or_queries:
                    for key in query:
                        query[key] = self._in_ids
                self.collection.update_many(self._or_ids, self._invalidate_cache, session=db_session)
                self._in_ids_op['$in'] = None
            else:
                for query in self._or_queries:
                    for key in query:
                        query[key] = doc_ids
                self.collection.update_many(self._or_ids, self._invalidate_cache, session=db_session)


class CombinedCategoricalDocStatsDAO(CategoricalIntervalUpdateStatsDAO):
    __slots__ = "_accumulator_gen"

    def __init__(self, stat_coll, data_coll, stat_model, accumulator_gen, id_mapping=None, invalidate_after_sec=6000):
        super().__init__(stat_coll, data_coll, stat_model, id_mapping, invalidate_after_sec)
        self._accumulator_gen = accumulator_gen

    def update(self, force_update=False, generate_response=False, db_session=None):
        if not force_update and not self.check_invalid(db_session):
            return
        generator = self._accumulator_gen()
        if generate_response:
            result = list(generator)
            if result:
                try:
                    res = None
                    for res in result:
                        self._bulk_update.append(UpdateOne({'_id': res['_id']}, {'$set': res}, upsert=True))
                    self.collection.bulk_write(self._bulk_update, session=db_session)
                    if res is not None:
                        self._in_ids_op['$ne'] = res['updatedAt']
                        self._fetch_stat_query['updatedAt'] = self._in_ids_op
                        self.collection.delete_many(self._fetch_stat_query, session=db_session)
                finally:
                    self._bulk_update.clear()
                    self._in_ids_op.clear()
                    self._fetch_stat_query.clear()
                for res in result:
                    id_dims = res['_id']
                    for dim, val in id_dims.items():
                        id_dims[dim] = str(val)
            result = {'result': result, "numInserted": len(result), "status": 200,
                      'model': self.model.__name__, 'isComplete': True}
        else:
            try:
                res = None
                for res in generator:
                    self._bulk_update.append(UpdateOne({'_id': res['_id']}, {'$set': res}, upsert=True))
                if self._bulk_update:
                    self.collection.bulk_write(self._bulk_update, session=db_session)
                if res is not None:
                    self._in_ids_op['$ne'] = res['updatedAt']
                    self._fetch_stat_query['updatedAt'] = self._in_ids_op
                    self.collection.delete_many(self._fetch_stat_query, session=db_session)
                result = len(self._bulk_update)
            finally:
                self._bulk_update.clear()
                self._in_ids_op.clear()
                self._fetch_stat_query.clear()
        return result


class MultiDimDocStatsDAO(CategoricalIntervalUpdateStatsDAO):
    __slots__ = "_stat_pipe"

    def __init__(self, stat_coll, data_coll, stat_model, stat_agg_pipe, id_mapping, invalidate_after_sec=6000):
        super().__init__(stat_coll, data_coll, stat_model, id_mapping, invalidate_after_sec)
        self._stat_pipe = stat_agg_pipe

    def update(self, force_update=False, generate_response=False, db_session=None):
        if not force_update and not self.check_invalid(db_session):
            return
        self.collection.delete_many(self._fetch_stat_query, session=db_session)
        while self.collection.count_documents(self._fetch_stat_query, limit=1, session=db_session):
            sleep(0.2)
        result = self.data_coll.aggregate(self._stat_pipe, session=db_session)
        if generate_response:
            result = list(result)
            if result:
                new_time = datetime.now()
                try:
                    for res in result:
                        res = self.model(**res, updated_at_ts=new_time).model_dump(by_alias=True)
                        self._bulk_update.append(InsertOne(res))
                    self.collection.bulk_write(self._bulk_update, session=db_session)
                finally:
                    self._bulk_update.clear()
                for res in result:
                    id_dims = res['_id']
                    for dim, val in id_dims.items():
                        id_dims[dim] = str(val)
            result = {'result': result, "numInserted": len(result), "status": 200,
                      'model': self.model.__name__, 'isComplete': True}
        else:
            new_time = datetime.now()
            try:
                for res in result:
                    res = self.model(**res, updated_at_ts=new_time).model_dump(by_alias=True)
                    self._bulk_update.append(InsertOne(res))
                if self._bulk_update:
                    self.collection.bulk_write(self._bulk_update, session=db_session)
            finally:
                self._bulk_update.clear()
        return result


class BaseStatsDAO(AbstractStatsDAO):
    __slots__ = ("_conf_keys", "refer_coll_name", "data_coll", "models", "_fetch_stat_query", "_invalidate_cache",
                 "_aggregations", "_write_stat_op", "_projection_dict")

    def __init__(self, data_coll, models):
        super().__init__('stats')
        self._conf_keys = {'_id', 'isValid', 'updatedAt'}
        self.refer_coll_name = data_coll
        self.data_coll = getattr(mdb, data_coll)
        self.models = models
        self._fetch_stat_query = {'_id': ''}
        self._invalidate_cache = {'$set': {'isValid': False}}
        self._write_stat_op = {'$set': None}
        self._aggregations = {}
        self._projection_dict = {}

    def stat_keys(self, stat_model):
        return set(stat_model.model_json_schema()['example']) - self._conf_keys

    def _aggregate(self, method_name, db_session=None):
        model, agg = self._aggregations[method_name]
        if type(agg) is list:
            agg = self.data_coll.aggregate(agg)
            result = next(agg, None)
            if result is None:
                return None
        else:
            result = {}
            for key, methd in tuple(agg.items()):
                result[key] = methd(key)[key]
        result = model(**result).to_dict()
        self._write_stat_op['$set'] = result
        self.collection.update_one(self._fetch_stat_query, self._write_stat_op, upsert=True, session=db_session)
        self._write_stat_op['$set'] = None
        result['_id'] = self._fetch_stat_query['_id']
        del result['isValid']
        return result

    def invalidate_cache(self, _=None, db_session=None):
        # Not all updates that would influence the stats result must invalidate the cache (in order to increase
        # performance). To ensure up-to-date stats, an admin can force the recalculation of a stat upon request.
        try:
            self._projection_dict['isValid'] = 1
            for stat_id in self._aggregations:
                self._fetch_stat_query['_id'] = f'{self.refer_coll_name}_{stat_id}'
                is_valid = self.collection.find_one(self._fetch_stat_query, self._projection_dict, session=db_session)
                if is_valid is not None and is_valid['isValid']:
                    self.collection.update_one(self._fetch_stat_query, self._invalidate_cache, session=db_session)
        finally:
            self._projection_dict.clear()


def simple_stat(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        query = method(self, *args, **kwargs)
        if kwargs.get('execute', True):
            projection = kwargs.get('projection', None)  # TODO
            if type(query) is not list:
                query = [query]
            agg = self.data_coll.aggregate(query, session=kwargs.get('db_session', None))
            length = 0
            curr = next(agg, None)
            result = None
            while curr is not None:
                if length > 2:
                    result.append(curr)
                elif length == 2:
                    result = [result, curr]
                else:
                    result = curr
                length += 1
                curr = next(agg, None)
            return result
        return query

    return wrapper


def should_recalc(stat_data):
    return stat_data is None or (
            not stat_data['isValid'] and datetime.now() - timedelta(minutes=30) > stat_data['updatedAt'])


def force_exec(kwargs):
    force = kwargs.get('force', False)
    if force:
        role = UserDAO().get_current_user('role')
        if role is None:
            return False
        else:
            return role['role'] == UserRole.ADMIN.value
    return force


def cached(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        # The stat's IDs are its unique name
        method_name = method.__name__
        db_session = kwargs.get('db_session', None)
        self._fetch_stat_query['_id'] = f'{self.refer_coll_name}_{method_name}'
        stat = self.collection.find_one(self._fetch_stat_query, session=db_session)
        if force_exec(kwargs) or should_recalc(stat):
            if method_name not in self._aggregations:
                agg = method(self, *args, **kwargs)
                self._aggregations[method_name] = agg
            return self._aggregate(method_name, db_session)
        else:
            del stat['isValid']
            return stat

    return wrapper
