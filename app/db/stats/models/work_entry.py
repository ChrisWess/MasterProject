from datetime import datetime

from pydantic import Field

from app.db.stats.models.base_stats import StatsBase


class WorkHistoryStats(StatsBase):
    avg_workers: float = Field(ge=0.0, alias="avgWorkers")
    total_num_workers: float = Field(ge=0.0, alias="totalWorkers")

    class Config:
        _json_example = {
            "_id": "work-history",
            "isValid": False,
            "avgWorkers": 0.0,
            "totalWorkers": 0,
            "updatedAt": datetime.now()
        }
        json_schema_extra = {"example": _json_example}
