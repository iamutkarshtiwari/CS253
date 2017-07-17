import hashlib
import random

from string import letters
from google.appengine.ext import db


def make_salt(length=5):
    return ''.join(random.choice(letters) for x in xrange(length))


def make_pw_hash(name, pw, salt=None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s|%s' % (salt, h)


def valid_pw(name, password, h):
    salt = h.split('|')[0]
    return h == make_pw_hash(name, password, salt)


class User(db.Model):
    user_id = db.StringProperty(required=True)
    password = db.StringProperty(required=True)
    email = db.StringProperty()

    @classmethod
    def by_id(self, uid):
        """
            This method fetches the User objects 
            from database based on object id.
        """
        return User.get_by_id(uid)

    @classmethod
    def by_user_id(self, username):
        """
            Returns the User object that matches the username.
        """
        return User.all().filter('user_id = ', username).get()

    @classmethod
    def register(self, username, pw, email=None):
        """
            This method creates a new User in database.
        """
        pw_hash = make_pw_hash(username, pw)
        return User(user_id=username,
                    password=pw_hash,
                    email=email)

    @classmethod
    def login(self, username, pw):
        """
            This method creates.
        """
        u_id = self.by_user_id(username)
        if u_id and valid_pw(username, pw, u_id.password):
            return u_id
