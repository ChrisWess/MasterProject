from datetime import datetime

import numpy as np
from bson import ObjectId
from numpy.random import default_rng
from pymongo import ASCENDING

from app.db.daos.base import JoinableDAO, dao_update, dao_query, BaseDAO
from app.db.daos.image_doc_dao import ImgDocDAO
from app.db.daos.user_dao import UserDAO
from app.db.models.payloads.project import ProjectPayload
from app.db.models.project import Project
from app.db.stats.daos.image_prios import PrioStatsDAO
from app.db.stats.daos.project_progress import ProjectProgressDAO


class ProjectDAO(JoinableDAO):
    __slots__ = ('rng', '_accumweights', '_array_idx_agg', '_add_arr', '_slice_start', '_slice_array', '_slice_agg',
                 '_fetch_docs_agg')

    def __init__(self):
        # Initialize mongodb collection of projects
        super().__init__("projects", Project, ProjectPayload)
        self.references = {
            'memberIds': ('members', UserDAO, True),
            'docIds': ('documents', ImgDocDAO, True),
            'createdBy': ('creator', UserDAO, False),
        }
        self.stat_references = (ProjectProgressDAO,)
        self.create_index('project_title_index', ('title', ASCENDING), ('createdBy', ASCENDING))
        self.create_index('project_tag_index', ('tags', ASCENDING))
        self.create_index('member_index', ('memberIds', ASCENDING))
        # RNG for image fetching
        self.rng = default_rng()
        self._accumweights = []
        self._array_idx_agg = ['$docIds', None]
        self._add_arr = ['$idx', 0]
        self._slice_start = {'$add': self._add_arr}
        self._slice_array = ['$docIds', self._slice_start, 5]
        self._slice_agg = {'$slice': self._slice_array}
        self._fetch_docs_agg = [
            self._match_agg_clause,
            {'$project': {'idx': {'$indexOfArray': self._array_idx_agg},
                          'docIds': 1}},
            self._agg_projection,
        ]

    def find_by_project_title(self, title, projection=None, generate_response=False, db_session=None):
        """
        Find all Projects with the given title
        :param title: the string that should match the project title
        :param projection:
        :param generate_response:
        :param db_session:
        :return: Projects with the given title
        """
        return self.simple_match("title", title, projection, generate_response, db_session)

    @dao_query(find_many=False)
    def find_by_users_project_title(self, user_id, title):
        """
        Find the Project of a user with the given title
        :param user_id: the ID of the user who is a member is the project
        :param title: the string that should match the project title
        :return: Projects with the given title
        """
        self.add_query('createdBy', user_id)
        self.add_query('title', title)

    def find_by_users_project_title_with_stats(self, user_id, title, projection=None,
                                               generate_response=False, db_session=None):
        """
        Find the Project of a user with the given title
        :param user_id: the ID of the user who is a member is the project
        :param title: the string that should match the project title
        :param projection:
        :param generate_response:
        :param db_session:
        :return: Projects with the given title
        """
        result = self.find_by_users_project_title(user_id, title, projection=projection, db_session=db_session)
        if result is None:
            return None
        project_id = result['_id']
        result = self.payload_model(**result).to_dict()
        stats = ProjectProgressDAO().update_and_get(project_id, projection=('numDocs', 'progress'),
                                                    db_session=db_session)
        if stats:
            result['numDocs'] = stats['numDocs']
            result['progress'] = stats['progress']
        if generate_response:
            # model schema extended by stats (validated projects earlier)
            return self.to_response(result, validate=False)
        else:
            return result

    def find_by_image(self, doc_id, projection=None, generate_response=False, db_session=None):
        """
        Find all Projects that contain the image with the given ID
        :param doc_id: image document ID to search for
        :param projection:
        :param generate_response:
        :param db_session:
        :return: Projects that share the image
        """
        return self.simple_match("docIds", doc_id, projection, generate_response, db_session)

    def find_by_tag(self, user_id, projection=None, generate_response=False, db_session=None):
        """
        Find all Projects that the user with the given ID is a member of
        :param user_id: user ID to search for
        :param projection:
        :param generate_response:
        :param db_session:
        :return: Projects to which the specified user has access to
        """
        return self.simple_match("tags", user_id, projection, generate_response, db_session)

    def find_by_member(self, user_id, projection=None, generate_response=False, db_session=None):
        """
        Find all Projects that the user with the given ID is a member of
        :param user_id: user ID to search for
        :param projection:
        :param generate_response:
        :param db_session:
        :return: Projects to which the specified user has access to
        """
        return self.simple_match("memberIds", user_id, projection, generate_response, db_session)

    def find_by_creator(self, user_id, projection=None, generate_response=False, db_session=None):
        """
        Find all Projects that were created by the user with the given ID
        :param user_id: user ID to search for
        :param projection:
        :param generate_response:
        :param db_session:
        :return: Projects that were created by the specified user
        """
        return self.simple_match("createdBy", user_id, projection, generate_response, db_session)

    def find_all_of_user_with_progress(self, user_id, projection=None, generate_response=False, db_session=None):
        """
        Find all Projects of a member including the progress of the projects
        :param user_id: the ID of the project member
        :param projection:
        :param generate_response:
        :param db_session:
        :return: Projects that the user is a member of
        """
        result = self.find_by_member(user_id, projection=projection, db_session=db_session)
        if result:
            for i, res in enumerate(result):
                project_id = res['_id']
                res = self.payload_model(**res).to_dict()
                result[i] = res
                self._field_check[project_id] = res
                self._helper_list.append(project_id)
            stats = ProjectProgressDAO()
            stats.update(self._helper_list, db_session=db_session)
            stats = stats.find_stats_by_ids(self._helper_list, projection=('numDocs', 'progress'),
                                            get_cursor=True, db_session=db_session)
            for res in stats:
                if res['_id'] in self._field_check:
                    doc = self._field_check[res['_id']]
                    doc['numDocs'] = res['numDocs']
                    doc['progress'] = res['progress']
            self._field_check.clear()
            self._helper_list.clear()
        if generate_response:
            # model schema extended by stats (validated projects earlier)
            return self.to_response(result, validate=False)
        else:
            return result

    def _notin_annotator_history(self, project_id, doc_ids, db_session=None):
        user_id = UserDAO().get_current_user_id()
        from app.db.daos.work_history_dao import WorkHistoryDAO
        docs = WorkHistoryDAO().find_worker_history_by_project(user_id, project_id, projection='docId',
                                                               get_cursor=True, db_session=db_session)
        id_set = {doc['docId'] for doc in docs}
        idx = 0
        while idx < len(doc_ids):
            did = doc_ids[idx]
            if did in id_set:
                del doc_ids[idx]
            else:
                idx += 1
        if doc_ids:
            return PrioStatsDAO().find_prio_imgs(doc_ids, self._helper_list, db_session=db_session)
        else:
            result = PrioStatsDAO().find_all_stats('prio', get_cursor=True, db_session=db_session)
            for doc in result:
                self._helper_list.append((doc['_id'], doc['prio']))
            return self._helper_list

    def random_fetch(self, project_id, n_fetch=1, filter_user_history=True, projection=None,
                     generate_response=False, db_session=None):
        """
        Randomly select an image document given their prio scores as weights
        :param project_id: ID of the current project
        :param n_fetch: The number of samples to fetch
        :param filter_user_history: Flag that denotes whether to filter out all `ImgDoc`s in the annotator's history.
        :param projection:
        :param generate_response:
        :param db_session:
        :return: random ImgDoc object
        """
        docs = self.find_by_id(project_id, 'docIds')
        if docs is None:
            return None
        proj_doc_ids = docs['docIds']
        if not proj_doc_ids:
            return proj_doc_ids
        num_proj_docs = len(proj_doc_ids)  # number of docs in the project (max possible result size)
        if n_fetch > num_proj_docs:
            return ImgDocDAO().find_many(proj_doc_ids, projection, generate_response, db_session=db_session)
        total_prio = ProjectProgressDAO().update_and_get(project_id, 'totalPrio',
                                                         db_session=db_session)['totalPrio']
        if filter_user_history:
            self._notin_annotator_history(project_id, proj_doc_ids, db_session)
        else:
            PrioStatsDAO().find_prio_imgs(proj_doc_ids, self._helper_list, db_session=db_session)
        num_docs = len(self._helper_list)
        if num_docs == 0:
            for idx in self.rng.choice(num_proj_docs, size=n_fetch, replace=False):
                self._helper_list.append(proj_doc_ids[int(idx)])
            result = ImgDocDAO().find_many(self._helper_list, projection, generate_response, db_session=db_session)
            self._helper_list.clear()
            return result
        elif num_docs > 1:
            # TODO: Also interesting to compute the thoroughness as "thorough" = num_annos / num_objs.
            if n_fetch >= num_docs:
                for i, doc in enumerate(self._helper_list):
                    self._helper_list[i] = doc[0]
                result = ImgDocDAO().find_many(self._helper_list, projection, generate_response, db_session=db_session)
                self._helper_list.clear()
                return result
            elif total_prio == 0.0:
                if n_fetch > 1:
                    for idx in self.rng.choice(num_docs, size=n_fetch, replace=False):
                        self._accumweights.append(self._helper_list[int(idx)][0])
                    result = ImgDocDAO().find_many(self._accumweights, projection,
                                                   generate_response, db_session=db_session)
                    self._accumweights.clear()
                    self._helper_list.clear()
                    return result
                else:
                    result = ImgDocDAO().find_by_id(self._helper_list[self.rng.choice(num_docs)][0], projection,
                                                    generate_response, db_session=db_session)
                    self._helper_list.clear()
                    return result
            if n_fetch > 1:
                cumweights = 0.0
                self._accumweights.append(cumweights)
                i_, i, started = 0, 0, -1
                yielded_idxs, mprios, result = set(), [], []
                rpos = self.rng.random(n_fetch) * total_prio
                while len(result) < n_fetch:
                    if i_ < num_docs:
                        cumweights += self._helper_list[i_][1]
                        self._accumweights.append(cumweights)
                    if i == started and i_ > num_docs:
                        if i not in yielded_idxs:
                            result.append(self._helper_list[i][0])
                    else:
                        matches = np.sum(np.logical_and(self._accumweights[i] <= rpos,
                                                        rpos < self._accumweights[i + 1])).item()
                        if matches:
                            if started == -1:
                                started = i
                            id_, prio = self._helper_list[i]
                            if matches > 2:
                                for j in range(matches - 1):
                                    mprios.append(prio)
                            elif matches == 2:
                                mprios.append(prio)
                            result.append(id_)
                            yielded_idxs.add(i)
                        elif mprios:
                            # Retrieve the next image with a >=prio as one of the overflown matches
                            id_, prio = self._helper_list[i]
                            for j, mprio in enumerate(mprios):
                                if prio >= mprio:
                                    result.append(id_)
                                    yielded_idxs.add(i)
                                    del mprios[j]
                                    break
                    i_ = i_ + 1
                    while i_ in yielded_idxs:
                        i_ += 1
                    i = i_ % num_docs
                self._accumweights.clear()
                self._helper_list.clear()
                return ImgDocDAO().find_many(result, projection, generate_response, db_session=db_session)
            else:
                rpos = self.rng.random() * total_prio
                if rpos > total_prio / 2:
                    cumval = total_prio
                    for i, prio in reversed(self._helper_list):
                        new_val = cumval - prio
                        if new_val <= rpos < cumval:
                            self._helper_list.clear()
                            return ImgDocDAO().find_by_id(i, projection, generate_response, db_session=db_session)
                        cumval = new_val
                else:
                    cumval = 0.0
                    for i, prio in self._helper_list:
                        new_val = cumval + prio
                        if cumval <= rpos < new_val:
                            self._helper_list.clear()
                            return ImgDocDAO().find_by_id(i, projection, generate_response, db_session=db_session)
                        cumval = new_val
                raise ValueError("Did not fetch an image!")  # If this happens, algo has an error
        else:
            i = self._helper_list[0][0]
            self._helper_list.clear()
            return ImgDocDAO().find_by_id(i, projection, generate_response, db_session=db_session)

    def find_new_doc_slice(self, project_id, curr_doc_id, num_fetch, projection=None,
                           generate_response=False, db_session=None):
        num_docs = ProjectProgressDAO().update_and_get(project_id, 'numDocs', db_session=db_session)
        if num_docs is None:
            return None
        num_docs = num_docs['numDocs']
        prev_flag = num_fetch < 0
        if prev_flag:
            self._add_arr[1] = 1
            num_fetch = - num_fetch
        else:
            self._add_arr[1] = - num_fetch
        if num_fetch >= num_docs:
            result = self.find_by_id(project_id, 'docIds', db_session=db_session)
            if result is None:
                return None
            result = result['docIds']
            res_idx = result.index(curr_doc_id)
            del result[res_idx]
            if res_idx == 0 or res_idx == num_docs - 1:
                sort_arg = 'createdAt'
            else:
                sort_arg = None
                result = result[res_idx:] + result[:res_idx]
            return ImgDocDAO().find_many_retain_order(result, sort_arg, projection=projection,
                                                      generate_response=generate_response, db_session=db_session)
        self._slice_array[2] = num_fetch
        self._array_idx_agg[1] = curr_doc_id
        self._projection_dict['idSlice'] = self._slice_agg
        self._projection_dict['idx'] = 1
        self._query_matcher['_id'] = project_id
        self._match_agg_clause['$match'] = self._query_matcher
        result = self.collection.aggregate(self._fetch_docs_agg, session=db_session)
        try:
            result = next(result)
            slce = result['idSlice']
            if num_fetch > len(slce):
                self._slice_array[1] = 0
                del self._projection_dict['idx']
                self._agg_pipeline.append(self._match_agg_clause)
                self._agg_pipeline.append(self._agg_projection)
                if not prev_flag and result['idx'] - num_fetch < 0:
                    # All IDs from indices 0 to (result['idx'] - 1)
                    self._slice_array[2] = result['idx']
                else:  # i.e. not prev_flag and result['idx'] + num_fetch > result['numDocsTotal']
                    # All IDs from 0 to (result['idx'] + num_fetch - result['numDocsTotal'])
                    self._slice_array[2] = result['idx'] + 1 + num_fetch - num_docs
                missing_slice = next(self.collection.aggregate(self._agg_pipeline, session=db_session))['idSlice']
                for i, doc in enumerate(reversed(tuple(missing_slice))):
                    missing_slice[i] = doc
                missing_slice.extend(reversed(slce))
                slce = missing_slice
                self._slice_array[1] = self._slice_start
                self._agg_pipeline.clear()
                sort_arg = None
            else:
                sort_arg = 'createdAt'
            self._projection_dict.clear()
            self._query_matcher.clear()
            return ImgDocDAO().find_many_retain_order(slce, sort_arg, projection=projection,
                                                      generate_response=generate_response, db_session=db_session)
        except StopIteration:
            self._projection_dict.clear()
            self._query_matcher.clear()
            return None

    @dao_query()
    def unrolled(self, unroll_depth=2):
        self.join(unroll_depth=unroll_depth)

    @dao_query()
    def unroll_project_images(self, project_id, unroll_depth=5):
        self.add_query('_id', project_id)
        self.join('docIds', unroll_depth)

    @staticmethod
    def export_as_dataset(doc_ids, data_format, exclude_features=False):
        if data_format.lower() == 'json':
            projection = ('name', 'fname', 'objects._id', 'objects.tlx', 'objects.tly', 'objects.brx',
                          'objects.bry', 'objects.label._id', 'objects.label.name', 'objects.label.categories',
                          'objects.annotations._id', 'objects.annotations.text',
                          'objects.annotations.concepts._id', 'objects.annotations.concepts.phraseWords')
            return ImgDocDAO().export_image_info(doc_ids, not exclude_features, projection=projection)
        else:
            return None  # TODO: add CSV format?

    def add(self, title, description=None, tags=None, initial_members=None, generate_response=False, db_session=None):
        # creates a new concept in the concepts collection
        user_id = UserDAO().get_current_user_id()
        if description is None:
            description = 'N/A'
        members = {ObjectId(user_id)}
        if initial_members:
            for member in initial_members:
                members.add(ObjectId(member))
        if tags:
            project = Project(title=title, description=description, tags=tags,
                              member_ids=list(members), created_by=user_id)
        else:
            project = Project(title=title, description=description, member_ids=list(members), created_by=user_id)
        return self.insert_doc(project, generate_response=generate_response, db_session=db_session)

    def add_idoc_to_project(self, project_id, doc_id, exist_check=True, generate_response=False, db_session=None):
        if exist_check and ImgDocDAO().find_by_id(doc_id, db_session=db_session) is None:
            raise ValueError(f'No Image Document with ID {doc_id} could be found!')
        self._set_field_op['updatedAt'] = datetime.now()
        self._update_commands['$set'] = self._set_field_op
        result = self.array_update('docIds', doc_id, where=('_id', project_id),
                                   update_many=False, db_session=db_session)
        del self._set_field_op['updatedAt']
        return self.to_response(result, BaseDAO.UPDATE) if generate_response else result

    def add_idocs_to_project(self, project_id, doc_ids, generate_response=False, db_session=None):
        self._set_field_op['updatedAt'] = datetime.now()
        self._update_commands['$set'] = self._set_field_op
        result = self.array_push_many('docIds', doc_ids, where=('_id', project_id),
                                      update_many=False, db_session=db_session)
        del self._set_field_op['updatedAt']
        return self.to_response(result, BaseDAO.UPDATE) if generate_response else result

    def remove_idoc_from_project(self, project_id, doc_id, delete_doc=True, generate_response=False, db_session=None):
        if delete_doc:
            result = ImgDocDAO().delete_by_id(doc_id, db_session=db_session)
            was_found = bool(result.deleted_count)
        else:
            result = ImgDocDAO().remove_project_id(doc_id, db_session=db_session)
            was_found = bool(result.modified_count)
        if not was_found:
            return None
        self._set_field_op['updatedAt'] = datetime.now()
        self._update_commands['$set'] = self._set_field_op
        result = self.array_update('docIds', doc_id, ('_id', project_id), False,
                                   False, db_session=db_session)
        del self._set_field_op['updatedAt']
        return self.to_response(result, BaseDAO.UPDATE) if generate_response else result

    @dao_update(update_many=False, update_stats=False)
    def rename(self, project_id, new_title):
        self.add_query("_id", project_id)
        self.add_update('title', new_title)

    def add_member(self, project_id, user_email, generate_response=False, db_session=None):
        user = UserDAO().find_by_email(user_email, '_id')
        if user is None:
            return None
        response = self.array_update('members', user['_id'], ('_id', project_id), update_many=False,
                                     notify_stats=False, db_session=db_session)
        return self.to_response(response, BaseDAO.UPDATE) if generate_response else response

    def delete_all_cascade(self, generate_response=False, db_session=None):
        doc_ids = self.find_all(projection='docIds', get_cursor=True, db_session=db_session)
        for docs in doc_ids:
            self._helper_list.extend(docs['docIds'])
        ImgDocDAO().delete_many(self._helper_list, db_session=db_session)
        self._helper_list.clear()
        return self.delete_all(generate_response, db_session)

    def delete_many_cascade(self, project_ids, generate_response=False, db_session=None):
        doc_ids = self.find_many(project_ids, projection='docIds', get_cursor=True, db_session=db_session)
        for docs in doc_ids:
            self._helper_list.extend(docs['docIds'])
        ImgDocDAO().delete_many(self._helper_list, db_session=db_session)
        self._helper_list.clear()
        return self.delete_many(project_ids, generate_response, db_session)

    def delete_by_id_cascade(self, project_id, generate_response=False, db_session=None):
        doc_ids = self.find_by_id(project_id, projection='docIds', db_session=db_session)
        if doc_ids is None:
            return None
        ImgDocDAO().delete_many(doc_ids['docIds'], db_session=db_session)
        return self.delete_by_id(project_id, generate_response, db_session)
