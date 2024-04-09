from app import application
from app.db.stats.daos.label_stats import LabelStatsDAO


@application.route('/stats/label', methods=['GET'])
def label_overview():
    return LabelStatsDAO().overview()
