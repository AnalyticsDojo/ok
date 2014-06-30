#pylint: disable=C0103,no-member
"""
Models
"""
from sqlalchemy.ext.declarative import declarative_base

from flask.ext.sqlalchemy import SQLAlchemy #pylint: disable=F0401,E0611
from flask import Blueprint
from app import constants

model_blueprint = Blueprint('models', __name__)

from app import app
from flask import json
from flask.json import JSONEncoder as old_json

from google.appengine.ext import ndb

db = SQLAlchemy(app)

class JSONEncoder(old_json):
    """
    Wrapper class to try calling an object's to_dict() method. This allows
    us to JSONify objects coming from the ORM. Also handles dates and datetimes.
    """

    def default(self, obj): #pylint: disable=E0202
        if isinstance(obj, ndb.Key):
            return obj.id()
        try:
            return obj.to_dict()
        except AttributeError:
            return json.JSONEncoder.default(self, obj)

app.json_encoder = JSONEncoder

base = declarative_base()

class Base(ndb.Model):
    """
    Add some default properties and methods to the SQLAlchemy declarative Base.
    """
    def update_values(self, values):
        """
        Merge in items in the values dict into our object if it's one of
        our columns
        """
        for name, value in values.iteritems():
            setattr(self, name, value)

    @classmethod
    def from_dict(cls, values):
        """
        Creates an instance from the given values
        """
        inst = cls()
        inst.update_values(values)
        return inst


class User(Base): #pylint: disable=R0903
    """
    The User Model
    """
    email = ndb.StringProperty()
    login = ndb.StringProperty()
    role = ndb.IntegerProperty(default=constants.STUDENT_ROLE)
    first_name = ndb.StringProperty()
    last_name = ndb.StringProperty()

    def __repr__(self):
        return '<User %r>' % self.email

class Submission(Base): #pylint: disable=R0903
    """
    The Submission Model
    """
    location = ndb.StringProperty()

class Assignment(Base): #pylint: disable=R0903
    """
    The Assignment Model
    """
    name = ndb.StringProperty()
    points = ndb.IntegerProperty()
