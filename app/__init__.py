import os
from importlib.metadata import version

from apispec import APISpec
from apispec_pydantic_plugin import PydanticPlugin
from apispec_webframeworks.flask import FlaskPlugin
from flask import Flask
from flask_login import LoginManager
from flask_pymongo import PyMongo
from flask_swagger_ui import get_swaggerui_blueprint
from gridfs import GridFS

import config

# Flask application
application = Flask(__name__)
flask_version = version("flask")

from flask_cors import CORS

CORS(application, supports_credentials=True)

# NOTE: install dependencies with "pip install -r requirements.txt"
#   => use "pip freeze > requirements.txt" to overwrite list of dependencies with new pipenv modules
spec = APISpec(
    title='objexplain-swagger-doc',
    version='1.0.0',
    openapi_version='3.0.2',
    plugins=[FlaskPlugin(), PydanticPlugin()]
)

ALLOWED_FILE_EXTS = {'png', 'webp', 'jpg', 'jpeg', 'gif'}

# Set app config
if 'PRODUCTION' in os.environ:
    config = config.Production
    config.load_admin_data()
    application.config.from_object('config.Production')
else:
    config = config.Debug
    config.load_admin_data()
    application.config.from_object('config.Debug')
    print(f'Flask {flask_version} App is running in debug mode.')
application.config["MONGO_URI"] = config.MONGODB_DATABASE_URI

# Swagger UI route
swaggerui_blueprint = get_swaggerui_blueprint(
    config.SWAGGER_URL,
    config.API_URL,
    config={
        'app_name': "ObjeXplain"
    }
)
application.register_blueprint(swaggerui_blueprint, url_prefix=config.SWAGGER_URL)

# MongoDB database
client = PyMongo(application, connect=True, serverSelectionTimeoutMS=5000)  # username='username', password='password'
mdb = client.db
fs = GridFS(mdb)  # the GridFS file system for file handling (e.g. images)
print("Available database collections:", mdb.list_collection_names())

# Login manager settings
login_manager = LoginManager()
login_manager.init_app(application)
login_manager.login_view = "login"  # define login_view: tell Flask the URL of the landing that we are dealing with

# Include models and routes
from app.db import models
from app import routes


def _get_demo_user():
    demo_str = "demo"
    user_role = models.user.UserRole.ADMIN
    return {"name": demo_str, "email": config.ROOT_ADMIN_EMAIL,
            "password": demo_str + demo_str, "role": user_role,
            "color": "lightgreen", "active": True}


def _setup_root_user(usersdb, user_data):
    # Check or set up root user
    if 'role' not in user_data:
        user_data['role'] = 1
    if 'name' not in user_data:
        user_data['name'] = 'root_admin'
    password = user_data['password']
    user_model = models.user.User
    user = user_model(**user_data)
    user_data = user.model_dump(exclude_unset=True, by_alias=True)
    root_user = usersdb.find_one({"email": user_data['email']})
    if root_user is None:
        result = usersdb.insert_one(user_data)
        user_data = user.postprocess_insert_response(user_data, result.inserted_id)
        application.logger.info("Root Admin inserted: " + str(user_data['_id']))
    else:
        user_id = root_user['_id']
        application.logger.info("Root Admin exists with ID: " + str(user_id))
        recover_vals = {}
        root_user = user_model(**root_user)
        for field, val in root_user.model_dump(exclude_unset=True, by_alias=True).items():
            if field in user.model_fields_set:
                desired = user_data[field]
                if desired is not None and desired != val:
                    recover_vals[field] = desired
        if not root_user.check_password(password):
            recover_vals['hashedPass'] = user_model.hash_password(password)
        if recover_vals:
            usersdb.update_one({'_id': user_id}, {'$set': recover_vals})
            application.logger.info("Curated fields for Root Admin: " + list(recover_vals).__repr__())
    return user_data


ROOT_ADMIN = None
if config.ROOT_ADMIN:
    ROOT_ADMIN = config.ROOT_ADMIN
elif config.DEBUG:
    ROOT_ADMIN = _get_demo_user()
if ROOT_ADMIN:
    ROOT_ADMIN = _setup_root_user(mdb.users, ROOT_ADMIN)
