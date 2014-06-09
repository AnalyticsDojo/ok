#pylint: disable=C0103
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

db = SQLAlchemy(app)

class JSONEncoder(old_json):
    """
    Wrapper class to try calling an object's tojson() method. This allows
    us to JSONify objects coming from the ORM. Also handles dates and datetimes.
    """

    def default(self, obj): #pylint: disable=E0202
        try:
            return obj.tojson()
        except AttributeError:
            return json.JSONEncoder.default(self, obj)

app.json_encoder = JSONEncoder

# Let's make this a class decorator
base = declarative_base()

class Base(object):
    """
    Add some default properties and methods to the SQLAlchemy declarative Base.
    """

    @property
    def columns(self):
        """
        Returns a list of the names of the columns for this object
        """
        return [c.name for c in self.__table__.columns] #pylint: disable=no-member

    @property
    def column_items(self):
        """
        Returns a dictionary of column to data value for this object
        """
        return dict([(c, getattr(self, c)) for c in self.columns])

    def tojson(self):
        """
        Converts the object to json.
        """
        return self.column_items

class User(db.Model, Base): #pylint: disable=R0903
    """
    The User Model
    """
    user_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True)
    login = db.Column(db.String(30))
    role = db.Column(db.Integer, default=constants.STUDENT_ROLE)

    def __repr__(self):
        return '<User %r>' % self.email

class Assignment(db.Model, Base): #pylint: disable=R0903
    """
    The Assignment Model
    """
    id = db.Column(db.Integer, primary_key=True)
    submissions = db.relationship('Submission', backref="assignment")

    def __init__(self, *args, **kwds):
        db.Model.__init__(*args, **kwds)

class Submission(db.Model, Base): #pylint: disable=R0903
    """
    The Submission Model
    """
    id = db.Column(db.Integer, primary_key=True)
    person_id = db.Column(db.Integer, db.ForeignKey('assignment.id'))

    def __init__(self, *args, **kwds):
        db.Model.__init__(*args, **kwds)
