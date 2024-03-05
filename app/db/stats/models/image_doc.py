from datetime import datetime

from bson import ObjectId
from pydantic import Field, NonNegativeInt, NonNegativeFloat

from app.db.stats.models.base_stats import StatsBase


class ImageOverviewStats(StatsBase):
    avg_img_width: NonNegativeFloat = Field(alias="avgWidth")
    avg_img_height: NonNegativeFloat = Field(alias="avgHeight")
    avg_num_objs: NonNegativeFloat = Field(alias="avgObjs")
    avg_num_annos: NonNegativeFloat = Field(alias="avgAnnos")
    count: NonNegativeInt

    class Config:
        _json_example = {
            "_id": "images_overview",
            "isValid": False,
            "avgWidth": 0.0,
            "avgHeight": 0.0,
            "avgObjs": 0.0,
            "avgAnnos": 0.0,
            "count": 0,
            "updatedAt": datetime.now()
        }
        json_schema_extra = {"example": _json_example}


class ImagePrioStat(StatsBase):
    prio: float = Field(default=0.0, ge=0.0, le=1.0)

    class Config:
        _json_example = {
            "_id": ObjectId("6560e23ce1a3e3df0863b6d8"),
            "isValid": False,
            "prio": 0.0,
            "updatedAt": datetime.now()
        }
        json_schema_extra = {"example": _json_example}
