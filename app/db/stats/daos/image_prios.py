from app.db.stats.daos.base import CategoricalDocStatsDAO
from app.db.stats.models.image_doc import ImagePrioStat


class PrioStatsDAO(CategoricalDocStatsDAO):
    __slots__ = '_in_ids', '_prio_query'

    def __init__(self):
        super().__init__('imageprios', 'images', ImagePrioStat,
                         [
                             {"$unwind": {"path": "$objects", "preserveNullAndEmptyArrays": True}},
                             {"$unwind": {"path": "$objects.annotations", "preserveNullAndEmptyArrays": True}},
                             {
                                 "$group": {
                                     "_id": {"iid": "$_id", "oid": "$objects._id"},
                                     "annos": {"$push": "$objects.annotations"}
                                 }
                             },
                             {
                                 "$project": {
                                     'numAnnos': {"$size": "$annos"},
                                 }
                             },
                             {
                                 "$group": {
                                     "_id": "$_id.iid",
                                     "numUnannoObjs": {
                                         "$sum": {"$cond": [{"$eq": ["$numAnnos", 0]}, 1, 0]}
                                     },
                                     "numObjs": {"$sum": {"$cond": [{"$not": ["$_id.oid"]}, 0, 1]}},
                                 }
                             },
                             {
                                 "$project": {
                                     'prio': {"$cond": [{'$gt': ["$numObjs", 0]},
                                                        {"$divide": ["$numUnannoObjs", "$numObjs"]}, 1]},
                                 }
                             },
                         ])

        self._in_ids = {'$in': None}
        self._prio_query = {'_id': self._in_ids, 'prio': {'$ne': 0.0}}

    def find_prio_imgs(self, ids, tuples_list, db_session=None):
        try:
            self._in_ids['$in'] = ids
            self._projection_dict["prio"] = 1
            result = self.collection.find(self._prio_query, self._projection_dict, session=db_session)
            for doc in result:
                tuples_list.append((doc['_id'], doc['prio']))
        finally:
            del self._projection_dict['prio']
            self._in_ids['$in'] = None
        return tuples_list
