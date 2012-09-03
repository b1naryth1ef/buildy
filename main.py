from flask import Flask, render_template, request, url_for, make_response, redirect, flash
import sys, os, time, random
from database import Project, Build

app = Flask(__name__)
app.secret_key = 'ads32304djlsf238mkndfi8320df'
sessions = {}
statsc = None

class Obby():
    def __init__(self, info={}):
        self.__dict__.update(info)

def getStats():
    global statsc
    if not statsc: 
        statsc = Obby()
        statsc.rebuild = True
    if getattr(statsc, 'rebuild', False):
        statsc.total_builds = 0
        statsc.total_projects = len([i for i in Project.select()])
        statsc.total_downloads = 0
        statsc.total_win = 0
        statsc.total_fail = 0
        for i in Build.select():
            statsc.total_builds += 1
            if i.success: statsc.total_win += 1
            else: statsc.total_fail += 1
            statsc.total_downloads += i.downloads
    return statsc

@app.route('/')
def index():
    v = Obby()
    v.stats = getStats()
    v.title = "Home"
    v.projects = [i for i in Project.select().where(active=True)]
    return render_template('index.html', v=v)

@app.route('/project/<pid>/')
def projectView(pid=None):
    if pid and pid.isdigit() or isinstance(pid, int):
        q = [i for i in Project.select().where(id=int(pid))]
        if len(q):
            return "Yay!"
        else: flash('No project with ID #%s' % pid)
    else: flash('The project ID is invalid!')
    return redirect(url_for('index'))

@app.route('/builds/')
@app.route('/build/<bid>')
@app.route('/build/p/<pid>')
@app.route('/build/dl/<did>')
def buildView(pid=None, bid=None, did=None): pass

def createBuild(): pass

@app.route('/api/<action>/', methods=['POST'])
def api(action=None):
    if action == "github":
        print request.form.keys()
    elif action == "gitlab":
        print request.form.keys()
        print request.args.keys()
        print request.data
        print request.json
    elif action == "buildfin":
        print request.form.keys()
    else: pass

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
