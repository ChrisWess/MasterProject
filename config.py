from pathlib import Path

from environs import Env

# Project base dir
basedir = Path(__file__).absolute()
env = Env()
PATH_PREFIX = env('PATH_PREFIX', env('OXP_PATH_PREFIX', None))
if PATH_PREFIX:
    env = env.prefixed(PATH_PREFIX)


# Common configurations
class Common:
    DEBUG: bool = True
    env: Env = env
    PATH_PREFIX: str | None = PATH_PREFIX
    HOST: str = env.str('SERVER_HOST', 'localhost')
    PORT: int = env.int('SERVER_PORT', 5000)
    WTF_CSRF_ENABLED: bool = True
    DB_NAME: str = "xplaindb"

    MAX_CONTENT_LENGTH: int = 64_000_000  # 64 MB

    UNAUTHORIZED_MESSAGE: str = "You don't have authorization to perform this action."
    ROOT_ADMIN = None
    ROOT_ADMIN_EMAIL: str = env.str('ROOT_ADMIN_EMAIL', env.str('ROOT_ADMIN_MAIL', ""))
    NUM_DAO_WORKERS: int = 5
    NUM_THUMBNAILS_PER_PAGE = 50
    MAX_PROJECT_DOCS = 100000  # TODO: limit a project

    # Enter a secret key
    SECRET_KEY = 'my-secret-key'

    SWAGGER_URL = '/swagger-ui'
    API_URL = '/swagger'

    @classmethod
    def load_admin_data(cls) -> None:
        user_info = env('ROOT_ADMIN', None)
        if user_info:
            fformat = split = None
            format_prefix = 'format:'
            if user_info.startswith(format_prefix):
                split = user_info.split('\n')
                fformat = split.pop(0)[len(format_prefix):].lower()
            if fformat:
                if fformat == 'json':
                    import json
                    cls.ROOT_ADMIN = json.loads(split[0])
                elif fformat == 'csv':
                    from app.db.util import load_csv_user
                    cls.ROOT_ADMIN = load_csv_user(split)
                else:
                    # TODO: load "fformat" with pandas or other (better) lib
                    raise NotImplementedError(f'File format {fformat} is not supported!')
            else:
                try:
                    import json
                    cls.ROOT_ADMIN = json.loads(user_info)
                except:
                    try:
                        from app.db.util import load_csv_user
                        cls.ROOT_ADMIN = load_csv_user(user_info)
                    except:
                        pass


# Debug specific configurations
class Debug(Common):
    WORKSPACE_URL: str = "http://localhost:3000/dashboard"
    DEV_SERVER_PROCESSES = env.int('SERVER_PROCESSES', 0)  # use threading by default
    MONGODB_DATABASE_URI: str = ("mongodb://" + env.str('DB_HOST', 'localhost') + ':' +
                                 str(env.int('DB_PORT', 27017)) + "/" + Common.DB_NAME)  # Your local database name

    @classmethod
    def load_admin_data(cls) -> None:
        Common.load_admin_data()
        if not cls.ROOT_ADMIN_EMAIL:
            if cls.ROOT_ADMIN and 'email' in cls.ROOT_ADMIN:
                cls.ROOT_ADMIN_EMAIL = cls.ROOT_ADMIN['email']
            else:
                cls.ROOT_ADMIN_EMAIL = "demo@mail.com"
        if cls.ROOT_ADMIN:
            cls.ROOT_ADMIN['email'] = cls.ROOT_ADMIN_EMAIL


# Production specific configurations
class Production(Common):
    DEBUG: bool = False
    # Database configuration
    WORKSPACE_URL: str = f"{Common.HOST}:{Common.PORT}/"  # FIXME: when going live
    MAX_CONTENT_LENGTH: int = 16_000_000
    MONGODB_DATABASE_URI: str = ('mongodb://' + env.str('DB_USER', '') + ':' + env.str('DB_PASS', '') + '@' +
                                 env.str('DB_HOST', '') + '/' + env.str('DB_SCHEMA', ''))

    @classmethod
    def load_admin_data(cls) -> None:
        user_pass = env('ROOT_PASS', None)  # Credentials must be specified to use a root user in prod
        if user_pass:
            Common.load_admin_data()
            if cls.ROOT_ADMIN is not None:
                cls.ROOT_ADMIN['password'] = user_pass
        if cls.ROOT_ADMIN_EMAIL:
            if cls.ROOT_ADMIN is None:
                cls.ROOT_ADMIN = {'email': cls.ROOT_ADMIN_EMAIL, 'password': user_pass} if user_pass else None
            else:
                cls.ROOT_ADMIN['email'] = cls.ROOT_ADMIN_EMAIL
        elif cls.ROOT_ADMIN and 'email' in cls.ROOT_ADMIN:
            cls.ROOT_ADMIN_EMAIL = cls.ROOT_ADMIN['email']
        if cls.ROOT_ADMIN_EMAIL:
            cls.UNAUTHORIZED_MESSAGE += f" Contact {cls.ROOT_ADMIN_EMAIL} to request privileges!"
            if 'password' not in cls.ROOT_ADMIN:
                cls.ROOT_ADMIN = None
        else:
            cls.ROOT_ADMIN = None
