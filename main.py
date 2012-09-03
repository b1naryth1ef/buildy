from flask import Flask, render_template, request, url_for, make_response, redirect, flash
import sys, os, time, random, socket, json
from database import Project, Build

app = Flask(__name__)
app.secret_key = 'ads32304djlsf238mkndfi8320df'
sessions = {}
statsc = None
buildinc = max([i.bnum for i in Build.select()] or [0])
build_servers = ['127.0.0.1']

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
getStats()

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
            v = Obby()
            v.stats = getStats()
            v.title = "%s" % q[0].name
            return render_template('project.html', p=q[0], v=v)
        else: flash('No project with ID #%s' % pid)
    else: flash('The project ID is invalid!')
    return redirect(url_for('index'))

def runBuild(b):
    print 'Sending build to worker...',
    c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    c.connect((random.choice(build_servers), 7660))
    c.send(json.dumps({
        'a':'build',
        'id':b.project.id,
        'job':b.bnum,
        'bcode':b.code
        }))
    c.close()
    print 'SENT!'

@app.route('/api/<action>/', methods=['POST'])
def api(action=None):
    global buildinc, statsc
    if action == "github":
        print request.form.keys()
        print request.json
    elif action == "gitlab":
        d = request.json
        q = [i for i in Project.select().where(repo_name=d['repository']['name'], active=True)]
        if len(q):
            buildinc += 1
            b = Build.create(project=q[0], bnum=buildinc, code=random.randint(1000, 9999))
            runBuild(b)
        else:
            print 'Invalid build info!', d, q
    elif action == "buildfin":
        b = [i for i in Build.select().where(bnum=request.form['bid'], code=request.form['bcode'])]
        if not len(b):
            print 'Invalid build!'
        else:
            b[0].finished = True
            b[0].success = bool(request.form['success'])
            if b[0].success:
                b[0].burl = request.form['result']
                b[0].project.b_win += 1
            else:
                b[0].project.b_fail += 1
            b[0].project.save()
            b[0].save()
        statsc.rebuild = True 
    else: pass
    return ":3"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
