from enum import Enum
from typing import Optional, Annotated

import bcrypt
from bson import ObjectId
from pydantic import Field, EmailStr, StringConstraints, SecretStr

from app.db.models.base_model import DataBaseModel
from app.db.util import NoPasswordFoundException, generate_random_color_hex


class UserRole(Enum):
    ADMIN = 0
    CURATOR = 1
    ANNOTATOR = 2


class User(DataBaseModel):
    name: Optional[Annotated[str, StringConstraints(min_length=1, max_length=50, strip_whitespace=True)]] = None
    email: EmailStr
    password: Optional[Annotated[SecretStr, StringConstraints(
        min_length=7, max_length=30)]] = Field(default=None, exclude=True)
    hashed_pass: Optional[bytes] = Field(default=None, alias="hashedPass")
    role: UserRole = UserRole.ANNOTATOR
    color: str = Field(default_factory=generate_random_color_hex)
    active: bool = True

    def __init__(self, **data):
        if 'role' in data:
            data['role'] = UserRole(data['role'])
        if 'password' in data:
            data['hashedPass'] = self.hash_password(data['password'])
        elif 'hashedPass' not in data:
            raise ValueError("User instance must be able to determine the user's credentials!")
        super().__init__(**data)

    @staticmethod
    def hash_password(password, gen_salt=True):
        return bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt() if gen_salt else b'')

    class Config:
        use_enum_values = True  # to serializer role-enum as its value
        json_exclude = 'hashed_pass'
        _json_example = {
            "_id": ObjectId("6560badba00004fb3359631f"),
            "name": "Max Mustermann",
            "email": "max.mustermann@email.de",
            "hashedPass": b"<hidden>",
            "role": 1,
            "color": "#3a7b25",
            "active": True
        }
        json_schema_extra = {"example": _json_example}

    def __eq__(self, other):
        if isinstance(other, User):
            return self.id == other.id
        return NotImplemented

    def __ne__(self, other):
        equal = self.__eq__(other)
        if equal is NotImplemented:
            return NotImplemented
        return not equal

    @classmethod
    def postprocess_insert_response(cls, model_dict, db_insert):
        model_dict.pop("hashedPass", None)
        return DataBaseModel.postprocess_insert_response(model_dict, db_insert)

    def to_json(self):
        return self.model_dump_json(exclude=self.Config.json_exclude, by_alias=True)

    def check_password(self, checkpass):
        if not self.hashed_pass:
            raise NoPasswordFoundException
        # Get stored hashed and salted password => compare password with hashed password
        return bcrypt.checkpw(checkpass.encode('utf-8'), self.hashed_pass)

    def get_id(self):
        return str(self.id)

    @property
    def is_active(self):
        return self.active

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return True
