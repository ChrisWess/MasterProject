from app.db.stats.daos.base import BaseStatsDAO, cached, simple_stat
from app.db.stats.models.image_doc import ImageOverviewStats


class ImageStatsDAO(BaseStatsDAO):
    def __init__(self):
        super().__init__('images', ImageOverviewStats)

    @simple_stat
    def find_width_avg(self, field_name='avgImgWidth'):
        return {'$group': {'_id': None, field_name: {'$avg': '$width'}}}

    @simple_stat
    def find_height_avg(self, field_name='avgImgHeight'):
        return {'$group': {'_id': None, field_name: {'$avg': '$height'}}}

    @simple_stat
    def find_objs_avg(self, field_name='avgObjs'):
        return {'$group': {'_id': None, field_name: {'$avg': {'$size': '$objects'}}}}

    @simple_stat
    def find_annos_avg(self, field_name='avgAnnos'):
        return [
            {"$unwind": {"path": "$objects", "preserveNullAndEmptyArrays": True}},
            {"$unwind": {"path": "$objects.annotations", "preserveNullAndEmptyArrays": True}},
            {
                "$group": {
                    "_id": "$_id",
                    "annos": {"$push": "$objects.annotations"},
                }
            },
            {
                "$group": {
                    "_id": None,
                    field_name: {'$avg': {"$size": "$annos"}},
                }
            },
        ]

    @simple_stat
    def find_annos_avg_per_obj(self, field_name='avgAnnos'):
        return {'$group': {'_id': None, field_name: {'$avg': {'$size': '$objects.annotations'}}}}

    @simple_stat
    def count(self, field_name='count'):
        return {'$group': {'_id': None, field_name: {'$count': {}}}}

    @cached
    def overview(self):
        return ImageOverviewStats, {
            'avgWidth': self.find_width_avg,
            'avgHeight': self.find_height_avg,
            'avgObjs': self.find_objs_avg,
            'avgAnnos': self.find_annos_avg,
            'count': self.count,
        }
