import os
from flask import Flask
from app.lib_master_python.json_session_interface import JSONSessionInterface

session_path = '/tmp/python_recipe_sessions'

app = Flask(__name__)
app.config.from_pyfile('config.py')
app.secret_key = ']V<\4/)qC?EwWnd9'

if 'DYNO' in os.environ:  # On Heroku?
    import logging
    stream_handler = logging.StreamHandler()
    app.logger.addHandler(stream_handler)
    app.logger.setLevel(logging.INFO)
    app.logger.info('Recipe example startup')
    app.config.update(dict(PREFERRED_URL_SCHEME = 'https'))

from app import views

# Set up sessions
if not os.path.exists(session_path):
    os.mkdir(session_path)
    os.chmod(session_path, int('700', 8))
app.session_interface = JSONSessionInterface(session_path)