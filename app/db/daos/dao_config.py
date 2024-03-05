daos_path_prefix = "app.db.daos."

dao_module_class_dict = {
    "project_dao": 'ProjectDAO',
    "user_dao": 'UserDAO',
    "label_dao": 'LabelDAO',
    "object_dao": 'ObjectDAO',
    "annotation_dao": 'AnnotationDAO',
    "image_doc_dao": 'ImgDocDAO',
    "work_history_dao": 'WorkHistoryDAO',
    "concept_dao": 'ConceptDAO',
    "corpus_dao": 'CorpusDAO',
    'vis_feature_dao': 'VisualFeatureDAO',
}

collection_dao_module_dict = {
    "projects": 'project_dao',
    "users": 'user_dao',
    "labels": 'label_dao',
    "images": 'image_doc_dao',
    "history": 'work_history_dao',
    "concepts": 'concept_dao',
    "corpus": 'corpus_dao',
    "visfeatures": 'vis_feature_dao',
}
