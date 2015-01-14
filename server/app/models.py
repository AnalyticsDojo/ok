#pylint: disable=no-member
#pylint: disable=unused-argument

"""Data models."""

import datetime

from app import constants

from app import app
from app.needs import Need
from app.exceptions import *
from app.utils import parse_date
from flask import json
from flask.json import JSONEncoder as old_json

from google.appengine.ext import ndb

class JSONEncoder(old_json):
    """
    Wrapper class to try calling an object's to_dict() method. This allows
    us to JSONify objects coming from the ORM. Also handles dates & datetimes.
    """
    def default(self, obj):
        if isinstance(obj, ndb.Key):
            got = obj.get()
            if not got:
                return None
            return got.to_json()
        elif isinstance(obj, datetime.datetime):
            obj = convert_timezone(obj)
            return obj.strftime(app.config["GAE_DATETIME_FORMAT"])
        if isinstance(obj, ndb.Model):
            return obj.to_json()
        return super(JSONEncoder, self).default(obj)

app.json_encoder = JSONEncoder

def convert_timezone(utc_dt):
    """Convert times to PST/PDT."""
    # This looks like a hack... is it even right? What about daylight savings?
    # Correct approach: each course should have a timezone. All times should be
    # stored in UTC for easy comparison. Dates should be converted to
    # course-local time when displayed.
    delta = datetime.timedelta(hours=-7)
    return datetime.datetime.combine(utc_dt.date(), utc_dt.time()) + delta


class Base(ndb.Model):
    """Shared utilities."""

    @classmethod
    def from_dict(cls, values):
        """Creates an instance from the given values."""
        inst = cls()
        inst.populate(**values)
        return inst

    def to_json(self, fields=None):
        """Converts this model to a json dictionary."""
        if fields == True:
            return self.to_dict()
        elif fields == False:
            return {}

        if not fields:
            fields = {}
        if fields:
            result = self.to_dict(include=fields.keys())
        else:
            result = self.to_dict()

        if self.key and (not fields or 'id' in fields):
            result['id'] = self.key.id()

        for key, value in result.items():
            if isinstance(value, ndb.Key):
                value = value.get()
                if value:
                    result[key] = value.to_json(fields.get(key))
                else:
                    result[key] = None
            elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], ndb.Key):
                new_list = []
                for value in value:
                    fields_key = fields.get(key)
                    if fields_key and not isinstance(fields_key, dict):
                        if fields.get(key):
                            new_list.append(value)
                    else:
                        value = value.get()
                        if value:
                            new_list.append(value.to_json(fields.get(key)))
                result[key] = new_list
            else:
                try:
                    new_value = app.json_encoder().default(value)
                    result[key] = new_value
                except TypeError:
                    pass
        return result

    @classmethod
    def can(cls, user, need, obj=None, query=None):
        """
        Tells you if the |user| satisfies the given |need| for this object.
        """
        need.set_object(obj or cls)
        return cls._can(user, need, obj, query)

    @classmethod
    def _can(cls, user, need, obj=None, query=None):
        return False


class User(Base):
    """Users may have multiple email addresses. Note: the built-in user model
    in appengine associates a different user object with each email."""
    email = ndb.StringProperty(repeated=True)
    # TODO add a name
    # TODO add a student ID

    def __repr__(self):
        return '<User %r>' % self.email

    ## Properties and getters

    @property
    def logged_in(self):
        return self.email != ["_anon"]

    @classmethod
    @ndb.transactional
    def get_or_insert(cls, email):
        """Retrieve a user by email."""
        assert isinstance(email, str), "bad email:" + str(email)
        users = cls.query().filter(cls.email == email).get()
        if len(users) > 1:
            raise ValueError("Multiple users for email: " + email)
        elif len(users) == 1:
            return users[0]
        else:
            user = cls(email=[email])
            user.put()
            return user

    @classmethod
    def _can(cls, user, need, obj=None, query=None):
        if not user.logged_in:
            return False

        action = need.action
        if need.action == "get":
            if user.is_admin:
                return True
            if obj:
                if obj.key == user.key:
                    return True

            if user.is_staff:
                for course in user.staffed_courses:
                    if course.key in obj.courses:
                        return True
        elif action == "index":
            if user.is_admin:
                return query

            filters = []
            for course in user.courses:
                if user.key in course.staff:
                    filters.append(User.query().filter(
                        User.courses == course.key))

            filters.append(User.key == user.key)

            if len(filters) > 1:
                return query.filter(ndb.OR(*filters))
            else:
                return query.filter(filters[0])
        elif action in ("create", "put"):
            return user.is_admin
        return False


_AnonUser = None
def AnonymousUser():
    global _AnonUser
    if not _AnonUser:
        _AnonUser = User.get_or_insert("_anon")
    return _AnonUser


class Assignment(Base):
    """Assignments are particular to courses, keyed by a unique string that
    should start with the course offering. E.g., cal/cs61a/fa14/proj1.
    """
    display_name = ndb.StringProperty()
    points = ndb.FloatProperty()
    templates = ndb.JsonProperty()
    creator = ndb.KeyProperty(User)
    course = ndb.KeyProperty('Course')
    max_group_size = ndb.IntegerProperty()
    due_date = ndb.DateTimeProperty()
    lock_date = ndb.DateTimeProperty() # no submissions after this date
    active = ndb.ComputedProperty(lambda a: datetime.datetime.now() <= a.lock_date)
    # TODO Add services requested

    @classmethod
    def _can(cls, user, need, obj=None, query=None):
        action = need.action
        if action == "get":
            return True
        elif action == "index":
            return query
        elif action in ("create", "put"):
            return user.is_admin
        return False


class Course(Base):
    """Courses are keyed by offering, e.g. cal/cs61a/fa14."""
    institution = ndb.StringProperty() # E.g., 'UC Berkeley'
    display_name = ndb.StringProperty()
    instructor = ndb.KeyProperty(User, repeated=True)
    active = ndb.BooleanProperty(default=True)

    @classmethod
    def _can(cls, user, need, course=None, query=None):
        action = need.action
        if action == "get":
            if user.is_admin:
                return True
            return True
        elif action == "index":
            return query
        elif action in ("create", "delete", "put"):
            return user.is_admin
        elif action == "modify":
            if user.is_admin:
                return True
            if not course:
                raise ValueError("Need instance for get action.")
            return user.key in course.staff
        elif action == "staff":
            if user.is_admin:
                return True
            return user.key in course.staff
        return False

    @property
    def assignments(self):
        """Return a query for assignments."""
        return Assignment.query(Assignment.course == self.key)


class Participant(Base):
    """Tracks participation of students & staff in courses."""
    user = ndb.KeyProperty(User)
    course = ndb.KeyProperty(Course)
    role = ndb.StringProperty() # See constants.py for roles

    @classmethod
    def _can(cls, user, need, course=None, query=None):
        # TODO
        pass

    @classmethod
    def has_role(self, user, course, role):
        if isinstance(user, User):
            user = user.key
        if isinstance(course, Course):
            course = course.key
        return Participant.query(Participant.user == user,
                                 Participant.course == course,
                                 Participant.role == role).get()


def validate_messages(_, message_str):
    """message_str is a JSON string encoding a map from protocols to data."""
    if not message_str:
        raise BadValueError('Empty messages')
    try:
        messages = json.loads(message_str)
        if not isinstance(messages, dict):
            raise BadValueError('messages is not a JSON map')
    except Exception as exc:
        raise BadValueError(exc)


# TODO CONTINUE HERE

class Message(Base):
    """
    A message given to us from the client.
    """
    contents = ndb.JsonProperty()
    kind = ndb.StringProperty()

    @classmethod
    def _can(cls, user, need, obj=None, query=None):
        action = need.action

        if action == "index":
            return False

        return Submission._can(user, need, obj, query)

class Score(Base):
    """
    The score for a submission.
    """
    score = ndb.IntegerProperty()
    message = ndb.StringProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)
    grader = ndb.KeyProperty('User')

class Submission(Base):
    """A submission is generated each time a student runs the client."""
    submitter = ndb.KeyProperty(User, required=True)
    assignment = ndb.KeyProperty(Assignment)
    created = ndb.DateTimeProperty()
    db_created = ndb.DateTimeProperty(auto_now_add=True)
    messages = ndb.StructuredProperty(Message, repeated=True)
    compScore = ndb.KeyProperty(Score)
    tags = ndb.StringProperty(repeated=True)

    SUBMITTED_TAG = "Submit"

    @classmethod
    def _get_kind(cls):
      return 'Submissionvtwo'

    def get_messages(self, fields=None):
        if not fields:
            fields = {}

        message_fields = fields.get('messages', {})
        if isinstance(message_fields, (str, unicode)):
            message_fields = (True if message_fields == "true" else False)

        messages = {message.kind: message.contents for message in self.messages}
        def test(x):
            if isinstance(message_fields, bool):
                return message_fields

            if not message_fields:
                return True
            return x in message_fields

        def get_contents(kind, contents):
            if isinstance(message_fields, bool):
                return contents

            if message_fields.get(kind) == "presence":
                return True
            return contents

        return {
            kind: get_contents(kind, contents)
            for kind, contents in messages.iteritems()
            if test(kind)}

    @property
    def group(self):
        submitter = self.submitter.get()
        return submitter.groups(self.assignment.get()).get()

    def to_json(self, fields=None):
        json = super(Submission, self).to_json(fields)
        if 'messages' in json:
            json['messages'] = self.get_messages(fields)
        return json

    @classmethod
    def _can(cls, user, need, obj=None, query=None):
        action = need.action
        if action == "get":
            if not obj:
                raise ValueError("Need instance for get action.")
            if user.is_admin or obj.submitter == user.key:
                return True
            if user.is_staff:
                for course in user.staffed_courses:
                    if course.key in obj.submitter.get().courses:
                        return True
            groups = list(user.groups(obj.assignment))
            my_group = obj.group

            if groups and my_group and my_group.key in [g.key for g in groups]:
                return True
            return False
        if action in ("create", "put"):
            return user.logged_in

        if action == "index":
            if not user.logged_in:
                return False

            if not query:
                raise ValueError(
                    "Need query instance for Submission index action")

            if user.is_admin:
                return query

            filters = []
            courses = Course.query().filter(Course.staff == user.key)
            for course in courses:
                assignments = Assignment.query().filter(
                    Assignment.course == course).fetch()

                filters.append(Submission.assignment.IN(
                    [assign.key for assign in assignments]))

            for group in user.groups():
                filters.append(ndb.AND(Submission.submitter.IN(group.members),
                    Submission.assignment == group.assignment))
            filters.append(Submission.submitter == user.key)

            if len(filters) > 1:
                return query.filter(ndb.OR(*filters))
            elif filters:
                return query.filter(filters[0])
            else:
                return query
        return False

class OldSubmission(Base):
    """A submission is generated each time a student runs the client."""
    submitter = ndb.KeyProperty(User, required=True)
    assignment = ndb.KeyProperty(Assignment)
    messages = ndb.JsonProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)
    converted = ndb.BooleanProperty(default=False)

    @classmethod
    def _get_kind(cls):
      return 'Submission'

    @property
    def group(self):
        submitter = self.submitter.get()
        return submitter.groups(self.assignment.get()).get()

    @classmethod
    def _can(cls, user, need, obj=None, query=None):
        return False

    def upgrade(self):
        created = self.created

        analytics = self.messages.get('analytics')
        if analytics:
            date = analytics.get('time') or created
            if not date == created:
                created = parse_date(date)

        new_messages = [Message(kind=kind, contents=contents)
                        for kind, contents in self.messages.iteritems()]

        return Submission(
            submitter=self.submitter,
            assignment=self.assignment,
            created=created,
            messages=new_messages)



class SubmissionDiff(Base):
    submission = ndb.KeyProperty(Submission)
    diff = ndb.JsonProperty()

    @property
    def comments(self):
        return Comment.query(ancestor=self.key).order(Comment.created)

    def to_json(self, fields=None):
        dct = super(SubmissionDiff, self).to_json(fields)
        comments = list(self.comments)
        comment_dict = {}
        for comment in comments:
            if comment.filename not in comment_dict:
                comment_dict[comment.filename] = {}
            if comment.line not in comment_dict[comment.filename]:
                comment_dict[comment.filename][comment.line] = []
            comment_dict[comment.filename][comment.line].append(comment)

        dct['comments'] = comment_dict
        return dct

class Comment(Base):
    author = ndb.KeyProperty('User', required=True)
    created = ndb.DateTimeProperty(auto_now_add=True)
    line = ndb.IntegerProperty(required=True)
    message = ndb.TextProperty(required=True)
    draft = ndb.BooleanProperty(required=True, default=True)
    filename = ndb.StringProperty(required=True)

    @classmethod
    def _can(cls, user, need, comment=None, query=None):
        if need.action == "get":
            return user.is_admin or comment.author == user.key
        if need.action == "delete":
            return user.is_admin or comment.author == user.key
        return False


class Version(Base):
    """A version of client-side resources. Used for auto-updating."""
    name = ndb.StringProperty(required=True)
    versions = ndb.StringProperty(repeated=True)
    current_version = ndb.StringProperty()
    base_url = ndb.StringProperty(required=True)

    def download_link(self, version=None):
        if version is None:
            if not self.current_version:
                raise BadValueError("current version doesn't exist")
            return '/'.join((self.base_url, self.current_version,
                             self.name))
        if version not in self.versions:
            raise BadValueError("specified version %s doesn't exist" % version)
        return '/'.join((self.base_url, version, self.name))

    def to_json(self, fields=None):
        json = super(Version, self).to_json(fields)
        if self.current_version:
            json['current_download_link'] = self.download_link()

        return json

    @classmethod
    def _can(cls, user, need, obj=None, query=None):
        action = need.action

        if action == "delete":
            return False
        if action == "index":
            return query
        if action == "get":
            return True
        return user.is_admin

    @classmethod
    def from_dict(cls, values):
        """Creates an instance from the given values."""
        if 'name' not in values:
            raise ValueError("Need to specify a name")
        inst = cls(key=ndb.Key('Version', values['name']))
        inst.populate(**values) #pylint: disable=star-args
        return inst

    @classmethod
    def get_or_insert(cls, key, **kwargs):
        assert not isinstance(id, int), "Only string keys allowed for versions"
        kwargs['name'] = key
        return super(cls, Version).get_or_insert(key, **kwargs)

    @classmethod
    def get_by_id(cls, key, **kwargs):
        assert not isinstance(id, int), "Only string keys allowed for versions"
        return super(cls, Version).get_by_id(key, **kwargs)

class Group(Base):
    """
    A group is a collection of users who all submit submissions.
    They all can see submissions for an assignment all as a group.
    """
    members = ndb.KeyProperty(kind='User', repeated=True)
    invited_members = ndb.KeyProperty(kind='User', repeated=True)
    assignment = ndb.KeyProperty('Assignment', required=True)

    @classmethod
    def _can(cls, user, need, obj=None, query=None):
        action = need.action
        if not user.logged_in:
            return False

        if action == "index":
            if user.is_admin:
                return query
            return query.filter(Group.members == user.key)

        if user.is_admin:
            return True

        if action == "delete":
            return False
        if action == "invitation":
            return user.key in obj.invited_members
        if action == "member":
            return user.key in obj.members
        if action == "get":
            return user.key in obj.members or user.key in obj.invited_members

        if action in ("create", "put"):
            #TODO(martinis) make sure other students are ok with this group
            if not obj:
                raise ValueError("Need instance for get action.")
            return user.key in obj.members
        return False

    def _pre_put_hook(self):
        max_group_size = self.assignment.get().max_group_size
        if max_group_size and len(self.members) > max_group_size:
            raise BadValueError("Too many members. Max allowed is %s" % (
                max_group_size))

def anon_converter(prop, value):
    if not value.get().logged_in:
        return None

    return value

class AuditLog(Base):
    created = ndb.DateTimeProperty(auto_now_add=True)
    event_type = ndb.StringProperty(required=True)
    user = ndb.KeyProperty('User', required=True, validator=anon_converter)
    description = ndb.StringProperty()
    obj = ndb.KeyProperty()

class Queue(Base):
    assignment = ndb.KeyProperty(Assignment, required=True)
    assigned_staff = ndb.KeyProperty(User, repeated=True)

    @property
    def submissions(self):
        return [fs.submission for fs in
            FinalSubmission.query().filter(FinalSubmission.queue == self.key)]

    @classmethod
    def _can(cls, user, need, obj=None, query=None):
        action = need.action
        if not user.logged_in:
            return False

        if action == "index":
            if user.is_admin:
                return query
            return False

        if user.is_admin:
            return True

        return False

    def to_json(self, fields=None):
        if not fields:
            fields = {}

        return {
            'submissions': [{'id': val.id()} for val in self.submissions],
            'assignment': self.assignment.get(),
            'assigned_staff': [val.get().to_json(fields.get('assigned_staff')) for val in self.assigned_staff],
            'id': self.key.id()
        }

class FinalSubmission(Base):
    assignment = ndb.KeyProperty(Assignment, required=True)
    group = ndb.KeyProperty(Group, required=True)
    submission = ndb.KeyProperty(Submission, required=True)
    published = ndb.BooleanProperty(default=False)
    queue = ndb.KeyProperty(Queue)

    @property
    def assigned(self):
        return bool(self.queue)

    @classmethod
    def _can(cls, user, need, obj=None, query=None):
        action = need.action
        if not user.logged_in:
            return False

        if action == "index":
            if user.is_admin:
                return query
            return False

        if user.is_admin:
            return True

        return False
