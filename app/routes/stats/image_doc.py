from app import application
from app.db.stats.daos.image_prios import PrioStatsDAO
from app.db.stats.daos.image_stats import ImageStatsDAO


@application.route('/stats/idoc', methods=['GET'])
def image_overview():
    return ImageStatsDAO().overview()


@application.route('/stats/idoc/prios', methods=['GET'])
def image_prios():
    return PrioStatsDAO().find_all_stats(generate_response=True)


@application.route('/stats/idoc/prios', methods=['POST'])
def update_prios():
    response = PrioStatsDAO().update(generate_response=True)
    application.logger.info(f"Updated the Priorities of {response['numUpdated']} Image Documents!")
    return response
