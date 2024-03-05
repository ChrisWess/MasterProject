import bisect
from base64 import b64encode
from functools import wraps
from random import randrange
from warnings import warn

from app import application


def deprecated(reason):
    def decorator(func):
        fmt = "Call to deprecated function {name} ({reason})."

        @wraps(func)
        def new_func(*args, **kwargs):
            warn_msg = fmt.format(name=func.__name__, reason=reason)
            warn(warn_msg, category=DeprecationWarning, stacklevel=2)
            application.logger.warning(warn_msg)
            return func(*args, **kwargs)

        return new_func

    return decorator


def encode_as_base64(byte_str):
    return b64encode(byte_str).decode('latin1')


def load_csv_user(rows, limit=1):
    if not rows:
        return None
    fields = None
    if type(rows) is str:
        rows = rows.split('\n')
    if isinstance(rows, (list, tuple)):
        if len(rows) > limit:
            rows = '\n'.join(rows[i] for i in range(limit + 1))
        else:
            rows = rows[0]
            fields = ["name", "email", 'hashedPass', "role", "active"]
    else:
        raise ValueError(f'Unsupported input type for CSV rows data "{type(rows)}"!')
    from csv import DictReader
    user_line = DictReader(rows, fieldnames=fields)
    return next(user_line)


def generate_random_color_hex():
    return f"#{randrange(0x1000000):06x}"


class NoPasswordFoundException(Exception):
    def __int__(self, message="There is no password attached to this User entity!"):
        self.message = message
        super().__init__(self.message)


class SortedList(list):
    def insert(self, item):
        # Find the index where the item should be inserted
        index = bisect.bisect_left(self, item)
        # Insert the item at the calculated index
        super().insert(index, item)
