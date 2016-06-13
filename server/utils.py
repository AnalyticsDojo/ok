import datetime as dt
import logging
import os
import random
from urllib.parse import urlparse, urljoin

from flask import render_template, url_for
from hashids import Hashids
import humanize
from premailer import transform
import pytz
import sendgrid

from server.extensions import cache

sg = sendgrid.SendGridClient(
    os.getenv('SENDGRID_API_KEY'), None, raise_errors=True)
logger = logging.getLogger(__name__)

# ID hashing configuration.
# DO NOT CHANGE ONCE THE APP IS PUBLICLY AVAILABLE. You will break every
# link with an ID in it.
hashids = Hashids(min_length=6)


def encode_id(id_number):
    return hashids.encode(id_number)

def decode_id(value):
    numbers = hashids.decode(value)
    if len(numbers) != 1:
        raise ValueError('Could not decode hash {} into ID'.format(value))
    return numbers[0]

# Timezones. Be cautious with using tzinfo argument. http://pytz.sourceforge.net/
# "tzinfo argument of the standard datetime constructors ‘’does not work’’
# with pytz for many timezones."

def local_time(time, course):
    """Format a time string in a course's locale.
    """
    if not time.tzinfo:
        # Assume UTC
        time = pytz.utc.localize(time)
    return time.astimezone(course.timezone).strftime('%a %m/%d %-I:%M %p')

def local_time_obj(time, course):
    """Get a Datetime object in a course's locale from a TZ Aware DT object."""
    if not time.tzinfo:
        time = pytz.utc.localize(time)
    return time.astimezone(course.timezone)

def server_time_obj(time, course):
    """Convert a datetime object from a course's locale to a UTC
    datetime object.
    """
    if not time.tzinfo:
        time = course.timezone.localize(time)
    # Store using UTC on the server side.
    return time.astimezone(pytz.utc)

def natural_time(date):
    """Format a human-readable time difference (e.g. "6 days ago")"""
    if date.tzinfo:
        date.astimezone(pytz.utc)
        date.replace(tzinfo=None)

    now = dt.datetime.utcnow()
    return humanize.naturaltime(now - date)

def is_safe_redirect_url(request, target):
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))
    return redirect_url.scheme in ('http', 'https') and \
        host_url.netloc == redirect_url.netloc

def random_row(query):
    count = query.count()
    if not count:
        return None
    return query.offset(random.randrange(count)).first()


def group_action_email(members, subject, text):
    emails = [m.user.email for m in members]
    return send_email(emails, subject, text)


def invite_email(member, recipient, assignment):
    subject = "{} group invitation".format(assignment.display_name)
    text = "{} has invited you to join their group".format(member.email)
    link_text = "Respond to the invitation"
    link = url_for('student.assignment', name=assignment.name, _external=True)
    template = 'email/invite.html'

    send_email(recipient.email, subject, text, template,
               link_text=link_text, link=link)


def send_email(to, subject, body, template='email/notification.html',
               link=None, link_text="Sign in"):
    """ Send an email using sendgrid.
    Usage: send_email('student@okpy.org', 'Hey from OK', 'hi')
    """
    if not link:
        link = url_for('student.index', _external=True)
    html = render_template(template, subject=subject, body=body,
                           link=link, link_text=link_text)
    message = sendgrid.Mail(
        to=to,
        from_name="Okpy.org",
        from_email="no-reply@okpy.org",
        subject=subject,
        html=transform(html),
        text=body)

    try:
        status, msg = sg.send(message)
        return status
    except (sendgrid.SendGridClientError, sendgrid.SendGridServerError,
            TypeError):
        logger.error("Could not send email", exc_info=True)
        return

def chunks(l, n):
    """ Yield N successive chunks from L. Used for evenly distributing
    grading tasks.

    Source: http://stackoverflow.com/a/2130042/411514

    >>> three_chunks = chunks(range(56), 3)
    >>> [len(i) for i in three_chunks] == [19, 19, 18]
    >>> five_chunks = chunks(range(55), 5)
    >>> [len(i) for i in five_chunks] == [11, 11, 11, 11, 11]
    """
    if n == 0:
        return
    new_n = int(1.0 * len(l) / n + 0.5)
    for i in range(0, n - 1):
        yield l[i * new_n: i * new_n + new_n]
    yield l[n * new_n - new_n:]
