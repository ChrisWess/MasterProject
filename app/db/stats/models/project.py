from datetime import datetime

from bson import ObjectId
from pydantic import Field

from app.db.stats.models.base_stats import StatsBase


class ProjectProgressStat(StatsBase):
    count: int = Field(alias='numDocs', default=0)
    total_prio: float = Field(alias='totalPrio', default=0.)
    progress: float = Field(default=0.0, ge=0.0, le=1.0)

    class Config:
        _json_example = {
            "_id": ObjectId("657c96f7bbcd24ecad0d0a10"),
            "isValid": False,
            "numDocs": 1,
            "totalPrio": 0.0,
            "progress": 0.0,
            "updatedAt": datetime.now()
        }
        json_schema_extra = {"example": _json_example}
