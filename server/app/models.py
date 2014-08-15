#pylint: disable=no-member

"""Data models."""

import datetime

from flask import Blueprint
from app import constants

MODEL_BLUEPRINT = Blueprint('models', __name__)

from app import app
from app.needs import Need, NeedException
from flask import json
from flask.json import JSONEncoder as old_json

from google.appengine.ext import db, ndb

BadValueError = db.BadValueError


class JSONEncoder(old_json):
    """
    Wrapper class to try calling an object's to_dict() method. This allows
    us to JSONify objects coming from the ORM. Also handles dates & datetimes.
    """

    def default(self, obj): #pylint: disable=E0202
        if isinstance(obj, ndb.Key):
            return obj.id()
        elif isinstance(obj, datetime.datetime):
            return str(obj)
        if isinstance(obj, ndb.Model):
            return obj.to_json()
        return super(JSONEncoder, self).default(obj)


app.json_encoder = JSONEncoder


class Base(ndb.Model):
    """Shared utilities."""

    @classmethod
    def from_dict(cls, values):
        """Creates an instance from the given values."""
        inst = cls()
        inst.populate(**values) #pylint: disable=star-args
        return inst

    def to_json(self):
        """Converts this model to a json dictionary."""
        result = self.to_dict()
        for key, value in result.items():
            try:
                new_value = app.json_encoder().default(value)
                result[key] = new_value
            except TypeError:
                pass
        return result


class User(Base):
    """Users."""
    email = ndb.StringProperty() # Must be associated with some OAuth login.
    login = ndb.StringProperty() # TODO(denero) Legacy of glookup system
    role = ndb.StringProperty(default=constants.STUDENT_ROLE)
    first_name = ndb.StringProperty()
    last_name = ndb.StringProperty()
    #TODO(martinis) figure out how to actually use this data
    courses = ndb.KeyProperty('Course', repeated=True)

    def __repr__(self):
        return '<User %r>' % self.email

    @property
    def is_admin(self):
        return self.role is not constants.STUDENT_ROLE

    @classmethod
    def from_dict(cls, values):
        """Creates an instance from the given values."""
        if 'email' not in values:
            raise ValueError("Need to specify an email")
        inst = cls(key=ndb.Key('User', values['email']))
        inst.populate(**values) #pylint: disable=star-args
        return inst

    @classmethod
    def get_or_insert(cls, email, **kwargs):
        assert not isinstance(id, int), "Only string keys allowed for users"
        kwargs['email'] = email
        return super(cls, User).get_or_insert(email, **kwargs)

    @classmethod
    def get_by_id(cls, id, **kwargs):
        assert not isinstance(id, int), "Only string keys allowed for users"
        return super(cls, User).get_by_id(id, **kwargs)

    @property
    def logged_in(self):
        return True

    @staticmethod
    def must_satisfy_static(user, need):
        if not user.logged_in:
            raise NeedException(need)

    def must_satisfy(self, user, need):
        action, key = need.items
        if action == "get":
            if not user.is_admin or self.key == key:
                raise NeedException(need)

class AnonymousUser(User):
    @property
    def logged_in(self):
        return False

    def put(self, *args, **kwds):
        """
        Disable puts for Anonymous Users
        """
        pass

AnonymousUser = AnonymousUser()


class Assignment(Base):
    """
    The Assignment Model
    """
    name = ndb.StringProperty() # Must be unique to support submission.
    # TODO(denero) Validate uniqueness of name.
    points = ndb.FloatProperty()
    creator = ndb.KeyProperty(User)
    course = ndb.KeyProperty('Course')

    @staticmethod
    def must_satisfy_static(user, need):
        if not user.logged_in:
            raise NeedException(need)

    def must_satisfy(self, user, need):
        return True


class Course(Base):
    """Courses have enrolled students and assignment lists with due dates."""
    institution = ndb.StringProperty() # E.g., 'UC Berkeley'
    name = ndb.StringProperty() # E.g., 'CS 61A'
    offering = ndb.StringProperty()  # E.g., 'Fall 2014'
    creator = ndb.StructuredProperty(User)
    staff = ndb.KeyProperty(User, repeated=True)


def validate_messages(_, messages):
    """Messages is a JSON string encoding a map from protocols to data."""
    if not messages:
        raise BadValueError('Empty messages')
    try:
        files = json.loads(messages)
        if not isinstance(files, dict):
            raise BadValueError('messages is not a JSON map')
        for k in files:
            if not isinstance(k, (str, unicode)):
                raise BadValueError('key %r is not a string' % k)
        # TODO(denero) Check that each key corresponds to a known protocol,
        #              and call protocol-specific validators on each value.
    except Exception as exc:
        raise BadValueError(exc)


class Submission(Base):
    """A submission is generated each time a student runs the client."""
    submitter = ndb.KeyProperty(User)
    assignment = ndb.KeyProperty(Assignment)
    messages = ndb.StringProperty(validator=validate_messages)
    created = ndb.DateTimeProperty(auto_now_add=True)

    @staticmethod
    def must_satisfy_static(user, need):
        pass

    def must_satisfy(self, user, need):
        #TODO(martinis) add check for number of items
        action, key = need.items
        if action == "get":
            if not user.is_admin or self.submitter == key:
                raise NeedException(need)

