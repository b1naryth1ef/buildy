from flask import Flask, render_template, request, url_for, make_response, redirect, flash, session
import sys, os, time, random, socket, json
from database import Project, Build, Commit, User
from werkzeug import secure_filename
from datetime import datetime
import redis, bcrypt

app = Flask(__name__)
app.secret_key = 'ads32304djlsf238mkndfi8320df'

THIS_URL = "build.hydr0.com"
BUILD_DIR = "/var/www/buildy/builds/"
REDIS = redis.StrictRedis()

class Obj():
    def __init__(self, info={}):
        self.__dict__.update(info)

def loggedIn():
    if session.get('logged'): return True
    return False

def getView():
    v = Obj()
    v.title = "Home"
    v.loggedin = loggedIn()
    v.projects = [i for i in Project.select().where(Project.active == True)]
    v.stat_total_builds = len([i for i in Build.select().where(Build.built==True)])
    v.stat_total_projects = len(v.projects)
    v.stat_total_downloads = 0
    v.stat_total_success = len([i for i in Build.select().where((Build.built==True) & (Build.success==True))])
    v.stat_total_failure = len([i for i in Build.select().where((Build.built==True) & (Build.success==False))])
    return v

def flashy(loc, msg, err):
    flash(msg, err)
    return redirect(loc)

# VIEWS (people see this)
@app.route('/')
def index():
    v = getView()
    return render_template('index.html', v=v)

@app.route('/project/<id>')
def projectView(id=None):
    if not id: redirect('/')
    v = getView()
    q = [i for i in Project.select().where(Project.id == id)]
    if not len(q): return flashy('/', "No project with ID #%s" % id, 'error')
    v.proj = q[0]
    return render_template('project.html', v=v)

@app.route('/build/<id>')
def buildView(id=None):
    v = getView()
    if not id: redirect('/')
    q = [i for i in Build.select().where(Build.id==id)]
    if not len(q):
        return flashy('/', 'No build with ID #%s' % id, 'error')
    v.build = q[0]
    return render_template('build.html', v=v)

@app.route('/admin')
def adminView():
    if not loggedIn():
        return flashy('/', 'You must be logged in to do that!', 'error')
    v = getView()
    return render_template('admin.html', v=v)

# ROUTES (post calls)
@app.route('/api/<action>', methods=['POST'])
def apiRoute(action=None):
    if action == 'put_build':
        print request.form
    if action == 'gitlab':
        d = request.json
        q = [i for i in Project.select().where((Project.repo_name==request.json['repository']['name']) &(Project.active==True))]
        if len(q):
            commits = []
            for i in request.json['commits']:
                if len([i for i in Commit.select().where((Commit.sha==i['id'][:6]))]): continue
                c = Commit(
                    project=q[0],
                    info=i['message'],
                    author=i['author']['name'],
                    url=i['url'].split('http://hydr0.com')[-1]),
                    sha=i['id'][:6])
                c.save()
                commits.append(c)
            b = Build(
                project=q[0],
                commit=commits[-1],
                build_id=q[0].getBuildId(),
                built=False,
                time=datetime.now())
            b.save()
            addBuild(b)
        else:
            print 'Invalid build info!', d, q
    return ':3'

@app.route('/admin_action/<action>', methods=['POST'])
@app.route('/admin_action/<action>/<id>')
def adminActionRoute(action=None, id=None):
    if not loggedIn():
        return flashy('/', 'You must be logged in to do that!', 'error')
    if not action:
        return flashy('/', 'There was an error processing your request!', 'error')
    if not request.form.get('isact') and not id or id and not id.isdigit(): #Best ifstatement EVAR
        return flashy('/', 'Invalid or maliformed request!', 'error')
    if action == 'delete_proj':
        q = [i for i in Project.select().where(Project.id == int(id))]
        if not len(q):
            return flashy('/', 'Invalid Project ID (%s)' % id, 'error')
        q[0].delete_instance()
        return flashy('/', 'Deleted Project #%s!' % id, 'success')
    elif action == 'add_proj':
        q = [i for i in Project.select().where(Project.name == request.form.get('pname'))]
        if len(q): return flashy('/admin', 'There is already a project with the name "%s"' % request.form.get('pname'), 'error')
        p = Project(
            name=request.form.get('pname'),
            author=User.get(User.id==session.get('uid')),
            desc=request.form.get('pdesc'),
            url=request.form.get('purl'),
            repo_type=request.form.get('repotype'),
            repo_name=request.form.get('pgitname'),
            repo_url=request.form.get('giturl'))
        p.save()
        return flashy('/admin', 'Added project "%s" (ID #%s)' % (p.name, p.id), 'success')

@app.route('/login', methods=['POST'])
def loginRoute():
    if not 'user' in request.form.keys() or not 'pw' in request.form.keys():
        return flashy('/', 'All fields must be filled in!', 'error')
    q = [i for i in User.select().where(User.username == request.form.get('user'))]
    if not len(q):
        return flashy('/', 'No such user with that name!', 'error')
    if bcrypt.hashpw(request.form.get('pw'), q[0].password) == q[0].password:
        session['logged'] = True
        session['uid'] = q[0].id
        return flashy('/', 'You have been logged in!', 'success')
    return flashy('/', 'Invalid password!', 'error')

@app.route('/logout')
def logoutRoute():
    del session['logged']
    del session['uid']
    return flashy('/', 'You have been logged out!', 'success')

def addBuild(b):
    info = json.dumps({
            'pid':b.project.id,
            'id':b.id,
            'git':b.project.repo_url})
    REDIS.rpush('buildy.builds', info)
    print 'Pushed build #%s' % b.id

# def saveBuild(b, f):
#     proj_dir = os.path.join(BUILD_DIR, b.project.name)
#     if not os.path.exists(proj_dir): os.mkdir(proj_dir)
#     build_dir = os.path.join(BUILD_DIR, proj_dir, str(b.bnum))
#     if not os.path.exists(build_dir): os.mkdir(build_dir)
#     f.save(os.path.join(build_dir, f.filename))
#     return os.path.join(THIS_URL, 'builds', b.project.name, str(b.bnum))

# @app.route('/api/<action>/', methods=['POST'])
# def api(action=None):
#     global statsc
#     statsc.rebuild = True 
#     if action == "github":
#         print request.form['payload']
#     elif action == "gitlab":
#         findStalled()
#         d = request.json
#         q = [i for i in Project.select().where(repo_name=d['repository']['name'], active=True)]
#         if len(q):
#             binc = max([i.bnum for i in Build.select().where(project=q[0])] or [0])+1
#             f = d['commits']
#             if len(d['commits']) > 1:
#                 url = '/'.join(f[-1]['url'].replace('http://hydr0.com', '').split('/')[:-1])
#                 url = url + '/compare?from=%s&to=%s' % (f[0]['id'], f[-1]['id'])
#                 sha = '%s...%s' % (f[0]['id'][:9], f[-1]['id'][:9]) 
#             else:
#                 url = f[-1]['url'].split('http://hydr0.com')[-1]
#                 sha = f[-1]['id'][:9]
#             c = Commit.create(
#             info=f[-1]['message'],
#             by=f[-1]['author']['name'],
#             url=url,
#             sha=sha)

#             b = Build.create(
#                     created=time.time(),
#                     project=q[0], 
#                     bnum=binc, 
#                     code=random.randint(1000, 9999),
#                     commit=c)
#             runBuild(b)
#         else:
#             print 'Invalid build info!', d, q
#     elif action == "buildfin":
#         b = [i for i in Build.select().where(id=request.form['bid'], code=request.form['bcode'])]

#         f = request.files.get('build')
#         if not f or not f.filename.endswith('.tar.gz'):
#             print "Invalid file!"

#         if len(b):
#             b = b[0]
#             url = 'http://'+saveBuild(b, f)
#             if b.finished == True: return ":3" #Cross compile stuffs
#             b.finished = True
#             b.success = bool(int(request.form['success']))
#             b.result = request.form['result']
#             b.time = request.form['time']
#             if b.success:
#                 b.burl = url
#                 b.project.b_win += 1
#             else: 
#                 b.project.b_fail += 1
#             b.project.save()
#             b.save()
#         else:
#             print 'Invalid build!'
#     else: pass
#     return ":3"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=9013)
