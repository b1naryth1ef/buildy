from flask import Flask, render_template, request, url_for, make_response, redirect, flash
import sys, os, time, random, socket, json
from database import Project, Build
from werkzeug import secure_filename

app = Flask(__name__)
app.secret_key = 'ads32304djlsf238mkndfi8320df'
sessions = {}
statsc = None
build_servers = ['127.0.0.1']

THIS_URL = "build.hydr0.com"
BUILD_DIR = "/var/www/buildy/builds/"
REDIS = redis.StrictRedis()
PUB = redis.pubsub()

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
            v.builds = list(reversed([i for i in Build.select().where(project=q[0])]))
            return render_template('project.html', p=q[0], v=v)
        else: flash('No project with ID #%s' % pid)
    else: flash('The project ID is invalid!')
    return redirect(url_for('index'))

def runBuild(b):
    print 'Adding build to queue!'
    PUB.publish('buildyjobs', json.dumps({
        'a':'build',
        'id':b.project.id,
        'dir':b.project.name,
        'job':b.id,
        'bcode':b.code
        }))
    # print 'Sending build to worker...',
    # c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # c.connect((random.choice(build_servers), 7660))
    # c.send(json.dumps({
    #     'a':'build',
    #     'id':b.project.id,
    #     'dir':b.project.name,
    #     'job':b.id,
    #     'bcode':b.code
    #     }))
    # c.close()
    # print 'SENT!'

def saveBuild(pname, f):
    p = os.path.join(BUILD_DIR, pname)
    if not os.path.exists(p):
        os.mkdir(p)
    f.save(os.path.join(p, f.filename))
    return os.path.join(THIS_URL, pname, f.filename)

@app.route('/api/<action>/', methods=['POST'])
def api(action=None):
    global statsc
    statsc.rebuild = True 
    if action == "github":
        print request.form.keys()
        print request.json
    elif action == "gitlab":
        d = request.json
        q = [i for i in Project.select().where(repo_name=d['repository']['name'], active=True)]
        if len(q):
            binc = max([i.bnum for i in Build.select().where(project=q[0])] or [0])+1
            b = Build.create(
                    project=q[0], 
                    bnum=binc, 
                    code=random.randint(1000, 9999),
                    commit=d['commits'][-1]['message'],
                    commit_by=d['commits'][-1]['author']['name'],
                    commit_url=d['commits'][-1]['url'].split('http://hydr0.com')[-1])
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
            url = 'http://'+saveBuild(b.project.name, f)
            b.finished = True
            b.success = bool(int(request.form['success']))
            b.result = request.form['result']
            if b.success:
                b.burl = url
                b.project.b_win += 1
            else: b.project.b_fail += 1
            b.project.save()
            b.save()
        else:
            print 'Invalid build!'
    else: pass
    return ":3"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=9013)
