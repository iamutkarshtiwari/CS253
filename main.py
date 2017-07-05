import webapp2
import jinja2
import os
import re
import hmac

from google.appengine.ext import db

from user import User
from post import Post

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
            self.user = User.by_id(int(uid)).user_id
        else:
            self.user = None


class MainPage(BlogHandler):

    def get(self):
        # self.render('home.html')
        self.redirect('/blog')

    def post(self):
        input_text = self.request.get('text')
        input_text = input_text.encode('rot13')


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
            self.redirect('/blog/%s' % username)
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
            self.redirect("/blog/%s" % self.user)
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
            u = User.register(username, password, email)
            u.put()

            self.login(u)
            self.redirect('/blog/%s' % username)


class NewPost(BlogHandler):

    def get(self, user_id):
        self.render('newpost.html')

    def post(self, user_id):
        subject = self.request.get('subject')
        content = self.request.get('content')
        if not (subject and content):
            self.render('newpost.html',
                        subject=subject, content=content, error="Subject and content, please!")
        else:
            postdata = Post(user_id=user_id,
                            subject=subject, content=content)
            postdata.put()
            self.redirect("/blog/%s/%s" %
                          (self.user, str(postdata.key().id())))


class DeletePost(BlogHandler):

    def get(self, user_id, post_id):
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
                    self.redirect("/blog/" + post.user_id + "/" + post_id + "?error=You don't have " +
                                  "access to delete this record.")
            else:
                self.redirect("/login?error=You need to be logged, in order" +
                              " to delete your post!!")
        else:
            self.render("404.html")


class EditPost(BlogHandler):

    def get(self, user_id, post_id):
        key = db.Key.from_path('Post', int(post_id))
        post = db.get(key)
        if post:
            if self.user:
                key = db.Key.from_path('Post', int(post_id))
                post = db.get(key)
                if post.user_id == self.user:
                    self.render('editpost.html', subject=post.subject,
                                content=post.content)
                else:
                    self.redirect("/blog/" + post.user_id + "/" + post_id + "?error=You don't have " +
                                  "access to edit this post.")
            else:
                self.redirect("/login?error=You need to be logged, in order" +
                              " to edit this post!!")
        else:
            self.render("404.html")

    def post(self, user_id, post_id):
        key = db.Key.from_path('Post', int(post_id))
        post = db.get(key)
        if post:
            if not self.user:
                self.redirect("/blog")

            else:
                subject = self.request.get('subject')
                content = self.request.get('content')
                if subject and content:
                    key = db.Key.from_path('Post', int(post_id))
                    post = db.get(key)
                    post.subject = subject
                    post.content = content
                    post.put()
                    self.redirect("/blog/" + post.user_id + "/" + post_id)
                else:
                    msg = "Subject and content please!"
                    self.render('editpost.html', error=msg,
                                subject=subject, content=content)
        else:
            self.render("404.html")


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

    def get(self, user_id, post_id):
        key = db.Key.from_path('Post', int(post_id))
        post = db.get(key)
        if post:
            error = self.request.get('error')
            self.render('postpage.html', post=post, error=error)
        else:
            self.render("404.html")


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
    ('/', MainPage),
    ('/login', Login),
    ('/signup', SignUp),
    ('/logout', Logout),
    ('/blog', BlogHome),
    ('/blog/([a-zA-Z0-9_.-]+)', Profile),
    ('/blog/([a-zA-Z0-9_.-]+)/([0-9]+)', PostPage),
    ('/blog/([a-zA-Z0-9_.-]+)/newpost', NewPost),
    ('/blog/([a-zA-Z0-9_.-]+)/editpost/([0-9]+)', EditPost),
    ('/blog/([a-zA-Z0-9_.-]+)/deletepost/([0-9]+)', DeletePost)
], debug=True)
