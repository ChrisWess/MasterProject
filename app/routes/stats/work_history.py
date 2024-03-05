from app import application
from app.db.stats.daos.work_stats import WorkHistoryStatsDAO


@application.route('/stats/workEntry', methods=['GET'])
def work_overview():
    return WorkHistoryStatsDAO().overview()
