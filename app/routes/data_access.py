import json
from collections import defaultdict
from importlib import import_module
from math import ceil
from threading import Thread
from zipfile import ZipFile

from bson import ObjectId
from bson.errors import InvalidId
from flask import abort, Response, stream_with_context, request
from flask_pymongo import PyMongo
from gridfs import GridFS
from pymongo.errors import BulkWriteError

from app import application
from app.db.daos.dao_config import collection_dao_module_dict, dao_module_class_dict
from app.db.daos.image_doc_dao import ImgDocDAO
from app.db.daos.label_dao import LabelDAO
from app.db.daos.project_dao import ProjectDAO
from app.db.daos.user_dao import UserDAO
from app.db.daos.vis_feature_dao import VisualFeatureDAO
from app.db.daos.work_history_dao import WorkHistoryDAO
from app.db.models.user import UserRole


def get_dao_by_collection(collection_name):
    module_name = collection_dao_module_dict[collection_name]
    module = import_module('app.db.daos.' + module_name)
    return getattr(module, dao_module_class_dict[module_name])()


def is_user_admin():
    role = UserDAO().get_current_user('role')
    if role is None:
        return False
    else:
        return role['role'] == UserRole.ADMIN.value


@application.route('/export', methods=['GET'])
def data_export():
    # require admin privileges
    if not is_user_admin():
        abort(401, "Admin privileges required!")

    def generate():
        module_root = 'app.db.daos.'
        for i, module_name in enumerate(collection_dao_module_dict.values()):
            module = import_module(module_root + module_name)
            curr_dao = getattr(module, dao_module_class_dict[module_name])()
            prev_file = None
            for file in curr_dao.export():
                if prev_file is None:
                    prev_file = file
                    continue
                yield prev_file
                prev_file = file
            if prev_file is not None:
                if i != len(collection_dao_module_dict) - 1:
                    prev_file = prev_file + '|-|'
                yield prev_file

    return Response(stream_with_context(generate()), content_type='text/plain', status=200,
                    headers={'Content-Disposition': 'attachment; filename=full_export.ojx'})


@application.route('/export/<coll_key>', methods=['GET'])
def export_collection(coll_key):
    if not is_user_admin():
        abort(401, "Admin privileges required!")

    def generate():
        for file in get_dao_by_collection(coll_key).export():
            yield file

    return Response(stream_with_context(generate()), content_type='text/plain', status=200,
                    headers={'Content-Disposition': f'attachment; filename={coll_key}_export.ojx'})


def _import_file(data, coll, dao, nums_imported, abort_errors=False):
    coll_end_idx = data.index('->>')
    new_coll = data[:coll_end_idx]
    new_coll = new_coll[:new_coll.rindex('_')]
    if new_coll != coll:
        coll = new_coll
        dao = get_dao_by_collection(coll)
    try:
        nums_imported[coll].append(dao.import_into(data[coll_end_idx + 4:]))
    except BulkWriteError as e:
        e = str(e)
        application.logger.error(e)
        if abort_errors:
            abort(400, e)
    return coll, dao


@application.route("/import", methods=["POST"])
def data_import():
    # By moving through chunks with a fixed bitrate, a file might get split up between two or more chunks.
    # The data of a split file is loaded into file_data until the file has been fully read.
    max_length = application.config['MAX_CONTENT_LENGTH']
    application.config['MAX_CONTENT_LENGTH'] = None
    try:
        if 'file' not in request.files:
            abort(400, 'No file part')
        file = request.files['file']
        if file.filename == '':
            abort(400, 'No selected file')
        file_stream = file.stream
        nums_imported = defaultdict(list)
        curr_dao = curr_coll = file_data = None
        chunk_size = 8192  # You can adjust the chunk size as needed
        while True:
            chunk = file_stream.read(chunk_size)
            if not chunk:
                break
            chunk = chunk.decode('utf-8')
            file_start_idx = 0
            next_file_idx = chunk.find('|-|')  # when the current file ends
            while next_file_idx != -1:
                file_end = chunk[file_start_idx:next_file_idx]
                if file_data:
                    file_data += file_end
                else:
                    file_data = file_end
                curr_coll, curr_dao = _import_file(file_data, curr_coll, curr_dao, nums_imported)
                file_data = None
                file_start_idx = next_file_idx + 3
                next_file_idx = chunk.find('|-|', file_start_idx)
            if file_start_idx != 0:
                chunk = chunk[file_start_idx:]
            if file_data:
                file_data = file_data + chunk
            else:
                file_data = chunk

        if curr_dao is not None and file_data:
            _import_file(file_data, curr_coll, curr_dao, nums_imported)
        nums_imported = dict(nums_imported)
        for coll, nums in nums_imported.items():
            nums_imported[coll] = sum(nums)
        application.logger.info(f"Documents imported: {nums_imported}")
    finally:
        application.config['MAX_CONTENT_LENGTH'] = max_length
    return {'status': 200, 'result': nums_imported}


@application.route("/dataset/export/<project_id>", methods=["GET"])
def dataset_export(project_id):
    args = request.args
    exclude_features = args.get('exclude_features', False)
    out_format = args.get('out_format', 'json')
    try:
        project = ProjectDAO().find_by_id(ObjectId(project_id), projection=('title', 'docIds'))
        if project is None:
            err_msg = "No project with the given ID could be found!"
            application.logger.error(err_msg)
            abort(404, err_msg)
        title, doc_ids = project['title'], project['docIds']
        if not doc_ids:
            err_msg = f'Project "{title}" contains no documents (empty dataset)!'
            application.logger.error(err_msg)
            abort(404, err_msg)
        title = title.replace(' ', '_')
        project = ProjectDAO().export_as_dataset(doc_ids, out_format, exclude_features)
        return Response(stream_with_context(project), content_type='text/plain', status=200,
                        headers={'Content-Disposition': f'attachment; filename={title}_dataset.json'})
    except InvalidId:
        err_msg = "The Project ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


def _handle_gridfs_file_upload(batch):
    client = PyMongo(application, connect=True, serverSelectionTimeoutMS=5000)
    fs = GridFS(client.db)
    for doc, img, thumb in batch:
        doc.image = fs.put(img)
        doc.thumbnail = fs.put(thumb)


def _execute_file_upload(batch, num_threads=3):
    batch_slice = ceil(len(batch) / num_threads)
    threads = []
    for i in range(num_threads):
        batch_start = i * batch_slice
        batch_end = batch_start + batch_slice
        t = Thread(target=_handle_gridfs_file_upload, args=(batch[batch_start:batch_end],))
        t.start()
        threads.append(t)
    for thread in threads:
        thread.join()
    for i, t in enumerate(batch):
        batch[i] = t[0]


def _add_to_batch(doc, new_docs, bulk_size, batch, has_worked, project_id):
    if bulk_size > 1:
        if len(doc) == 4:
            batch.append(doc[0:-1])
            has_worked.append(doc[-1])
        else:
            batch.append(doc)
            has_worked.append(None)
        if len(batch) >= bulk_size:
            _execute_file_upload(batch)
            batch = ImgDocDAO().insert_docs(batch, generate_response=False)
            new_docs.extend(doc['_id'] for doc in batch)
            application.logger.info(f'Imported a batch of {bulk_size} Image Documents into project {project_id}!')
            batch.clear()
    else:
        doc = doc[1]
        application.logger.info('Imported an Image Document by the name of "' + doc['name'] +
                                f'" into project {project_id}!')
        new_docs.append(doc['_id'])


def _finish_import(new_docs, bulk_size, batch, has_worked, project_id, user_id):
    if bulk_size > 1:
        if batch:
            _execute_file_upload(batch)
            batch = ImgDocDAO().insert_docs(batch, generate_response=False)
            new_docs.extend(doc['_id'] for doc in batch)
            application.logger.info(
                f'Imported the last batch of {len(batch)} Image Documents into project {project_id}!')
            batch.clear()
        for id_and_flag in zip(new_docs, has_worked):
            if id_and_flag[1] is not None:
                batch.append(id_and_flag)
                if len(batch) >= bulk_size:
                    WorkHistoryDAO().add_bulk(batch, user_id, project_id)
                    batch.clear()
        if batch:
            WorkHistoryDAO().add_bulk(batch, user_id, project_id)
    ProjectDAO().add_idocs_to_project(project_id, new_docs)


def _import_json_dset(project_id, file, bulk_size):
    new_docs = []
    nums_annos = 0
    batch = has_worked = None
    if bulk_size > 1:
        use_bulk = True
        batch, has_worked = [], []
    else:
        use_bulk = False
    file_stream = file.stream
    line = file_stream.readline().decode('utf-8')
    assert len(line) == 2 and line[0] == '['
    user_id = UserDAO().get_current_user_id()
    img_dao = ImgDocDAO()
    label_dao = LabelDAO()
    label_names, categories, label_map = [], [], {}
    feat_obj_ids, feat_anno_ids, feat_concept_ids, feat_bboxs, pbboxs = [], [], [], [], []
    for line in file_stream:
        line = line.decode('utf-8')
        if line == ']':
            break
        # remove last 2 chars in a line to remove the comma after the document line and the newline char
        tail = 2 if line[-2] == ',' else 1
        doc = json.loads(line[:-tail])
        doc['projectId'] = project_id
        feats = []
        objects = doc['objects']
        for obj in objects:
            label = obj.pop('label')
            lid = label['_id']
            if lid in label_map:
                existing_label = label_map[lid]
                if existing_label is not None:
                    obj['labelId'] = existing_label['_id']
                    obj['label'] = existing_label
                else:
                    obj['labelId'] = lid
            else:
                existing_label = label_dao.find_by_name(label['name'], projection=("labelIdx", "nameTokens"))
                if existing_label is None:
                    label_names.append(label['name'])
                    categs = label['categories']
                    if not categs:
                        err_msg = "Provide at least one basic category for an object label!"
                        application.logger.error(err_msg)
                        abort(400, err_msg)
                    categories.append(categs)
                    obj['labelId'] = lid
                    label_map[lid] = None
                else:
                    obj['labelId'] = existing_label['_id']
                    obj['label'] = existing_label
                    label_map[lid] = existing_label
            bbox = None
            for anno in obj['annotations']:
                nums_annos += 1
                if 'visFeatures' in anno:
                    if bbox is None:
                        bbox = (obj['tlx'], obj['tly'], obj['brx'], obj['bry'])
                    feats.append((anno.pop('idxPath'), anno.pop('visFeatures'), bbox))
        # TODO: allow to have doc['annotations'] and doc['label'] without any objects => create one object that
        #  has a bbox over the entire image, then add the prepared annotations and label to it.
        if label_names:
            labels = label_dao.add_many(label_names, categories)
            # Prepare objects for ImgDoc insert
            new_label_idx = 0
            for obj in objects:
                if 'label' not in obj:
                    lid = obj['labelId']
                    label = label_map[lid]
                    if label is None:
                        label = labels[new_label_idx]
                        label_map[lid] = label
                        obj['labelId'] = label['_id']
                        obj['label'] = label
                        new_label_idx += 1
                    else:
                        obj['labelId'] = label['_id']
                        obj['label'] = label
            label_names.clear()
            categories.clear()
        doc = img_dao.add_from_json(doc, user_id, use_bulk)
        _add_to_batch(doc, new_docs, bulk_size, batch, has_worked, project_id)
        # Collect visual features data for final insert
        for idxs, fts, pbx in feats:
            i, j = idxs
            obj = doc['objects'][i]
            anno = obj['annotations'][j]
            concepts = anno['conceptIds']
            cids, bboxs = [], []
            for feat in fts:
                feat_concept = ObjectId(feat['conceptId'])
                if feat_concept in concepts:
                    cids.append(feat_concept)
                    bboxs.append(feat['bboxs'])
            if cids:
                feat_obj_ids.append(ObjectId(obj['_id']))
                feat_anno_ids.append(ObjectId(anno['_id']))
                feat_concept_ids.append(cids)
                feat_bboxs.append(bboxs)
                pbboxs.append(pbx)
    if new_docs or batch:
        _finish_import(new_docs, bulk_size, batch, has_worked, project_id, user_id)
    if feat_anno_ids:
        VisualFeatureDAO().add_many(feat_obj_ids, feat_anno_ids, feat_concept_ids, feat_bboxs, pbboxs)
    return len(new_docs), nums_annos


def _import_zipped_dset(project_id, file, bulk_size):
    # TODO: needs to be able to handle the most basic case of image + label + annotation tuple examples,
    #  but also objects (and visual features). The usual case should be a zip file that contains a folder structure
    #  that we define in the parameters.
    struct_preset = request.args.get('structure', '<labels>/<data>')
    img_path = request.args.get('imgPath', 'images')
    img_fsuffix = request.args.get('imgSuffix', '.jpg')
    anno_path = request.args.get('annoPath', 'text')
    anno_fsuffix = request.args.get('annoSuffix', '.txt')
    obj_path = request.args.get('objPath', None)
    dir_delim = request.args.get('dirdelim', '_')
    dir_prefix = request.args.get('dirprefix', '<int:3>.')
    dir_suffix = request.args.get('dirsuffix', None)
    fname_delim = request.args.get('fdelim', '_')
    fname_prefix = request.args.get('fprefix', None)
    fname_suffix = request.args.get('fsuffix', '_<int:6>')  # TODO: make option <len:7> to just remove the last 7 chars
    # allows input of some categories that describe the type of entities (input comma seperated strings)
    label_categories = request.args['categories']
    label_categories = label_categories.split(',')
    # TODO: allow to extract the categories from the files (e.g. from file names or their contents),
    #  if the dataset contains many types of entities

    new_docs = []
    nums_annos = 0
    batch = has_worked = None
    if bulk_size > 1:
        use_bulk = True
        batch, has_worked = [], []
    else:
        use_bulk = False
    user_id = UserDAO().get_current_user_id()
    img_dao = ImgDocDAO()
    label_dao = LabelDAO()
    with ZipFile(file) as myzip:
        file_list = myzip.namelist()
        idir_start = len(img_path) + 1
        fnames = defaultdict(list)
        for fname in file_list:
            if fname.startswith(img_path):
                dir_name = fname[idir_start:fname.find('/', idir_start)]
                cls_dir_start = idir_start + len(dir_name) + 1
                if len(fname) > cls_dir_start:
                    fname = fname[cls_dir_start:] if img_fsuffix is None else fname[cls_dir_start:-len(img_fsuffix)]
                    fnames[dir_name].append(fname)
        for dir_name, fnames in fnames.items():
            label_name = dir_name.replace(fname_delim, ' ')[4:]
            label = label_dao.find_or_add(label_name, label_categories, projection='_id')
            title = dir_name.replace(dir_delim[:7], ' ')
            for fname in fnames:
                full_fname = fname
                iloc = f"{img_path}/{dir_name}/{fname}"
                if img_fsuffix:
                    full_img_fname = full_fname + img_fsuffix
                    iloc = iloc + img_fsuffix
                aloc = f"{anno_path}/{dir_name}/{fname}"
                if anno_fsuffix:
                    aloc = aloc + anno_fsuffix
                with myzip.open(aloc) as annof:
                    annos = [anno.decode('utf-8')[:-1] for anno in annof]
                    with myzip.open(iloc) as imgf:
                        doc = img_dao.add_with_annos(title, full_img_fname, imgf.read(), annos,
                                                     label['_id'], user_id, project_id, use_bulk)
                        nums_annos += len(annos)
                        _add_to_batch(doc, new_docs, bulk_size, batch, has_worked, project_id)
    if new_docs or batch:
        _finish_import(new_docs, bulk_size, batch, has_worked, project_id, user_id)
    return len(new_docs), nums_annos


@application.route("/dataset/import/<project_id>", methods=["PUT"])
def dataset_import(project_id):
    try:
        project_id = ObjectId(project_id)
    except InvalidId:
        err_msg = "The Project ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)
    max_length = application.config['MAX_CONTENT_LENGTH']
    application.config['MAX_CONTENT_LENGTH'] = None
    bulk_size = request.args.get('bulkSize', 1000)
    try:
        if 'file' not in request.files:
            abort(400, 'No file part')
        file = request.files['file']
        if file.filename == '':
            abort(400, 'No selected file')
        file_suffix_idx = file.filename.rfind('.')
        data_format = file.filename[file_suffix_idx + 1:] if file_suffix_idx >= 0 else 'json'
        if data_format == 'json':
            nums_docs, nums_annos = _import_json_dset(project_id, file, bulk_size)
        elif data_format == 'zip':
            nums_docs, nums_annos = _import_zipped_dset(project_id, file, bulk_size)
        elif data_format == 'csv':
            nums_docs, nums_annos = 0, 0  # TODO
        else:
            raise ValueError('Unsupported data format!')
        application.logger.info(f"Images imported: {nums_docs} ; Annotations imported: {nums_annos}")
        return {"numInserted": nums_docs, "status": 200, 'model': 'ImgDoc'}
    finally:
        application.config['MAX_CONTENT_LENGTH'] = max_length
