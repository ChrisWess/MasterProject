from typing import Optional

from bson import ObjectId
from pydantic import Field, NonNegativeInt

from app.db.models.payloads.base_model import PayloadBaseModel


class LabelPayload(PayloadBaseModel):
    label_idx: Optional[NonNegativeInt] = Field(default=None, alias="labelIdx")
    name: Optional[str] = Field(default=None)
    name_tokens: Optional[list[str]] = Field(default=None, alias="nameTokens")
    categories: Optional[list[str]] = Field(default=None)

    class Config:
        _json_example = {
            "_id": ObjectId("65610d371e91b2dff82f93b8"),
            "labelIdx": 0,
            "name": "Fox",
            "nameTokens": ["fox"],
            "categories": ["animal"]
        }
        json_schema_extra = {"example": _json_example}
