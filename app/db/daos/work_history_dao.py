from datetime import datetime

from pymongo import ASCENDING, DESCENDING

from app.db.daos.base import JoinableDAO, dao_query, dao_update
from app.db.daos.image_doc_dao import ImgDocDAO
from app.db.daos.project_dao import ProjectDAO
from app.db.daos.user_dao import UserDAO
from app.db.models.payloads.work_entry import WorkEntryPayload
from app.db.models.work_entry import WorkEntry
from app.db.stats.daos.work_stats import WorkHistoryStatsDAO


class WorkHistoryDAO(JoinableDAO):
    def __init__(self):
        # Initialize mongodb collection of work entry history
        super().__init__("history", WorkEntry, WorkEntryPayload)
        from app.db.daos.image_doc_dao import ImgDocDAO
        self.references = {
            'workerId': ('worker', UserDAO, False),
            'docId': ('document', ImgDocDAO, False),
            'projectId': ('project', ProjectDAO, False),
        }
        self.stat_references = (WorkHistoryStatsDAO,)
        self.create_index('work_entry_index', ('workerId', ASCENDING),
                          ('docId', ASCENDING), unique=True)

    @dao_query()
    def unrolled(self, unroll_depth=3):
        self.join(unroll_depth=unroll_depth)

    @dao_query(find_many=False)
    def find_entry(self, doc_id, worker_id, unroll_depth=None):
        """
        Find `DetectedObject`s that were created by user with given Id
        :param doc_id: Id of the image document
        :param worker_id: Id of the working annotator user
        :param unroll_depth: Whether to unroll the document and user information
        :return: List of entries if found
        """
        if unroll_depth:
            self.add_agg_match('docId', doc_id)
            self.add_agg_match('workerId', worker_id)
            self.join(unroll_depth=unroll_depth)
        else:
            self.add_query('docId', doc_id)
            self.add_query('workerId', worker_id)

    def find_worker_history(self, worker_id, projection=None, generate_response=False,
                            get_cursor=False, db_session=None):
        """
        Find `WorkEntry`s that were initiated by worker user with given Id
        :param worker_id: Id of the working annotator user
        :param projection:
        :param generate_response:
        :param get_cursor:
        :param db_session:
        :return: List of entries (or the cursor to these) if found
        """
        return self.simple_match('workerId', worker_id, projection, generate_response,
                                 db_session, get_cursor=get_cursor)

    def find_worker_history_ordered(self, worker_id, projection=None, generate_response=False,
                                    get_cursor=False, db_session=None):
        """
        Find `WorkEntry`s that were initiated by worker user with given Id, sorted by
         the latest update timestamp of that worker
        :param worker_id: Id of the working annotator user
        :param projection:
        :param generate_response:
        :param get_cursor:
        :param db_session:
        :return: List of entries (or the cursor to these) if found
        """
        self.sort_by('updatedAt')
        return self.find_worker_history(worker_id, projection, generate_response, get_cursor, db_session)

    def find_workers_recent_task(self, worker_id, projection=None, generate_response=False, db_session=None):
        """
        Find the most recent `WorkEntry` that the worker with the given User ID was working on.
        :param worker_id: Id of the working annotator user
        :param projection:
        :param generate_response:
        :param db_session:
        :return: Entry entity if found, None otherwise
        """
        projection = self.build_projection(projection)
        self._sort_list.append(('updatedAt', DESCENDING))
        self._query_matcher['workerId'] = worker_id
        self._ne_query['$ne'] = None
        self._ne_query['$exists'] = True
        self._query_matcher['projectId'] = self._ne_query
        result = self.collection.find_one(self._query_matcher, projection, sort=self._sort_list, session=db_session)
        self._sort_list.clear()
        self._query_matcher.clear()
        self._ne_query.clear()
        if projection:
            projection.clear()
        return result if result is None or not generate_response else self.to_response(result)

    @dao_query()
    def find_worker_history_by_project(self, worker_id, proj_id, n_fetch=None):
        """
        Find `WorkEntry`s that were initiated by worker user with given Id in the given project
        :param worker_id: Id of the working annotator user
        :param proj_id: Id of the project
        :param n_fetch: The number of entries to fetch
        :return: List of entries (or the cursor to these) if found
        """
        if n_fetch is not None:
            self.limit(n_fetch)
        self.sort_by('updatedAt')
        self.add_query('workerId', worker_id)
        self.add_query('projectId', proj_id)

    # @transaction
    def add(self, doc_id, worker_id=None, proj_id=None, is_finished=False, generate_response=False, db_session=None):
        # creates a new entry in the history collection
        if worker_id is None:
            worker_id = UserDAO().get_current_user_id()
        doc = WorkEntry(doc_id=doc_id, worker_id=worker_id, project_id=proj_id, is_finished=is_finished)
        return self.insert_doc(doc, generate_response=generate_response, db_session=db_session)

    def add_many(self, docs, worker_id=None, proj_id=None, generate_response=False, db_session=None):
        # creates a new entry in the history collection
        if worker_id is None:
            worker_id = UserDAO().get_current_user_id()
        for i, doc in enumerate(docs):
            docs[i] = WorkEntry(worker_id=worker_id, project_id=proj_id, **doc)
        return self.insert_docs(docs, generate_response=generate_response, db_session=db_session)

    def add_bulk(self, docs, worker_id=None, proj_id=None, db_session=None):
        # creates a new entry in the history collection
        if worker_id is None:
            worker_id = UserDAO().get_current_user_id()
        creation_ts = datetime.now()
        for i, (doc_id, is_finished) in enumerate(docs):
            docs[i] = WorkEntry(doc_id=doc_id, worker_id=worker_id, project_id=proj_id,
                                is_finished=is_finished, createdAt=creation_ts)
        return self.insert_docs(docs, generate_response=False, db_session=db_session)

    def update_or_add(self, doc_id, worker_id=None, proj_id=None, is_finished=None, db_session=None):
        if worker_id is None:
            worker_id = UserDAO().get_current_user_id()
        entry = self.find_entry(doc_id, worker_id, projection='_id')
        update_ts = datetime.now()
        if entry is None:
            if proj_id is True:
                proj_id = ImgDocDAO().find_by_id(doc_id, 'projectId', db_session=db_session)
                if proj_id is not None and 'projectId' in proj_id:
                    proj_id = proj_id['projectId']
                else:
                    proj_id = None
            entry = WorkEntry(doc_id=doc_id, worker_id=worker_id, project_id=proj_id,
                              is_finished=bool(is_finished), createdAt=update_ts)
            return self.insert_doc(entry, generate_response=False, db_session=db_session)[1]['_id']
        else:
            entry_id = entry['_id']
            self._query_matcher['_id'] = entry_id
            if is_finished is not None:
                self._set_field_op['isFinished'] = is_finished
            self._set_field_op['updatedAt'] = update_ts
            self._update_commands['$set'] = self._set_field_op
            self.collection.update_one(self._query_matcher, self._update_commands, session=db_session)
            return entry_id

    @dao_update(update_many=False)
    def start_working(self, doc_id, worker_id):
        # update timestamp
        self.add_query('docId', doc_id)
        self.add_query('workerId', worker_id)
        self.add_update('updatedAt', datetime.now())

    @dao_update(update_many=False)
    def finished_work(self, doc_id, worker_id):
        # update timestamp and is_finished=True
        self.add_query('docId', doc_id)
        self.add_query('workerId', worker_id)
        self.add_update('isFinished', True)
        self.add_update('updatedAt', datetime.now())

    @dao_update()
    def new_work_for_doc(self, doc_id):
        # is_finished=False for all entries with doc ID
        self.add_query('docId', doc_id)
        self.add_update('isFinished', False)
