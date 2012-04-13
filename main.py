import sys, os, time
from flask import Flask, render_template, request, url_for, make_response, redirect
from mongoengine import *
import bcrypt, random

app = Flask(__name__)
sessions = {}

connect('buildy', username='admin', password=sys.argv[1], host='hydr0.com')

class User(Document):
    username = StringField(required=True)
    password = StringField(required=True)
    data = DictField()

class Project(Document):
    pid = IntField()
    owner = IntField()
    url = URLField()
    git = StringField()
    builds = ListField()

class Build(Document):
    bid = IntField()
    owner = IntField()
    project = IntField()
    data = DictField()

if not User.objects(username="b1naryth1ef"):
    print 'adding'
    u = User(username="b1naryth1ef", password='1234')
    u.save()
# else:
#     for i in User.objects(username="b1naryth1ef"):
#         i.delete()
#     sys.exit()

@app.route('/')
def root():
    return "Hello world!"

@app.route('/login/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.objects(username=request.form['login'].lower())
        if user != None:
            if len(user) == 1:
                if request.form['password'] == user[0].password:
                    sid = random.randint(111111,999999)
                    resp = make_response(render_template('login.html', win=True))
                    sessions[user[0].username] = sid
                    resp.set_cookie('user', user[0].username)
                    resp.set_cookie('sessid', sid)
                    return resp
        return render_template('login.html', error="Bad login!")
    else:
        return render_template('login.html', error='')

@app.route('/admin/')
def adminindex():
    return redirect(url_for('admin', action='index'))

@app.route('/admin/<action>')
def admin(action=None):
    if 'sessid' in request.cookies.keys():
        s = request.cookies.get('sessid')
        u = request.cookies.get('user')
        if u in sessions.keys():
            print sessions[u], s
            if str(sessions[u]) == s:
                if action == 'index': return actionIndex()
                    
    return redirect(url_for('login'))

def actionIndex():
    data = {
    'num_builds':100,
    'num_projects':1245,
    'num_users':8543,
    'user':'B1naryth1ef'
    }
    return render_template('index.html', data=data)

@app.route('/api/<action>', methods=['GET', 'POST'])
def api(action=None): pass

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
