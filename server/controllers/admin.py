from flask import Blueprint, render_template, flash, redirect, url_for, abort

from flask.ext.login import login_required, current_user
from functools import wraps
import pytz

from server.models import User, Course, Assignment, Participant, db
from server.constants import STAFF_ROLES
from server.forms import AssignmentForm

admin = Blueprint('admin', __name__)


def convert_to_pacific(date):
    # TODO Move to UTILS
    return date.replace(tzinfo=pytz.utc)


def is_staff(course_arg=None):
    """ A decorator for routes to ensure that user is a member of
    the course staff.

    Usage:
    @is_staff() - A staff member for any course
    @is_staff(course_arg=1) A staff member for the course with id 1
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if current_user.is_authenticated:
                roles = current_user.enrollments(roles=STAFF_ROLES)
                if len(roles) > 0 or current_user.is_admin:
                    if course_arg:
                        course = kwargs[course_arg]
                        if course in [r.course.id for r in roles]:
                            return func(*args, **kwargs)
                    else:
                        return func(*args, **kwargs)
            flash("You are not on the course staff", "error")
            return redirect(url_for("student.index"))
        return wrapper
    return decorator


def get_courses(cid=None):
    #  TODO : The decorator could add these to the routes
    enrollments = current_user.enrollments(roles=STAFF_ROLES)
    courses = [e.course for e in enrollments]
    matching_courses = [c for c in courses if c.id == cid]
    if not cid:
        return courses, []
    elif len(matching_courses) == 0:
        abort(401)  # TODO to actual error page
    current_course = matching_courses[0]
    return courses, current_course


@admin.route("/")
@is_staff()
def index():
    courses, current_course = get_courses()
    return render_template('staff/index.html', courses=courses)


@admin.route("/course/<int:cid>")
@is_staff(course_arg='cid')
def course(cid):
    courses, current_course = get_courses(cid)
    return render_template('staff/course/index.html',
                           courses=courses, current_course=current_course)


@admin.route("/course/<int:cid>/assignments")
@is_staff(course_arg='cid')
def course_assignments(cid):
    courses, current_course = get_courses(cid)
    assgns = current_course.assignments
    active_asgns = [a for a in assgns if a.active]
    due_asgns = [a for a in assgns if not a.active]
    # TODO CLEANUP : Better way to send this data to the template.

    return render_template('staff/course/assignments.html',
                           courses=courses, current_course=current_course,
                           active_asgns=active_asgns, due_assgns=due_asgns)


@admin.route("/course/<int:cid>/assignments/new", methods=["GET", "POST"])
@is_staff(course_arg='cid')
def new_assignment(cid):
    courses, current_course = get_courses(cid)
    # TODO  Form Creation
    form = AssignmentForm()

    if form.validate_on_submit():
        model = Assignment(course_id=cid, creator=current_user.id)
        form.populate_obj(model)
        # TODO CONVERT TO UTC from PST.
        db.session.add(model)
        db.session.commit()

        flash("Assignment created successfully.", "success")
        return redirect(url_for(".course_assignments", cid=cid))

    return render_template('staff/course/assignment.new.html', form=form,
                           courses=courses, current_course=current_course)


@admin.route("/course/<int:cid>/assignments/<int:aid>",
             methods=['GET', 'POST'])
@is_staff(course_arg='cid')
def assignment(cid, aid):
    courses, current_course = get_courses(cid)
    assgn = Assignment.query.filter_by(id=aid, course_id=cid).one()
    # Convert TZ to Pacific
    assgn.due_date = convert_to_pacific(assgn.due_date)
    assgn.lock_date = convert_to_pacific(assgn.lock_date)

    form = AssignmentForm(obj=assgn)

    if assgn.course != current_course:
        return abort(401)

    return render_template('staff/course/assignment.html', assignment=assgn,
                           form=form, courses=courses,
                           current_course=current_course)
