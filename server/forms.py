from flask_wtf import Form
from flask_wtf.file import FileField, FileRequired
from wtforms import (StringField, DateTimeField, BooleanField, IntegerField,
                     SelectField, TextAreaField, DecimalField, HiddenField,
                     SelectMultipleField, widgets, validators)
from flask_wtf.html5 import EmailField

import datetime as dt

from server import utils
from server.models import Assignment
from server.constants import VALID_ROLES, GRADE_TAGS

import csv
import logging

def strip_whitespace(value):
    if value and hasattr(value, "strip"):
        return value.strip()
    else:
        return value

class MultiCheckboxField(SelectMultipleField):
    """
    A multiple-select, except displays a list of checkboxes.

    Iterating the field will produce subfields, allowing custom rendering of
    the enclosed checkbox fields.
    """
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()

class BaseForm(Form):
    class Meta:
        def bind_field(self, form, unbound_field, options):
            filters = unbound_field.kwargs.get('filters', [])
            field_type = type(unbound_field)
            if field_type == StringField:
                filters.append(strip_whitespace)
            return unbound_field.bind(form=form, filters=filters, **options)


class AssignmentForm(BaseForm):
    def __init__(self, course, obj=None, **kwargs):
        self.course = course
        super(AssignmentForm, self).__init__(obj=obj, **kwargs)
        if obj:
            if obj.due_date == self.due_date.data:
                self.due_date.data = utils.local_time_obj(obj.due_date, course)
            if obj.lock_date == self.lock_date.data:
                self.lock_date.data = utils.local_time_obj(obj.lock_date, course)

    display_name = StringField(u'Display Name',
                               validators=[validators.required()])
    name = StringField(u'Offering', validators=[validators.required()])
    due_date = DateTimeField(u'Due Date (Course Time)',
                             default=dt.datetime.now,
                             validators=[validators.required()])
    lock_date = DateTimeField(u'Lock Date (Course Time)',
                              default=dt.datetime.now,
                              validators=[validators.required()])
    max_group_size = IntegerField(u'Max Group Size', default=1,
                                  validators=[validators.required()])
    url = StringField(u'URL',
                      validators=[validators.optional(), validators.url()])
    revisions = BooleanField(u'Enable Revisions', default=False,
                             validators=[validators.optional()])
    autograding_key = StringField(u'Autograder Key', [validators.optional()])

    def populate_obj(self, obj):
        """ Updates obj attributes based on form contents. """
        super(AssignmentForm, self).populate_obj(obj)
        obj.due_date = utils.server_time_obj(self.due_date.data, self.course)
        obj.lock_date = utils.server_time_obj(self.lock_date.data, self.course)

    def validate(self):
        check_validate = super(AssignmentForm, self).validate()

        # if our validators do not pass
        if not check_validate:
            return False

        # If the name is changed, ensure assignment offering is unique
        assgn = Assignment.query.filter_by(name=self.name.data).first()
        if assgn:
            self.name.errors.append('That offering already exists')
            return False
        return True

class AssignmentUpdateForm(AssignmentForm):
    def validate(self):
        return super(AssignmentForm, self).validate()

class AssignmentTemplateForm(BaseForm):
    template_files = FileField('Template Files', [FileRequired()])

class EnrollmentForm(BaseForm):
    name = StringField(u'Name', validators=[validators.optional()])
    email = EmailField(u'Email',
                       validators=[validators.required(), validators.email()])
    sid = StringField(u'SID', validators=[validators.optional()])
    secondary = StringField(u'Secondary Auth (e.g Username)',
                            validators=[validators.optional()])
    section = StringField(u'Section',
                          validators=[validators.optional()])
    role = SelectField(u'Role',
                       choices=[(r, r.capitalize()) for r in VALID_ROLES])


class VersionForm(BaseForm):
    current_version = EmailField(u'Current Version',
                                 validators=[validators.required()])
    download_link = StringField(u'Download Link',
                                validators=[validators.required(), validators.url()])


class BatchEnrollmentForm(BaseForm):
    csv = TextAreaField(u'Email, Name, SID, Course Login, Section')

    def validate(self):
        check_validate = super(BatchEnrollmentForm, self).validate()
        # if our validators do not pass
        if not check_validate:
            return False
        try:
            rows = self.csv.data.splitlines()
            self.csv.parsed = list(csv.reader(rows))
        except csv.Error as e:
            logging.error(e)
            self.csv.errors.append(['The CSV could not be parsed'])
            return False

        for row in self.csv.parsed:
            if len(row) != 5:
                err = "{} did not have 5 columns".format(row)
                self.csv.errors.append(err)
                return False
            if not row[0]:
                err = "{} did not have an email".format(row)
                self.csv.errors.append(err)
                return False
            elif "@" not in row[0]:
                # TODO : Better email check.
                err = "{} is not a valid email".format(row[0])
                self.csv.errors.append(err)
                return False
        return True

class CSRFForm(BaseForm):
    pass

class GradeForm(BaseForm):
    score = DecimalField('Score', validators=[validators.required()])
    message = TextAreaField('Message', validators=[validators.required()])
    kind = SelectField('Kind', choices=[(c, c.title()) for c in GRADE_TAGS],
                       validators=[validators.required()])

class CompositionScoreForm(GradeForm):
    score = SelectField('Composition Score',
                        choices=[('0', '0'), ('1', '1'), ('2', '2')],
                        validators=[validators.required()])
    kind = HiddenField('Score', default="composition",
                       validators=[validators.required()])

class CreateTaskForm(BaseForm):
    kind = SelectField('Kind', choices=[(c, c.title()) for c in GRADE_TAGS],
                       validators=[validators.required()], default="composition")
    staff = MultiCheckboxField('Assigned Staff', choices=[],
                    validators=[validators.required()])

class AutogradeForm(BaseForm):
    description = """Paste into terminal to get token: cd ~/.config/ok;python3 -c "import pickle; print(pickle.load(open('auth_refresh', 'rb'))['access_token'])"; cd -; """
    token = StringField('Access Token', description=description,
                        validators=[validators.optional()])
    autograder_id = StringField('Autograder Assignment ID',
                                 validators=[validators.required()])
    autopromote = BooleanField('Backup Autopromotion',
                                description="If an enrolled student does not have a submission, this will grade their latest submission before the deadline")
