import json, requests
from flask import Flask, request, render_template, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from sqlalchemy.sql import text, or_
from datetime import datetime as DateTime


app = Flask(__name__)
socketio = SocketIO(app)

db_name = "chat.db"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_name

db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    email = db.Column(db.String)
    nickname = db.Column(db.String)


class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String)
    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    recipient_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    author = db.relationship("User", foreign_keys=[author_id], backref="sent_messages")
    recipient = db.relationship(
        "User", foreign_keys=[recipient_id], backref="received_messages"
    )
    date = db.Column(db.DateTime)


with app.app_context():
    db.create_all()


@socketio.on("connect-ack")
def connect_ack(message):
    print(f"received ACL message: {message} of type {type(message)}")


@app.route("/")
def hello_world():
    return redirect("/front/users")


@app.route("/db/alive")
def db_alive():
    try:
        result = db.session.execute(text("SELECT 1"))
        print(result)
        return dict(status="healthy", message="Databse connection is alive")
    except Exception as e:
        error_text = "<p>The error:<br>" + str(e) + "</p>"
        head = "<h1>Something is broken.</h1>"
        return head + error_text


@app.route("/api/users", methods=["POST"])
def create_user():
    try:
        parameters = json.loads(request.data)
        name = parameters["name"]
        email = parameters["email"]
        nickname = parameters["nickname"]
        print(name, email, nickname)
        new_user = User(name=name, email=email, nickname=nickname)
        db.session.add(new_user)
        db.session.commit()
        return parameters
    except Exception as e:
        return dict(error=f"{type(e)}: {e}"), 422


@app.route("/api/users", methods=["GET"])
def list_users():
    users = User.query.all()
    return [
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "nickname": user.nickname,
        }
        for user in users
    ]


@app.route("/api/users/<int:id>", methods=["GET"])
def user_detail(id):
    user = User.query.get(id)
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "nickname": user.nickname,
    }


@app.route("/api/messages", methods=["POST"])
def create_message():
    parameters = json.loads(request.data)
    message = Message(
        content=parameters["content"],
        author_id=parameters["author_id"],
        recipient_id=parameters["recipient_id"],
        date=DateTime.now(),
    )
    db.session.add(message)
    db.session.commit()

    recipient = User.query.get(message.recipient_id)
    author = User.query.get(message.author_id)

    parameters["author"] = {
        "id": author.id,
        "name": author.name,
        "email": author.email,
        "nickname": author.nickname,
    }
    parameters["recipient"] = {
        "id": recipient.id,
        "name": recipient.name,
        "email": recipient.email,
        "nickname": recipient.nickname,
    }
    parameters["date"] = message.date

    socketio.emit(recipient.nickname, json.dumps(parameters, default=str))
    socketio.emit(author.nickname, json.dumps(parameters, default=str))
    return parameters


@app.route("/api/users/<int:id>/messages", methods=["GET"])
def get_messages_for_user(id):
    messages = Message.query.filter(
        or_(Message.recipient_id == id, Message.author_id == id)
    ).all()
    return [
        {
            "id": message.id,
            "author": {
                "id": message.author.id,
                "name": message.author.name,
                "email": message.author.email,
                "nickname": message.author.nickname,
            },
            "recipient": {
                "id": message.recipient.id,
                "name": message.recipient.name,
                "email": message.recipient.email,
                "nickname": message.recipient.nickname,
            },
            "content": message.content,
            "date": message.date,
        }
        for message in messages
    ]


def parse_json_from(ressource):
    url = request.url_root + ressource
    req = requests.get(url)
    if not (200 <= req.status_code < 300):
        return dict(
            error=f"error while fetching API",
            url=url,
            status=req.status_code,
            text=req.text,
        )
    return req.json()


@app.route("/front/users", methods=["GET"])
def front_users():
    users = parse_json_from("api/users")
    return render_template("users.html", users=users)


@app.route("/front/users/<int:id>", methods=["GET"])
def front_user_detail(id):
    user = parse_json_from(f"api/users/{id}")
    messages = parse_json_from(f"api/users/{id}/messages")
    recipients = parse_json_from(f"api/users")
    return render_template(
        "messages.html", user=user, messages=messages, recipients=recipients
    )


if __name__ == "__main__":
    socketio.run()
