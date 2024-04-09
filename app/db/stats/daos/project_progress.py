from app.db.stats.daos.base import CategoricalDocStatsDAO
from app.db.stats.daos.image_prios import PrioStatsDAO
from app.db.stats.models.project import ProjectProgressStat


class ProjectProgressDAO(CategoricalDocStatsDAO):
    def __init__(self):
        super().__init__('progress', 'projects', ProjectProgressStat,
                         [
                             {"$unwind": {"path": "$docIds", "preserveNullAndEmptyArrays": True}},
                             {"$lookup": {"from": 'imageprios', "localField": 'docIds',
                                          "foreignField": "_id", "as": 'document'}},
                             {"$unwind": {"path": "$document", "preserveNullAndEmptyArrays": True}},
                             {
                                 "$group": {
                                     "_id": "$_id",
                                     "totalPrio": {"$sum": '$document.prio'},
                                     "numDocs": {"$sum": {"$cond": [{"$not": ["$document"]}, 0, 1]}},
                                 }
                             },
                             {
                                 "$project": {
                                     'numDocs': 1,
                                     'totalPrio': 1,
                                     'progress': {"$cond": [{'$gt': ["$numDocs", 0]},
                                                            {'$divide': [{"$subtract": ["$numDocs", "$totalPrio"]},
                                                                         "$numDocs"]}, 0]},
                                 }
                             },
                         ])

    def update(self, doc_ids=None, force_update=False, generate_response=False, db_session=None):
        if doc_ids is None:
            PrioStatsDAO().update(doc_ids, db_session=db_session)
            force_update = True
        else:
            self._projection_dict['docIds'] = 1
            if type(doc_ids) is list:
                self._in_ids_op['$in'] = doc_ids
                self._fetch_stat_query['_id'] = self._in_ids_op
                # if any of these idocs are invalid or missing, then force an update on the corresponding projects
                idocs = self.data_coll.find(self._fetch_stat_query, self._projection_dict, session=db_session)
                force_upd_list = None
                for doc in idocs:
                    dids = doc['docIds']
                    if dids:
                        dids = PrioStatsDAO().update(dids, db_session=db_session)
                        if dids:
                            if force_upd_list is None:
                                dids.clear()
                                force_upd_list = dids
                            force_upd_list.append(doc['_id'])
                self._in_ids_op.clear()
                self._fetch_stat_query.clear()
                self._projection_dict.clear()
                if force_upd_list:
                    super().update(force_upd_list, True, False, db_session)
            else:
                self._fetch_stat_query['_id'] = doc_ids
                idocs = self.data_coll.find_one(self._fetch_stat_query, self._projection_dict, session=db_session)
                if idocs is not None:
                    PrioStatsDAO().update(idocs['docIds'], db_session=db_session)
                    force_update = True
                self._fetch_stat_query.clear()
                self._projection_dict.clear()
        return super().update(doc_ids, force_update, generate_response, db_session)
