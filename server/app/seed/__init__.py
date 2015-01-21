from app import models
from app import utils

import json

SEED_OFFERING="cal/cs61a/fa14"

def is_seeded():
    is_seed = models.Course.offering==SEED_OFFERING
    return bool(models.Course.query(is_seed).get())

def seed():
    import os
    import datetime
    import random
    from google.appengine.ext import ndb

    def make_seed_course(creator):
        return models.Course(
            display_name="CS 61A",
            institution="UC Soumya",
            offering=SEED_OFFERING,
            instructor=[creator.key])

    def make_future_assignment(course, creator):
        date = (datetime.datetime.now() + datetime.timedelta(days=365))
        with open('app/seed/hog_template.py') as fp:
            templates = {}
            templates['hog.py'] = fp.read()
            templates['hogq.scm'] = fp.read()

        return models.Assignment(
            name='proj1',
            display_name="Hog",
            points=20,
            templates=json.dumps(templates),
            creator=creator.key,
            course=course.key,
            max_group_size=4,
            due_date=date,
            lock_date=date,
            )

    # Will reject all scheme submissions
    def make_past_assignment(course, creator):
        date = (datetime.datetime.now() - datetime.timedelta(days=365))
        with open('app/seed/scheme_templates/scheme.py') as sc, \
            open('app/seed/scheme_templates/scheme_reader.py') as sr, \
            open('app/seed/scheme_templates/tests.scm') as tests, \
            open('app/seed/scheme_templates/questions.scm') as quest :
            templates = {}
            templates['scheme.py'] = sc.read(),
            templates['scheme_reader.py'] = sr.read(),
            templates['tests.scm'] = tests.read(),
            templates['questsions.scm'] = quest.read(),

        return models.Assignment(
            name='cal/61A/fa14/proj4',
            points=20,
            display_name="Scheme",
            templates=json.dumps(templates),
            course=course.key,
            creator=creator.key,
            max_group_size=4,
            due_date=date)

    def make_group(assign, members):
        return models.Group(
            member=[m.key for m in members],
            assignment = assign.key
        )

    def make_invited_group(assign, members):
        return models.Group(
            member=[members[0].key],
            invited=[members[1].key],
            assignment = assign.key
        )


    def make_seed_submission(assignment, submitter, final=False):
        #TODO(soumya): Change this to actually be a submission.
        sdate = (datetime.datetime.now() - datetime.timedelta(days=random.randint(0,12), seconds=random.randint(0,86399)))

        with open('app/seed/hog_modified.py') as fp:
            messages = {}
            messages['file_contents'] = {
                'hog.py': fp.read(),
                'hogq.scm': 'Blank Stuff',
                'submit': final
            }

        messages = [models.Message(kind=kind, contents=contents)
                    for kind, contents in messages.items()]
        return models.Backup(
            messages=messages,
            assignment=assignment.key,
            submitter=submitter.key,
            created=sdate)


    def make_seed_scheme_submission(assignment, submitter, final=False):
        #TODO(soumya): Change this to actually be a submission
        sdate = (datetime.datetime.now() - datetime.timedelta(days=random.randint(0,12), seconds=random.randint(0,86399)))

        with open('app/seed/scheme.py') as sc, \
            open('app/seed/scheme_reader.py') as sr, \
            open('app/seed/tests.scm') as tests, \
            open('app/seed/questions.scm') as quest :
            messages = {}
            messages['file_contents'] = {
                'scheme.py': sc.read(),
                'scheme_reader.py': sr.read(),
                'tests.scm': tests.read(),
                'questsions.scm': quest.read(),
                'submit': final
            }

        messages = [models.Message(kind=kind, contents=contents)
                    for kind, contents in messages.items()]
        return models.Backup(
            messages=messages,
            assignment=assignment.key,
            submitter=submitter.key,
            created=sdate)

    def make_version(current_version):
        return models.Version(
            name='ok',
            id='ok',
            base_url='https://github.com/Cal-CS-61A-Staff/ok/releases/download',
            versions=[current_version],
            current_version=current_version
        )


    def make_queue(assignment, submissions, asignee):
        queue = models.Queue(
            assignment=assignment.key,
            assigned_staff=[asignee.key])
        queue = queue.put()
        for subm in submissions:
            fs = models.FinalSubmission(
                assignment=assignment.key,
                group=subm.submitter.get().get_group(assignment.key).key,
                submission=subm.key,
                queue=queue)
            fs.put()

    # Start putting things in the DB.

    c = models.User(
        email=["test@example.com"],
        is_admin=True
    )
    c.put()

    a = models.User(
        email=["dummy@admin.com"],
    )
    a.put()

    students = []
    group_members = []

    for i in range(4):
        s = models.User(
            email=["partner" + str(i) + "@teamwork.com"],
        )
        s.put()
        group_members += [s]


    for i in range(0,9):
        s = models.User(
            email=["student" + str(i) + "@student.com"],
        )
        s.put()
        students += [s]


    k = models.User(
        email=["dummy2@admin.com"],
    )
    k.put()

    version = make_version('v1.3.0')
    version.put()

    # Create a course
    course = make_seed_course(c)
    course.put()

    # Put a few members on staff
    course.instructor.append(c.key)
    course.put()
    course.instructor.append(a.key)
    course.put()


    # Create a few assignments
    assign = make_future_assignment(course, c)
    assign.put()
    assign2 = make_past_assignment(course, c)
    assign2.put()


    # Create submissions
    subms = []

    # Group submission
    team1 = group_members[0:2]
    g1 = make_group(assign, team1)
    g1.put()

    team2 = group_members[2:4]
    g2 = make_invited_group(assign, team2)
    g2.put()

    # Have each member in the group submit one
    for member in group_members:
        subm = make_seed_submission(assign, member)
        subm.put()

    for member in group_members:
        subm = make_seed_scheme_submission(assign2, member)
        subm.put()

    # Make this one be a final submission though.
    subm = make_seed_submission(assign, group_members[1], True)
    subm.put()
    subms.append(subm)

    # scheme final
    subm = make_seed_scheme_submission(assign2, group_members[1], True)
    subm.put()


    # Now create indiviual submission
    for i in range(9):
        subm = make_seed_submission(assign, students[i])
        subm.put()
        #subms.append(subm)

        subm = make_seed_submission(assign, students[i], True)
        subm.put()
        #subms.append(subm)



    # TODO(soumya): Seed a queue. This should be auto-generated.

    # q = make_queue(assign, subms, c)
    # q = make_queue(assign, subms, k)

    #utils.assign_work(assign.key)





