from typing import Optional

from bson import ObjectId
from pydantic import Field

from app.db.models.payloads.base_model import PayloadBaseModel


class WordPayload(PayloadBaseModel):
    index_val: Optional[int] = Field(default=None, alias="index")
    text: Optional[str] = Field(default=None)
    lemma: Optional[str] = Field(default=None)
    stem: Optional[str] = Field(default=None)
    noun_flag: Optional[bool] = Field(default=None, alias="nounFlag")
    proper: Optional[bool] = Field(default=None)

    class Config:
        _json_example = {
            "_id": ObjectId("65610d521e91b2dff82f93b9"),
            "index": 0,
            "text": "fur",
            "stem": "fur",
            "lemma": "fur",
            "nounFlag": True,
            "proper": False,
        }
        json_schema_extra = {"example": _json_example}
