import webapp2
import jinja2
import os
import re

from google.appengine.ext import db

jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader('templates'),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


def jinja_render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)


class BlogHandler(webapp2.RequestHandler):

    def initialize(self, *a, **kw):
        """
            This methods gets executed for each page and
            verfies user login status, using cookie information.
        """
        webapp2.RequestHandler.initialize(self, *a, **kw)
        # uid = self.read_secure_cookie('user_id')
        # self.user = uid and User.by_id(int(uid))
        self.username = 'iamutkarsh'

    def write(self, *a, **kw):
        """
            This methods write output to client browser.
        """
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        """
            This methods renders html using template.
        """
        params['username'] = self.username
        return jinja_render_str(template, **params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def login(self, username):
        self.username = username


class MainPage(BlogHandler):

    def get(self):
        # self.response.write(render_str('main.html'))
        visits = int(self.request.cookies.get('visits', 0))

        visits += 1
        # self.response.headers.add_header('Set-Cookie', "visits=%s" % visits)
        # self.response.write("You have been here %s times" % str(visits))
        self.render('front.html')

    def post(self):
        input_text = self.request.get('text')
        input_text = input_text.encode('rot13')

        # self.response.out.write(render_str('main.html', text=input_text))


class Login(BlogHandler):

    def get(self):
        self.render('login-form.html')

    def post(self):
        pass


class Logout(BlogHandler):

    def get(self):
        pass

    def post(self):
        pass


class EditPost(BlogHandler):

    def get(self):
        pass

    def post(self):
        pass


class SignUp(BlogHandler):

    def get(self):
        self.response.write(render_str('signup-form.html'))

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
            self.login(username)
            self.redirect('/welcome?username=' + username)


class Profile(BlogHandler):

    def get(self, username):
        posts = db.GqlQuery(
            "select * from Post where user_id = :user", user=username)

        # myResult = db.GqlQuery(
        #     "SELECT * FROM Posts WHERE filter = :user", user=username)
        self.render('user.html', username=username, posts=posts)


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

    # def getUserName(self):
    #     """
    #         Gets username of the person, who wrote the blog post.
    #     """
    #     user = User.by_id(self.user_id)
    #     return user.name

    # def render(self):
    #     """
    #         Renders the post using object data.
    #     """
    #     self._render_text = self.content.replace('\n', '<br>')
    #     return jinja_render_str("permalink.html", p=self)


class NewPost(BlogHandler):

    def get(self, user_id):
        self.render('newpost.html')

    def post(self, user_id):
        user_id = self.username
        subject = self.request.get('subject')
        content = self.request.get('content')
        if not (subject and content):
            self.render('newpost.html',
                        subject=subject, content=content, error="Subject and content, please!")
        else:
            postdata = Post(user_id=user_id,
                            subject=subject, content=content)
            postdata.put()
            self.redirect("/blog/" + user_id + "/" + str(postdata.key().id()))


class DeletePost(BlogHandler):

    def get(self, user_id, post_id):
        if user_id:
            key = db.Key.from_path('Post', int(post_id))
            post = db.get(key)
            if post.user_id == user_id:
                post.delete()
                self.redirect("/blog?deleted_post_id=" + post_id)
            else:
                self.redirect("/blog/" + post_id + "?error=You don't have " +
                              "access to delete this record.")
        else:
            self.redirect("/login?error=You need to be logged, in order" +
                          " to delete your post!!")


class EditPost(BlogHandler):

    def get(self, user_id, post_id):
        pass

    def post(self):
        pass


class PostPage(BlogHandler):

    def get(self, user_id, blog_id):
        key = db.Key.from_path('Post', int(blog_id))
        post = db.get(key)
        self.render('postpage.html', post=post)

    # def post(self, blog_id):
    #     pass


class BlogHome(BlogHandler):

    def get(self):
        deleted_post_id = self.request.get('deleted_post_id')
        posts = Post.all().order('-created')
        posts = db.GqlQuery(
            "select * from Post order by created desc limit 10")

        if (posts.count() == 0):
            self.render(
                "front.html", nopost="Oops! Sorry there are no posts to show :/", posts=posts)
        else:
            self.render('front.html', posts=posts,
                        deleted_post_id=deleted_post_id)


app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/login', Login),
    ('/signup', SignUp),
    ('/logout', Logout),
    ('/blog', BlogHome),
    ('/blog/([a-zA-Z0-9_.-]+)/([0-9]+)', PostPage),
    ('/blog/([a-zA-Z0-9_.-]+)', Profile),
    ('/blog/([a-zA-Z0-9_.-]+)/newpost', NewPost),
    ('/blog/([a-zA-Z0-9_.-]+)/editpost/([0-9]+)', EditPost),
    ('/blog/([a-zA-Z0-9_.-]+)/deletepost/([0-9]+)', DeletePost)
], debug=True)
