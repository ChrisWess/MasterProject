from app.db.stats.daos.base import BaseStatsDAO, cached, simple_stat
from app.db.stats.models.work_entry import WorkHistoryStats


class WorkHistoryStatsDAO(BaseStatsDAO):
    def __init__(self):
        super().__init__('history', WorkHistoryStats)

    @simple_stat
    def find_workers_avg(self, field_name='avgWorkers'):
        return [
            {
                "$group": {
                    "_id": "$docId",
                    "numWorkers": {"$sum": 1},
                }
            },
            {
                "$group": {
                    "_id": None,
                    field_name: {"$avg": "$numWorkers"},
                }
            },
        ]

    @simple_stat
    def find_workers_count(self, field_name='totalWorkers'):
        return [
            {
                "$group": {
                    "_id": "$workerId",
                }
            },
            {"$count": field_name}
        ]

    @cached
    def overview(self):
        return WorkHistoryStats, {
            'avgWorkers': self.find_workers_avg,
            'totalWorkers': self.find_workers_count,
        }
