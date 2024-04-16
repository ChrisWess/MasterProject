from threading import Thread

from app import application
from app.db.stats.daos.anno_concept_stats import ConceptTfIdfDAO
from app.db.stats.daos.anno_word_stats import CorpusTfIdfDAO
from app.db.stats.daos.project_progress import ProjectProgressDAO


@application.route('/stats/project/progress', methods=['GET'])
def project_progress():
    return ProjectProgressDAO().find_all_stats(generate_response=True)


@application.route('/stats/project/progress', methods=['POST'])
def update_progress():
    response = ProjectProgressDAO().update(generate_response=True)
    application.logger.info(f"Updated the Progress of {response['numUpdated']} Projects!")
    return response


def _trigger_updates():
    ConceptTfIdfDAO().update()
    CorpusTfIdfDAO().update()
    application.logger.info("Updated Tf-Idfs!")


@application.route('/stats/project/suggestions', methods=['PUT'])
def trigger_suggestion_update():
    # TODO: make sure that only one thread is running at a time
    thread = Thread(target=_trigger_updates)
    thread.start()
    return 'started'
