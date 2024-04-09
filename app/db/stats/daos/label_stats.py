from app.db.stats.daos.base import BaseStatsDAO, cached, simple_stat
from app.db.stats.models.label import LabelOverviewStats


class LabelStatsDAO(BaseStatsDAO):
    def __init__(self):
        super().__init__('labels', LabelOverviewStats)

    @simple_stat
    def token_avg(self, field_name='avgTokens'):
        return {"$group": {"_id": None, field_name: {"$avg": {"$size": "$nameTokens"}}}}

    @simple_stat
    def category_avg(self, field_name='avgCategories'):
        return {"$group": {"_id": None, field_name: {"$avg": {"$size": "$categories"}}}}

    @simple_stat
    def count(self, field_name='count'):
        return {'$group': {'_id': None, field_name: {'$count': {}}}}

    @cached
    def overview(self):
        return LabelOverviewStats, {
            'avgTokens': self.token_avg,
            'avgCategories': self.category_avg,
            'count': self.count,
        }
