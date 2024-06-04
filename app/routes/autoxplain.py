from io import BytesIO

from PIL import Image

from app import application
from app.autoxplain.infer import classify_object_images, identify_object_concepts
from app.autoxplain.train import run_ccnn_training
from app.db.daos.image_doc_dao import ImgDocDAO
from app.db.daos.label_dao import LabelDAO


@application.route('/train', methods=['GET'])
def trigger_train_model():
    run_ccnn_training()
    return 'done'


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
    img_docs = ImgDocDAO().get_img_sample(sample_size, projection=('image', 'fname', 'objects.labelId'))
    imgs = [Image.open(BytesIO(idoc['image'])) for idoc in img_docs]
    concept_data = identify_object_concepts(imgs)
    result = [{'concepts': cd[1],
               'imgId': str(idoc['_id']),
               'fname': idoc['fname']} for cd, idoc in zip(concept_data, img_docs)]
    return result
