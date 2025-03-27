"""
new POST endpoint /api/messages to create a message
"""

import json
from datetime import datetime as DateTime
import requests

from flask import Flask
from flask import request
from flask import render_template
from flask import redirect

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import text

VERSION = "07"

## usual Flask initilization
app = Flask(__name__)

## DB declaration

# filename where to store stuff (sqlite is file-based)
db_name = 'chat.db'
# how do we connect to the database ?
# here we say it's by looking in a file named chat.db
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_name
# this variable, db, will be used for all SQLAlchemy commands
db = SQLAlchemy(app)


## define a table in the database

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    email = db.Column(db.String)
    nickname = db.Column(db.String)

class Message(db.Model):
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    date = db.Column(db.DateTime)


# actually create the database (i.e. tables etc)
with app.app_context():
    db.create_all()


@app.route('/')
def hello_world():
    # redirect to /front/users
    # actually this is just a rsponse with a 301 HTTP code
    return redirect('/front/users')


# try it with
"""
http :5001/db/alive
"""
@app.route('/db/alive')
def db_alive():
    try:
        result = db.session.execute(text('SELECT 1'))
        print(result)
        return dict(status="healthy", message="Database connection is alive")
    except Exception as e:
        # e holds description of the error
        error_text = "<p>The error:<br>" + str(e) + "</p>"
        hed = '<h1>Something is broken.</h1>'
        return hed + error_text


# try it with
"""
http :5001/api/version
"""
@app.route('/api/version')
def version():
    return dict(version=VERSION)


# try it with
"""
http :5001/api/users name="Alice Caroll" email="alice@foo.com" nickname="alice"
http :5001/api/users name="Bob Morane" email="bob@foo.com" nickname="bob"
"""
@app.route('/api/users', methods=['POST'])
def create_user():
    # we expect the user to send a JSON object
    # with the 3 fields name email and nickname
    try:
        parameters = json.loads(request.data)
        name = parameters['name']
        email = parameters['email']
        nickname = parameters['nickname']
        print("received request to create user", name, email, nickname)
        # temporary
        new_user = User(name=name, email=email, nickname=nickname)
        db.session.add(new_user)
        db.session.commit()
        return parameters
    except Exception as exc:
        return dict(error=f"{type(exc)}: {exc}"), 422


# try it with
"""
http :5001/api/users
"""
@app.route('/api/users', methods=['GET'])
def list_users():
    users = User.query.all()
    return [dict(
            id=user.id, name=user.name, email=user.email, nickname=user.nickname)
        for user in users]


# try it with
"""
http :5001/api/users/1
"""
@app.route('/api/users/<int:id>', methods=['GET'])
def list_user(id):
    try:
        # as id is the primary key
        user = User.query.get(id)
        return dict(
            id=user.id, name=user.name, email=user.email, nickname=user.nickname)
    except Exception as exc:
        return dict(error=f"{type(exc)}: {exc}"), 422


# try it with
"""
http :5001/api/messages author_id=1 recipient_id=2 content="trois petits chats"
http :5001/api/messages author_id=2 recipient_id=1 content="chapeau de paille"
http :5001/api/messages author_id=1 recipient_id=2 content="paillasson"
http :5001/api/messages author_id=2 recipient_id=1 content="somnambule"
http :5001/api/messages author_id=1 recipient_id=2 content="bulletin"
http :5001/api/messages author_id=2 recipient_id=1 content="tintamarre"
"""
@app.route('/api/messages', methods=['POST'])
def create_message():
    try:
        parameters = json.loads(request.data)
        content = parameters['content']
        author_id = parameters['author_id']
        recipient_id = parameters['recipient_id']
        date = DateTime.now()
        new_message = Message(content=content, date=date,
                              author_id=author_id, recipient_id=recipient_id)
        db.session.add(new_message)
        db.session.commit()
        return parameters
    except Exception as exc:
        return dict(error=f"{type(exc)}: {exc}"), 422



## Frontend
# for clarity we define our routes in the /front namespace
# however in practice /front/users would probably be just /users

# try it by pointing your browser to
""""
http://localhost:5001/front/users
"""
@app.route('/front/users')
def front_users():
    # first option of course, is to get all users from DB
    # users = User.query.all()
    # but in a more fragmented architecture we would need to
    # get that info at another endpoint
    # here we ask ourselves on the /api/users route
    url = request.url_root + '/api/users'
    req = requests.get(url)
    if not (200 <= req.status_code < 300):
        # return render_template('errors.html', error='...')
        return dict(error=f"could not request users list", url=url,
                    status=req.status_code, text=req.text)
    users = req.json()
    return render_template('users.html.j2', users=users, version=VERSION)


if __name__ == '__main__':
    app.run()
