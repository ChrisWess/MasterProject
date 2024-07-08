from io import BytesIO

from PIL import Image

from app import application
from app.autoxplain.infer import classify_object_images, identify_object_concepts, show_dset, \
    highlight_filter_activation_masks
from app.autoxplain.train import run_ccnn_training
from app.db.daos.image_doc_dao import ImgDocDAO
from app.db.daos.label_dao import LabelDAO


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


@application.route('/showTrainImages', methods=['GET'])
def show_images():
    show_dset()
    return 'Opened PIL images on local machine!'
