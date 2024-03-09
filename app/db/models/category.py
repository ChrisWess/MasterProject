from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints


class Category(BaseModel):
    id: Annotated[str, StringConstraints(min_length=2, max_length=30,
                                         to_lower=True, strip_whitespace=True)] = Field(alias="_id")
    tokens: list[Annotated[str, StringConstraints(min_length=2, max_length=30,
                                                  to_lower=True, strip_whitespace=True)]] = Field(default_factory=list)
    assigned_labels: list[int] = Field(alias="labelIdxRefs", default_factory=list)

    class Config:
        validate_assignment = True
        populate_by_name = True

    def to_dict(self):
        return self.model_dump(by_alias=True)

    def to_json(self):
        return self.model_dump_json(by_alias=True)
