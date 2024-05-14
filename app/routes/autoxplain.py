from app import application
from app.autoxplain.train import test_classify


@application.route('/train', methods=['GET'])
def trigger_train_model():
    test_classify(5, 0.0001)
    return 'done'
