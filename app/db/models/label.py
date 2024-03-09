from typing import Annotated

from bson import ObjectId
from pydantic import Field, StringConstraints, NonNegativeInt

from app.db.models.base_model import DataBaseModel

UNKNOWN = '<unknown>'


class Label(DataBaseModel):
    label_idx: NonNegativeInt = Field(alias="labelIdx")
    name: Annotated[str, StringConstraints(min_length=2, max_length=50, strip_whitespace=True)] = Field(default=UNKNOWN)
    name_tokens: list[str] = Field(default_factory=list, alias="nameTokens")
    token_idxs: list[NonNegativeInt] = Field(default_factory=list, alias="tokenRefs")
    categories: list[
        Annotated[str, StringConstraints(min_length=2, max_length=50, strip_whitespace=True, to_lower=True)]
    ] = Field(default_factory=list)
    lower: str = Field(init_var=False)

    # TODO: maybe add ground-truth feature phrases (list of adjs + noun) that best describe the class/entity
    #  or most commonly associated concepts/words with this class (probably rather as stats)

    def __init__(self, **data):
        data['lower'] = data['name'].lower()
        super().__init__(**data)

    class Config:
        _json_example = {
            "_id": ObjectId("65610d371e91b2dff82f93b8"),
            "labelIdx": 0,
            "name": "Fox",
            "lower": "fox",
            "nameTokens": ["fox"],
            "tokenRefs": [0],
            "categories": ["animal"]
        }
        json_schema_extra = {"example": _json_example}
