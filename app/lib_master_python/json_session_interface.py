"""Uses JSON-formated file storage for sessions

NOTE: does not time-out the sessions!

Based on http://flask.pocoo.org/snippets/132/
"""

import os, json

from uuid import uuid1
from collections import MutableMapping
from flask.sessions import SessionInterface, SessionMixin


class JSONSession(MutableMapping, SessionMixin):
    """Server-side session implementation.

    Uses JSON storage to achieve a disk-backed session.
    """

    def __init__(self, directory, sid, *args, **kwargs):
        self.path = os.path.join(directory, sid)
        self.directory = directory
        self.sid = sid # session id
        self.read()

    def __getitem__(self, key):
        self.read()
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value
        self.save()

    def __delitem__(self, key):
        del self.data[key]
        self.save()

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def read(self):
        """Load json from (ram)disk."""
        try:
            with open(self.path) as data_file:
                self.data = json.load(data_file)
        except (ValueError, EOFError, IOError):
            self.data = {}

    def save(self):
        """Dump json to (ram)disk atomically."""
        new_name = '{}.new'.format(self.path)
        with open(new_name, 'w') as data_file:
            data_file.write(json.dumps (self.data))
        os.rename(new_name, self.path)

    # Note: Newer versions of Flask no longer require
    # CallableAttributeProxy and PersistedObjectProxy

class JSONSessionInterface(SessionInterface):
    """Basic SessionInterface which uses the JSONSession."""

    def __init__(self, directory):
        self.directory = os.path.abspath(directory)
        if not os.path.isdir(self.directory):
            os.makedirs(self.directory)

    def open_session(self, app, request):
        sid = request.cookies.get(
            app.session_cookie_name) or '{}-{}'.format(uuid1(), os.getpid())
        return JSONSession(self.directory, sid)

    def save_session(self, app, session, response):
        domain = self.get_cookie_domain(app)
        if not session:
            try:
                os.unlink(session.path)
            except OSError:
                pass
            response.delete_cookie(
                app.session_cookie_name, domain=domain)
            return
        cookie_exp = self.get_expiration_time(app, session)
        response.set_cookie(
            app.session_cookie_name, session.sid,
            expires=cookie_exp, httponly=True, domain=domain)

# Can be used like so:
#
# path = '/run/shm/app_session'
# if not os.path.exists(path):
#     os.mkdir(path)
#     os.chmod(path, int('700', 8))
# app.session_interface = JSONSessionInterface(path)