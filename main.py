from flask import Flask, render_template, request, url_for, make_response, redirect, flash
import sys, os, time
import bcrypt, random
import goatfish, sqlite3

app = Flask(__name__)
app.secret_key = 'ads32304djlsf238mkndfi8320df'
sessions = {}

class Project(goatfish.Model):
    class Meta:
        connection = sqlite3.connect("./data.db", check_same_thread = False)
        indexes = (
            ("pid",),
            ("pid", "name", "desc", "url", "git", "builds", "downloads"),
        )
Project.initialize()

class Build(goatfish.Model):
    class Meta:
        connection = sqlite3.connect("./data.db", check_same_thread = False)
        indexes = (
            ("bid",),
            ("bid", "project", "data", "built", "success"),
        )
Build.initialize()

# project = Project()
# project.pid = 1
# project.name = "SWiSH"
# project.desc = "An improved ioquake3/Urban Terror build created by Strata (mirrored by Neek)"
# project.url = "https://github.com/spekode/SWiSH_ioUrT"
# project.git = "git://github.com/spekode/SWiSH_ioUrT.git"
# project.builds = []
# project.downloads = 0
# project.save()

def getProjects():
    a = []
    for i in Project.find():
        g, b = 0, 0
        for x in i.builds:
            for y in Build.find({'bid':x}):
                if y.built:
                    if y.success: g += 1
                    else: b += 1
        a.append({'pid':i.pid, 'name':i.name, 'desc':i.desc, 'buildcount':[g,b]})
    return a

@app.route('/')
def index():
    return actionIndex() 

@app.route('/project/')
@app.route('/project/<pid>/')
def projectView(pid=None):
    if pid:
        if pid.isdigit(): return "Blah %s | %s" % (pid, action)
        flash('The project you requested does not exsist!')
        return redirect(url_for('index'))
    else: return actionProjects()

@app.route('/project/<pid>/builds/')
@app.route('/project/<pid>/builds/<bid>')
def buildView(pid=None, bid=None): pass

@app.route('/builds/')
def buildsView():
    return render_template('build.html', builds=[i for i in Build.find()], projects=[i for i in Project.find()])

def actionProjects(): pass

def actionIndex():
    data = {
    'projects':getProjects()
    }
    data.update(cached_stats)
    return render_template('index.html', data=data)

@app.route('/api/<action>/', methods=['GET', 'POST'])
def api(action=None):
    if action == "gitty":
        print request.args.keys()

if __name__ == '__main__':
    q =  [i for i in Build.find()]
    p_count = len([i for i in Project.find()])
    b_count = [len([i for i in q if i.success]), len([i for i in q if not i.success])]
    b_count.append(sum(b_count))
    d_count = sum([i.downloads for i in Project.find()])
    cached_stats = {
    'num_projects':p_count,
    'num_builds':b_count,
    'num_downloads':d_count,
    }
    app.run(debug=True, host='0.0.0.0')
