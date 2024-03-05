from app import application
from app.db.stats.daos.project_progress import ProjectProgressDAO


@application.route('/stats/project/progress', methods=['GET'])
def project_progress():
    return ProjectProgressDAO().find_all_stats(generate_response=True)


@application.route('/stats/project/progress', methods=['POST'])
def update_progress():
    response = ProjectProgressDAO().update(generate_response=True)
    application.logger.info(f"Updated the Progress of {response['numUpdated']} Projects!")
    return response
