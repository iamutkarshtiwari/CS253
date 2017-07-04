# Copyright 2016 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import webapp2
import jinja2
import os
import re

from google.appengine.ext import db

jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader('templates'),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


def render_str(template, **params):
    params['username'] = "Utkarsh"
    t = jinja_env.get_template(template)
    return t.render(params)


class MainPage(webapp2.RequestHandler):

    def get(self):
        # self.response.write(render_str('main.html'))
        visits = int(self.request.cookies.get('visits', 0))

        visits += 1
        # self.response.headers.add_header('Set-Cookie', "visits=%s" % visits)
        self.response.write("You have been here %s times" % str(visits))

    def post(self):
        input_text = self.request.get('text')
        input_text = input_text.encode('rot13')

        # self.response.out.write(render_str('main.html', text=input_text))


class SignUp(webapp2.RequestHandler):

    def get(self):
        self.response.write(render_str('signup.html'))

    def post(self):
        self.validate()

    def validate(self):
        params = dict()
        username = self.request.get('username')
        password = self.request.get('pass')
        password_verify = self.request.get('verify_pass')
        email = self.request.get('email')
        is_error = False

        if not (username and (re.compile(r"^[a-zA-Z0-9_-]{3,20}$").match(username))):
            params['username_error'] = "That wasn't a valid username."
            is_error = True
        if not (password and (re.compile(r"^.{3,20}$").match(password))):
            params['password_error'] = "That wasn't a valid password."
            is_error = True
        elif password_verify != password:
            params['password_match_error'] = "The password did not match."
            is_error = True

        if email:
            if not(re.compile(r"^[\S]+@[\S]+.[\S]+$").match(email)):
                params['email_error'] = "That's not a valid email address."
                is_error = True

        if is_error:
            self.response.out.write(render_str('signup.html', **params))
        else:
            self.redirect('/welcome?username=' + username)


class Welcome(webapp2.RequestHandler):

    def get(self):
        username = self.request.get('username')
        self.response.write(render_str('welcome.html', username=username))


class Post(db.Model):
    subject = db.StringProperty(required=True)
    content = db.TextProperty(required=True)
    created = db.DateTimeProperty(auto_now_add=True)


class NewPost(webapp2.RequestHandler):

    def get(self):
        self.response.write(render_str('newpost.html'))

    def post(self):
        subject = self.request.get('subject')
        content = self.request.get('content')
        if not (subject and content):
            self.response.write(render_str('newpost.html',
                                           subject=subject, content=content, error="Subject and content, please!"))
        else:
            postdata = Post(subject=subject, content=content)
            postdata.put()
            self.redirect('/blog/%s' % str(postdata.key().id()))


class PostPage(webapp2.RequestHandler):

    def get(self, blog_id):
        key = db.Key.from_path('Post', int(blog_id))
        post = db.get(key)
        subject = post.subject
        content = post.content
        created = post.created
        self.response.out.write(render_str(
            'newpost.html', subject=subject, content=content, created=created))

    # def post(self, blog_id):
        # print blog_id


class Blog(webapp2.RequestHandler):

    def get(self):
        posts = db.GqlQuery(
            "select * from Post order by created desc limit 10")
        self.response.write(render_str("bloghome.html", posts=posts))


app = webapp2.WSGIApplication([
    ('/', MainPage), ('/signup', SignUp), ('/welcome',
                                           Welcome), ('/blog', Blog), ('/blog/newpost', NewPost), ('/blog/([0-9]+)', PostPage)
], debug=True)
