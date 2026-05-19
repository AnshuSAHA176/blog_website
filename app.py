from __future__ import annotations
from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash,request
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor

from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
from typing import List
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
from wtforms.validators import email
from forms import CreatePostForm,RegisterForm,LoginForm,Comment_form
from hashlib import md5
import os
import hashlib
import smtplib
# "anshusahaa62@gmail.com"
MY_EMAIL=os.environ.get("my_email")
PASSWORD=os.environ.get("password")
login_manager = LoginManager()


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY', 'temporary-test-key')
ckeditor = CKEditor(app)
Bootstrap5(app)
@app.template_filter('md5')
def md5_filter(string):
    return hashlib.md5(string.encode()).hexdigest()
# TODO: Configure Flask-Login
login_manager.init_app(app)

  
@login_manager.user_loader

def load_user(user_id):
    return db.get_or_404(Users, user_id)

# CREATE DATABASE
class Base(DeclarativeBase):
    pass
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///posts.db")

db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CONFIGURE TABLES

class Users(UserMixin, db.Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    email: Mapped[str] = mapped_column(
        String(250),
        unique=True,
        nullable=False
    )

    passward: Mapped[str] = mapped_column(
        String(250),
        nullable=False
    )

    full_name: Mapped[str] = mapped_column(
        String(250),
        nullable=False
    )

    posts: Mapped[List["BlogPost"]] = relationship(
        back_populates="author"
    )
    comments:Mapped[List["Comment"]]=relationship(back_populates="author")
class BlogPost(db.Model):
    __tablename__ = "blog_posts"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    title: Mapped[str] = mapped_column(
        String(250),
        unique=True,
        nullable=False
    )

    subtitle: Mapped[str] = mapped_column(
        String(250),
        nullable=False
    )

    date: Mapped[str] = mapped_column(
        String(250),
        nullable=False
    )

    body: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    img_url: Mapped[str] = mapped_column(
        String(250),
        nullable=False
    )

    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )
    author: Mapped["Users"] = relationship(
    back_populates="posts"
)
    

    comments: Mapped[List["Comment"]] = relationship(
    back_populates="parent_post"
)
   
class Comment(db.Model):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

    post_id: Mapped[int] = mapped_column(
        ForeignKey("blog_posts.id")
    )

    author: Mapped["Users"] = relationship(
        back_populates="comments"
    )

    parent_post: Mapped["BlogPost"] = relationship(
        back_populates="comments"
    )

with app.app_context():
    db.create_all()

@app.route("/commnts/<int:post_id>",methods=['GET','POST'])
def add_comments(post_id):
    if not current_user.is_authenticated:
        flash("You need to login or ragister first")
        return redirect(url_for('login'))
    requested_post = db.get_or_404(BlogPost, post_id)
    form=Comment_form()
    if form.validate_on_submit():
        new_comment=Comment(
            text=form.body.data,
            author=current_user,
            parent_post=requested_post
        )
        db.session.add(new_comment)
        db.session.commit()
    return redirect(url_for('show_post',post_id=post_id))
    
# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register',methods=['GET','POST'])
def register():
    form=RegisterForm()
    if request.method =="POST":
        hash_password=generate_password_hash(request.form['passward'], method='pbkdf2:sha256', salt_length=16)
        if form.validate_on_submit():
            new_user=Users(
                email=request.form['email'],
                passward=hash_password,
                full_name=request.form['full_name']


            )
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('get_all_posts'))
    return render_template("register.html",form=form)


# TODO: Retrieve a user from the database based on their email. 
@app.route('/login',methods=['GET','POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user=db.session.execute(db.select(Users).where(Users.email==form.email.data)).scalar()
        if not user:
            flash("Email does not exist.")
            print("EMAIL")
            return redirect(url_for('login'))
            
        
        elif not check_password_hash(user.passward,form.passward.data):
                print("PASSWARD")
                flash("Incorrect password.")
                return redirect(url_for('login'))
        else:
            login_user(user)

            flash('Logged in successfully.')
            print("login")
            return redirect(url_for('get_all_posts'))
    return render_template("login.html",form=form)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    
    

    logout_user()

    flash("Logged out successfully.")

    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
   
    
    posts = result.scalars().all()
    return render_template("index.html", all_posts=posts,current_user=current_user)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>")
def show_post(post_id):

    form = Comment_form()
    requested_post = db.get_or_404(BlogPost, post_id)

    return render_template(
        "post.html",
        post=requested_post,
        current_user=current_user,
        form=form
    )
def admin_only(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

      

        if not current_user.is_authenticated or current_user.id !=1:
            return abort(403)

        return f(*args, **kwargs)

    return decorated_function





# TODO: Use a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    else:
        print("FORM ERRORS:", form.errors)
    return render_template("make-post.html", form=form,current_user=current_user)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))
    return render_template("make-post.html", form=edit_form, is_edit=True,current_user=current_user)


# TODO: Use a decorator so only an admin user can delete a post

@app.route("/delete/<int:post_id>",methods=["GET", "POST"])
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact",methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        # Handle form submission
        name=request.args.get("name")
        email_address=request.args.get("email")
        phone_number=request.args.get("phone")
        message=request.args.get("message")
        
        send_message=f"""
name: {name},

email: {email_address},

phone number: {phone_number},

message: {message}
"""
        connection=smtplib.SMTP("smtp.gmail.com",587)
        connection.starttls()
        connection.login(user=MY_EMAIL,password=PASSWORD)
        connection.sendmail(from_addr=MY_EMAIL,to_addrs=MY_EMAIL,msg=f"subject:contact news\n\n{send_message}")

    return render_template("contact.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))