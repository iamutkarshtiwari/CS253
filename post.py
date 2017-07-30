from google.appengine.ext import db
from user import User


# Post Model
class Post(db.Model):
    """
        Holds info about who wrote this post and when.
    """
    user_id = db.StringProperty(required=True)
    subject = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now=True)


class Like(db.Model):
    user_id = db.StringProperty(required=True)
    post_id = db.StringProperty(required=True)

    def getUserName(self):
        user = User.by_id(self.user_id)
        return user.user_id


class Comment(db.Model):
    user_id = db.StringProperty(required=True)
    post_id = db.StringProperty(required=True)
    comment = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)
    last_modified = db.DateTimeProperty(auto_now=True)

    def getUserName(self):
        user = User.by_id(self.user_id)
        return user.user_id
