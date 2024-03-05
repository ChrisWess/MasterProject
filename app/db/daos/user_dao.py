from json import loads

from bson.objectid import ObjectId
from flask import session
from flask_login import login_user, logout_user
from pymongo import ASCENDING

from app import application, config, login_manager
from app.db.daos.base import BaseDAO
from app.db.models.payloads.user import UserPayload
from app.db.models.user import User


class UserDAO(BaseDAO):
    __slots__ = "root_admin"

    def __init__(self):
        # Initialize mongodb collection of users
        super().__init__("users", User, UserPayload)
        self.create_index('email_index', ('email', ASCENDING), unique=True)
        from app import ROOT_ADMIN
        from app.db.stats.daos.work_stats import WorkHistoryStatsDAO
        self.root_admin = ROOT_ADMIN
        self.stat_references = (WorkHistoryStatsDAO,)

    def load_user_model(self, user_id):
        query = self.add_query("_id", user_id)
        user = self.collection.find_one(query)
        self.clear_query()
        if user is not None:
            return self.model(**user)

    @staticmethod
    @login_manager.user_loader
    def load_user(user_id):
        return UserDAO().load_user_model(ObjectId(user_id))

    @staticmethod
    def logout_user():
        application.logger.info('User logged out')
        logout_user()
        session['logged_in'] = False

    @staticmethod
    def is_logged_in_in_session():
        return session.get('logged_in', default=False)

    def validate_login(self, email, usr_entered):
        # Validates a user login. Returns user record or None
        # Get Fields Username & Password
        # Client Side Login & Validation handled by wtforms in register class
        query = self.add_query("email", email)
        user = self.collection.find_one(query)
        self._query_matcher.clear()
        if user is not None:
            user = self.model(**user)
            if user.check_password(usr_entered):
                application.logger.info('Password Matched! Logging in user ' + email)
                session['logged_in'] = login_user(user)
                session['userid'] = str(user.id)
                session['username'] = email

                return user
            else:
                raise ValueError('Incorrect Credentials')
        else:
            raise ValueError('Email not registered')

    def get_current_user_id(self):
        # FIXME: Workaround (session not available with react dev server)
        #   Could be fixed with setting authorization & session in headers (e.g. JWT)
        if config.DEBUG:
            return self.find_by_email(self.root_admin['email'], projection='_id')['_id']
        else:
            return ObjectId(session['userid'])

    def get_current_user(self, projection=None, generate_response=False):
        return self.find_by_id(self.get_current_user_id(), projection=projection,
                               generate_response=generate_response)

    def find_by_email(self, email, projection=None, generate_response=False, db_session=None):
        """
        Find User with given email
        :param email: String email to find
        :param projection:
        :param generate_response:
        :param db_session:
        :return: User object if found, None otherwise
        """
        return self.simple_match("email", email, projection, generate_response, db_session, find_many=False)

    def delete_by_email(self, email, generate_response=False, db_session=None):
        return self.simple_delete('email', email, generate_response, db_session, delete_many=False)

    def add(self, name, email, password, generate_response=False, db_session=None):
        # creates a new user in the users collection
        user = User(name=name, email=email, password=password)
        # TODO: is this even necessary? The index is defined as unique anyway!
        email_exists = self.find_by_email(email, projection='_id', db_session=db_session) is not None
        if email_exists:
            raise ValueError(f"User with email {email} does already exist!")
        return self.insert_doc(user, generate_response=generate_response, db_session=db_session)

    def _prepare_doc_import(self, doc):
        doc = loads(doc)
        doc['hashedPass'] = doc['hashedPass'].encode('utf-8')
        return self.model(**doc).model_dump(by_alias=True)
