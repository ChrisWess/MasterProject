from io import BytesIO

from PIL import Image
from bson import ObjectId
from bson.errors import InvalidId
from flask import abort

from app import application, fs
from app.autoxplain.infer import classify_object_images, identify_object_concepts, show_dset, \
    highlight_filter_activation_masks, generate_full_annotation_data
from app.autoxplain.model import oxp_model_data_dir, dset_args
from app.autoxplain.train import run_ccnn_training
from app.db.daos.annotation_dao import AnnotationDAO
from app.db.daos.corpus_dao import CorpusDAO
from app.db.daos.image_doc_dao import ImgDocDAO
from app.db.daos.label_dao import LabelDAO
from app.db.daos.user_dao import UserDAO
from app.db.daos.vis_feature_dao import VisualFeatureDAO
from app.db.models.object import DetectedObject
from app.preproc.object import detect_objects
from app.routes.vis_feature import validate_visual_feature


@application.route('/train', methods=['GET'])
def trigger_train_model():
    run_ccnn_training()
    return 'Training finished successfully!'


@application.route('/testClassify', methods=['GET'])
def classify_images():
    sample_size = 5
    img_docs = ImgDocDAO().get_img_sample(sample_size, projection=('image', 'objects.labelId'))
    imgs = [Image.open(BytesIO(idoc['image'])) for idoc in img_docs]
    clsfy_result = classify_object_images(imgs)
    accuracy = 0
    for idoc, cls in zip(img_docs, clsfy_result):
        label = idoc['objects'][0]['labelId']
        label = LabelDAO().find_by_id(label, projection='labelIdx')['labelIdx']
        if label == cls:
            accuracy += 1
    return f"Classified {accuracy} / {sample_size} images correctly! Accuracy: {accuracy / sample_size}"


@application.route('/testConceptIdent', methods=['GET'])
def identify_imgobj_concepts():
    sample_size = 3
    img_docs = ImgDocDAO().get_img_sample(sample_size, projection=('objects._id', 'fname'))
    imgs = [idoc['objects'][0]['_id'] for idoc in img_docs]
    concept_data = identify_object_concepts(imgs)
    result = [{'concepts': cd[1],
               'contributions': [conf * 100 for conf in cd[2]],
               'imgId': str(idoc['_id']),
               'fname': idoc['fname']} for cd, idoc in zip(concept_data, img_docs)]
    return result


@application.route('/testConceptMasks', methods=['GET'])
def show_concept_masks():
    sample_size = 20
    img_docs = ImgDocDAO().get_img_sample(sample_size, projection=('objects._id', 'fname'))
    img_ids = [idoc['objects'][0]['_id'] for idoc in img_docs]
    concept_data = identify_object_concepts(img_ids)
    highlight_filter_activation_masks(img_ids, concept_data)
    return [cd[1] for cd in concept_data]


def get_label_id_by_ccnn_idx(cls_idx):
    fpath = oxp_model_data_dir / dset_args[0]
    with fpath.open() as f:
        for idx, line in enumerate(f):
            if cls_idx == idx:
                return ObjectId(line.strip())


@application.route('/idocAutoAnno/<doc_id>', methods=['PUT'])
def autoxplain_image(doc_id=None):
    try:
        doc_id = ObjectId(doc_id)
        idoc = ImgDocDAO().find_by_id_complete(doc_id, projection=('image', 'objects'))
        if idoc is None:
            err_msg = f"No image with ID {str(doc_id)} could be found!"
            application.logger.error(err_msg)
            abort(404, err_msg)
        # TODO: What to do with explanations, if more than one object exists in image? How to correctly
        #  reassign explanations to corresponding object? Perhaps define a specified order relation
        #  for objects e.g. order by x-coordinate (and y coord)
        new_obj = idoc['objects'][0]  # old obj becomes new obj container
        old_obj_id = new_obj['_id']
        annos = new_obj['annotations']
        for i, anno in enumerate(annos):
            annos[i] = anno['text']
        img = Image.open(BytesIO(fs.get(idoc['image']).read()))
        try:
            bbox = next(detect_objects(img))[0]
        except StopIteration:
            return abort(400, "No objects could be detected in the image!")
        crop = img.crop(bbox)
        cls_idx, concept_token_lists, bboxs = generate_full_annotation_data(crop)
        for i, bb in enumerate(bboxs):
            bboxs[i] = list(bb)
        concept_token_sets = []
        for concept_tokens in concept_token_lists:
            concept_token_sets.append(set(concept_tokens))
        label_id = get_label_id_by_ccnn_idx(cls_idx)
        if label_id is None:
            return abort(400, "Error in remote file (Class Index Mapping File)!")
        categories = LabelDAO().find_by_id(label_id, projection='categories')
        if categories is None:
            return abort(400, "Label ID in class index mapping file is invalid!")
        categories = categories['categories']
        new_obj['labelId'] = label_id
        new_obj['tlx'] = bbox[0]
        new_obj['tly'] = bbox[1]
        new_obj['brx'] = bbox[2]
        new_obj['bry'] = bbox[3]
        new_obj['annotations'] = AnnotationDAO().prepare_annotations(annos, label_id, skip_val_errors=True)
        has_new_concept = False
        for tokens in concept_token_lists:
            end_idx = len(tokens) - 1
            for i in range(end_idx):
                is_new, doc = CorpusDAO().find_doc_or_add(tokens[i], False)
                if is_new:
                    has_new_concept = True
                tokens[i] = doc["index"]
            is_new, doc = CorpusDAO().find_doc_or_add(tokens[end_idx], True)
            if is_new:
                has_new_concept = True
            tokens[end_idx] = doc["index"]
        user_id = UserDAO().get_current_user_id()
        generated_anno = AnnotationDAO().from_concepts(concept_token_lists, categories[0],
                                                       user_id, return_entity=True)
        # add new annotation with all detected concepts
        if has_new_concept:
            # TODO: create an equality relation for annotations to check easily if annotation with
            #  the exact same concepts is already present.
            pass
        else:
            new_obj['annotations'].append(generated_anno)
        new_objs = [DetectedObject(**new_obj).to_dict()]
        new_obj = new_objs[0]
        new_obj['_id'] = ObjectId()
        old_obj_ids = [old_obj_id]
        result = ImgDocDAO().replace_objects(doc_id, new_objs, old_obj_ids, generate_response=True)
        curr_anno_concept_token_set = set()
        for anno in new_obj['annotations']:
            anno_id = anno['_id']
            num_concepts = len(anno['conceptIds'])
            concept_idx = 0
            for token, mask_id in zip(anno['tokens'], anno["conceptMask"]):
                if concept_idx == mask_id:
                    curr_anno_concept_token_set.add(token)
                elif curr_anno_concept_token_set:
                    concept_id = anno['conceptIds'][concept_idx]
                    for i, token_set in enumerate(concept_token_sets):
                        if token_set.issubset(curr_anno_concept_token_set):
                            bbs = [bboxs[i]]
                            try:
                                obj_id = validate_visual_feature(anno_id, concept_id, bbs)
                                VisualFeatureDAO().add(obj_id, anno_id, concept_id, bbs)
                            except ValueError as e:
                                err_msg = (f"Could not validate visual feature with Bounding Box defintions {bbs} of "
                                           f"annotation {0} with concept ID {0}!\nRoot Error: {e}")
                                application.logger.error(err_msg)
                    curr_anno_concept_token_set.clear()
                    concept_idx += 1
                    if concept_idx >= num_concepts:
                        break
        return result
    except InvalidId:
        err_msg = "The Image Document ID you provided is not a valid ID!"
        application.logger.error(err_msg)
        abort(404, err_msg)


@application.route('/showTrainImages', methods=['GET'])
def show_images():
    show_dset()
    return 'Opened PIL images on local machine!'
