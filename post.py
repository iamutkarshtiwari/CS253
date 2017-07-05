from google.appengine.ext import db


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
