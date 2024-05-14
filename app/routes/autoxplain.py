from app import application
from app.autoxplain.train import run_ccnn_training


@application.route('/train', methods=['GET'])
def trigger_train_model():
    run_ccnn_training(5, 0.0001)
    return 'done'
