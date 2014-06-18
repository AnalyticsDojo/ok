"""
Sets up the path and stuff for anything running this.

You can run "python -i run.py" to have a sort of console.
"""
import os
import sys

sys.path.insert(1, os.path.join(os.path.abspath('.'), 'gaenv'))
import app #pylint: disable=W0611

