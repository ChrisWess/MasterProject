from datetime import datetime
from typing import Dict, Any

from bson import ObjectId
from pydantic import Field, NonNegativeInt

from app.db.models.payloads.base_model import PyObjectId
from app.db.stats.models.base_stats import StatsBase


class ConceptStats(StatsBase):
    concept_id: PyObjectId = Field(alias="conceptId", default=None)
    # TODO: save tf - idfs
    count: NonNegativeInt = 1
    class_counts: Dict[Any, Any] = Field(default=None, alias="classCounts")  # occurrence per class

    class Config:
        _json_example = {
            "_id": "concepts_indiv_stats",
            "isValid": False,
            "conceptId": ObjectId("65610d601e91b2dff82f93ba"),
            "count": 1,
            "classCounts": {"labelId": ObjectId("65610d371e91b2dff82f93b8"), "count": 1},
            "updatedAt": datetime.now()
        }
        json_schema_extra = {"example": _json_example}
