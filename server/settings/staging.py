import os
import sys
import binascii

default_secret = binascii.hexlify(os.urandom(24))

ENV = 'staging'
SECRET_KEY = os.getenv('SECRET_KEY', default_secret)
CACHE_TYPE = 'simple'

DEBUG = False
ASSETS_DEBUG = False
TESTING_LOGIN = False
DEBUG_TB_INTERCEPT_REDIRECTS = False

SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_URL', 'sqlite:///../oksqlite.db')
WTF_CSRF_CHECK_DEFAULT = True
WTF_CSRF_ENABLED = True

try:
   os.environ["GOOGLE_ID"]
   os.environ["GOOGLE_SECRET"]
except KeyError:
   print("Please set the google login variables. source secrets.sh")
   sys.exit(1)

GOOGLE = {
    'consumer_key': os.environ.get('GOOGLE_ID'),
    'consumer_secret':  os.environ.get('GOOGLE_SECRET')
}

SENDGRID_AUTH = {
    'user': os.environ.get("SENDGRID_USER"),
    'key': os.environ.get("SENDGRID_KEY")
}
