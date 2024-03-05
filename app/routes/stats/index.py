from importlib import import_module

from app import application, mdb
from app.db.stats.daos.dao_config import collection_stat_dict, stat_module_class_dict


@application.route('/stats', methods=['GET'])
def cached_stats():
    return list(mdb.stats.find())


@application.route('/stats/summary', methods=['GET'])
def stats_summary():
    stats = {}
    module_root = 'app.db.stats.daos.'
    for coll_key, module_name in collection_stat_dict.items():
        data = []
        stats[coll_key] = data
        module = import_module(module_root + module_name)
        curr_dao = getattr(module, stat_module_class_dict[module_name])()
        for doc in curr_dao.find_all():
            data.append(doc)

    return stats
