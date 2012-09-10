from flask import Flask, render_template, request, url_for, make_response, redirect, flash
import sys, os, time, random, socket, json
from database import Project, Build, Commit
from werkzeug import secure_filename
import redis

app = Flask(__name__)
app.secret_key = 'ads32304djlsf238mkndfi8320df'
sessions = {}
statsc = None
build_servers = ['127.0.0.1']

THIS_URL = "build.hydr0.com"
BUILD_DIR = "/var/www/buildy/builds/"
REDIS = redis.StrictRedis()
#PUB = REDIS.pubsub()

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
        statsc.total_building = 0
        statsc.total_projects = len([i for i in Project.select()])
        statsc.total_downloads = 0
        statsc.total_win = 0
        statsc.total_fail = 0
        for i in Build.select():
            statsc.total_builds += 1
            if i.finished:
                if i.success: statsc.total_win += 1
                else: statsc.total_fail += 1
            else:
                statsc.total_building += 1
            statsc.total_downloads += i.downloads or 0
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
            v.builds = list(reversed([i for i in Build.select().where(project=q[0])]))
            return render_template('project.html', p=q[0], v=v)
        else: flash('No project with ID #%s' % pid)
    else: flash('The project ID is invalid!')
    return redirect(url_for('index'))

def runBuild(b):
    print 'Adding build to queue!'
    info = json.dumps({
        'projid':b.project.id,
        'dir':b.project.name,
        'bid':b.bnum,
        'jobid':b.id,
        'bcode':b.code
        })
    REDIS.publish('buildyjobs', info)

def saveBuild(b, f):
    proj_dir = os.path.join(BUILD_DIR, b.project.name)
    if not os.path.exists(proj_dir): os.mkdir(proj_dir)
    build_dir = os.path.join(BUILD_DIR, proj_dir, b.bnum)
    if not os.path.exists(build_dir): os.mkdir(build_dir)
    f.save(os.path.join(build_dir, f.filename))
    return os.path.join(THIS_URL, 'builds', b.project.name, b.bnum)

def findStalled():
    q = [i for i in Build.select().where(finished=False) if time.time()-i.created >= 600]
    if len(q):
        print "Removing %s stalled builds!" % len(q)
        for i in q:
            i.finished = True
            i.success = False
            i.result = "Build timed out!"
            i.project.b_fail += 1
            i.project.save()
            i.save()

@app.route('/api/<action>/', methods=['POST'])
def api(action=None):
    global statsc
    statsc.rebuild = True 
    if action == "github":
        print request.form.keys()
        print request.json
    elif action == "gitlab":
        findStalled()
        d = request.json
        q = [i for i in Project.select().where(repo_name=d['repository']['name'], active=True)]
        if len(q):
            binc = max([i.bnum for i in Build.select().where(project=q[0])] or [0])+1
            c = Commit.create(
                info=d['commits'][-1]['message'],
                by=d['commits'][-1]['author']['name'],
                url=d['commits'][-1]['url'].split('http://hydr0.com')[-1],
                sha=d['commits'][-1]['id'][:9])
            b = Build.create(
                    created=time.time(),
                    project=q[0], 
                    bnum=binc, 
                    code=random.randint(1000, 9999),
                    commit=c)
            runBuild(b)
        else:
            print 'Invalid build info!', d, q
    elif action == "buildfin":
        b = [i for i in Build.select().where(id=request.form['bid'], code=request.form['bcode'])]

        f = request.files.get('build')
        if not f or not f.filename.endswith('.tar.gz'):
            print "Invalid file!"

        if len(b):
            b = b[0]
            url = 'http://'+saveBuild(b, f)
            if b.finished == True: return ":3" #Cross compile stuffs
            b.finished = True
            b.success = bool(int(request.form['success']))
            b.result = request.form['result']
            b.time = request.form['time']
            if b.success:
                b.burl = url
                b.project.b_win += 1
            else: 
                b.project.b_fail += 1
            b.project.save()
            b.save()
        else:
            print 'Invalid build!'
    else: pass
    return ":3"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=9013)
