from datetime import datetime

from pydantic import Field, NonNegativeInt, NonNegativeFloat

from app.db.stats.models.base_stats import StatsBase


class LabelOverviewStats(StatsBase):
    avg_num_tokens: NonNegativeFloat = Field(alias="avgTokens")
    avg_num_categories: NonNegativeFloat = Field(alias="avgCategories")
    count: NonNegativeInt

    class Config:
        _json_example = {
            "_id": "labels_overview",
            "isValid": False,
            "avgTokens": 0.0,
            "avgCategories": 0.0,
            "count": 0,
            "updatedAt": datetime.now()
        }
        json_schema_extra = {"example": _json_example}
