import webapp2
import jinja2
import os
import re
import time
import hmac

from google.appengine.ext import db
from google.appengine.api import memcache

from user import User
from post import Post, Like, Comment

# For cookie hashing
secret = 'super_secured'


def make_secure_val(val):
    """
        Creates secure value using secret.
    """
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())


def check_secure_val(secure_val):
    """
        Verifies secure value against secret.
    """
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val

jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader('templates'),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


def jinja_render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)


class BlogHandler(webapp2.RequestHandler):

    def write(self, *a, **kw):
        """
            This methods write output to client browser.
        """
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        """
            This methods renders html using template.
        """
        if self.user:
            params['username'] = self.user
        return jinja_render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def set_secure_cookie(self, name, val):
        """
            Sets secure cookie to browser.
        """
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        """
            Reads secure cookie to browser.
        """
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, username):
        """
            Verifies user existance.
        """
        self.set_secure_cookie('user_id', str(username.key().id()))

    def logout(self):
        """
            Removes login information from cookies.
        """
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    def initialize(self, *a, **kw):
        """
            This methods gets executed for each page and
            verfies user login status, using cookie information.
        """
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        if (uid and User.by_id(int(uid))):
            self.user = str(User.by_id(int(uid)).user_id)
        else:
            self.user = None


class MainPage(BlogHandler):

    def get(self):
        self.redirect('/blog')


class Login(BlogHandler):

    def get(self):
        self.render('login-form.html', error=self.request.get('error'))

    def post(self):
        """
            Login validation.
        """
        username = self.request.get('username')
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/blog/profile/%s' % username)
        else:
            msg = 'Invalid login'
            self.render('login-form.html', error=msg)


class Logout(BlogHandler):

    def get(self):
        self.logout()
        self.redirect('/blog')


class SignUp(BlogHandler):

    def get(self):
        # Redirect if logged in
        if self.user:
            self.redirect("/blog/profile/%s" % self.user)
        else:
            self.render('signup-form.html')

    def post(self):
        self.validate()

    def validate(self):
        params = dict()
        username = self.request.get('username')
        password = self.request.get('password')
        password_verify = self.request.get('verify')
        email = self.request.get('email')

        params['username'] = username
        params['email'] = email
        is_error = False

        if not (username and (re.compile(r"^[a-zA-Z0-9_-]{3,20}$").match(username))):
            params['error_username'] = "That wasn't a valid username."
            params['username'] = ""
            is_error = True
        else:
            u = User.all().filter('user_id = ', username).get()
            if u:
                params['error_username'] = "This username already exists"
                params['username'] = ""
                is_error = True

        if not (password and (re.compile(r"^.{3,20}$").match(password))):
            params['error_password'] = "That wasn't a valid password."
            is_error = True
        elif password_verify != password:
            params['error_verify'] = "The password did not match."
            is_error = True

        if email:
            if not(re.compile(r"^[\S]+@[\S]+.[\S]+$").match(email)):
                params['error_email'] = "That's not a valid email address."
                params['email'] = ""
                is_error = True

        if is_error:
            self.render('signup-form.html', **params)
        else:

            # Used Memcached to prevent registration clash with same username
            if (memcache.get(username) is None):
                memcache.set(key=username, value=1)

                # Database registration
                u = User.register(username, password, email)
                u.put()

                # Clear memcache
                memcache.delete(username)

                self.login(u)
                self.redirect('/blog/profile/%s' % username)
            else:
                params['error_username'] = "This username already exists"
                params['username'] = ""
                self.render('signup-form.html', **params)


class NewPost(BlogHandler):

    def get(self):
        if self.user:
            self.render("newpost.html")
        else:
            self.redirect("/login?error=You need to be logged, in order" +
                          " to create a post!")

    def post(self):
        if self.user:
            subject = self.request.get('subject')
            content = self.request.get('content')
            if not (subject and content):
                self.render('newpost.html',
                            subject=subject, content=content, error="Subject and content, please!")
            else:
                postdata = Post(user_id=self.user,
                                subject=subject, content=content)
                postdata.put()
                self.redirect("/blog/%s" %
                              str(postdata.key().id()))
        else:
            self.redirect("/login?error=You need to be logged, in order" +
                          " to create a post!")


class DeletePost(BlogHandler):

    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id))
        post = db.get(key)
        if post:
            if self.user:
                key = db.Key.from_path('Post', int(post_id))
                post = db.get(key)
                if post.user_id == self.user:
                    post.delete()
                    self.redirect("/blog?deleted_post_id=" + post_id)
                else:
                    self.redirect("/blog/" + post_id + "?error=You don't have " +
                                  "access to delete this record.")
            else:
                self.redirect("/login?error=You need to be logged, in order" +
                              " to delete your post!!")
        else:
            self.render("404.html")


class EditPost(BlogHandler):

    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id))
        post = db.get(key)
        if post:
            if self.user:
                if post.user_id == self.user:
                    self.render('editpost.html', subject=post.subject,
                                content=post.content)
                else:
                    self.redirect("/blog/" + post_id + "?error=You don't have " +
                                  "access to edit this post.")
            else:
                self.redirect("/login?error=You need to be logged, in order" +
                              " to edit this post!!")
        else:
            self.render("404.html")

    def post(self, post_id):
        key = db.Key.from_path('Post', int(post_id))
        post = db.get(key)
        if post:
            if not self.user:
                self.redirect("/blog")

            else:
                subject = self.request.get('subject')
                content = self.request.get('content')
                if subject and content:
                    key = db.Key.from_path(
                        'Post', int(post_id))
                    post = db.get(key)
                    post.subject = subject
                    post.content = content
                    post.put()
                    self.redirect("/blog/" + post_id)
                else:
                    msg = "Subject and content please!"
                    self.render('editpost.html', error=msg,
                                subject=subject, content=content)
        else:
            self.render("404.html")


class DeleteComment(BlogHandler):

    def get(self, post_id, comment_id):
        if self.user:
            key = db.Key.from_path('Comment', int(
                comment_id))
            c = db.get(key)
            if c.user_id == self.user:
                c.delete()
                time.sleep(0.1)
                self.redirect("/blog/" + post_id + "?deleted_comment_id=" +
                              comment_id)
            else:
                self.redirect("/blog/" + post_id + "?error=You don't have " +
                              "access to delete this comment.")
        else:
            self.redirect("/login?error=You need to be logged, in order to " +
                          "delete your comment!!")


class EditComment(BlogHandler):

    def get(self, post_id, comment_id):

        if self.user:
            key = db.Key.from_path('Comment', int(
                comment_id))
            c = db.get(key)
            if (c.user_id == self.user):
                self.render("editcomment.html", comment=c.comment)

            else:
                self.redirect("/blog/" + post_id + "?error=You don't have " +
                              "access to edit this comment.")

        else:
            self.redirect("/login?error=You need to be logged, in order to " +
                          "edit your comment!!")

    def post(self, post_id, comment_id):
        if not self.user:
            self.redirect('/blog')

        new_comment = self.request.get("comment")

        if new_comment:
            key = db.Key.from_path('Comment',
                                   int(comment_id))
            c = db.get(key)
            c.comment = new_comment
            c.put()
            time.sleep(0.1)
            self.redirect('/blog/%s' % post_id)
        else:
            error = "No blank comments, please!"
            self.render("editcomment.html", error=error)


class Profile(BlogHandler):

    def get(self, username):
        user = User.by_user_id(username)
        if (user):
            posts = db.GqlQuery(
                "select * from Post where user_id = :user", user=username)
            self.render('profile.html', posts=posts, profile=username)
        else:
            self.render('404.html')


class PostPage(BlogHandler):

    def get(self, post_id):
        key = db.Key.from_path('Post', int(post_id))
        post = db.get(key)
        likes = db.GqlQuery(
            "select * from Like where post_id = '%s'" % post_id)
        comments = db.GqlQuery(
            "select * from Comment where post_id = '%s' order by created desc" % post_id)

        if post:
            error = self.request.get('error')
            self.render('postpage.html', post=post,
                        error=error, noOfLikes=likes.count(), comments=comments)
        else:
            self.render("404.html")

    def post(self, post_id):
        key = db.Key.from_path('Post', int(post_id))
        post = db.get(key)
        comment = self.request.get('comment')
        like = self.request.get('like')

        if (self.user):
            # Adds comment
            if (comment != ""):
                c = Comment(user_id=self.user,
                            post_id=post_id,
                            comment=comment)
                c.put()

            # Adds like
            if(like and like == "update"):
                likes = db.GqlQuery(
                    "select * from Like where post_id = '%s' and user_id = '%s'" % (post_id, self.user))

                if self.user == post.user_id:
                    self.redirect("/blog/" + post_id +
                                  "?error=You cannot like your " +
                                  "post.!!")
                    return
                elif likes.count() == 0:
                    l = Like(user_id=self.user,
                             post_id=post_id)
                    l.put()

        else:
            self.redirect("/login?error=You need to login before " +
                          "performing edit, like or commenting.!!")
            return

        time.sleep(0.1)
        likes = db.GqlQuery(
            "select * from Like where post_id = '%s'" % post_id)
        comments = db.GqlQuery(
            "select * from Comment where post_id = '%s' order by created desc" % post_id)
        self.render("postpage.html", post=post,
                    comments=comments, noOfLikes=likes.count())


class BlogHome(BlogHandler):

    def get(self):
        deleted_post_id = self.request.get('deleted_post_id')
        posts = Post.all().order('-created')
        if (posts.count() == 0):
            self.render(
                "front.html", nopost="Oops! Sorry there are no posts to show :/", posts=posts, front=True)
        else:
            self.render('front.html', posts=posts,
                        deleted_post_id=deleted_post_id, front=True)


app = webapp2.WSGIApplication([
    ('/?', MainPage),
    ('/login', Login),
    ('/signup', SignUp),
    ('/logout', Logout),
    ('/blog', BlogHome),
    ('/blog/([0-9]+)', PostPage),
    ('/blog/profile/([a-zA-Z0-9_.-]+)', Profile),
    ('/blog/newpost', NewPost),
    ('/blog/editpost/([0-9]+)', EditPost),
    ('/blog/deletepost/([0-9]+)', DeletePost),
    ('/blog/([0-9]+)/deletecomment/([0-9]+)', DeleteComment),
    ('/blog/([0-9]+)/editcomment/([0-9]+)', EditComment),
], debug=True)
