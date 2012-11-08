import sys, os, time
import socket, json, thread, urllib2, platform
import requests, subprocess, redis
from collections import deque

acpt_addr = ['127.0.0.1']
main_addr = "build.hydr0.com"
JOBS_BUILT = []
DEBUG = False

class BuildJob():
    def __init__(self, id, pid, url):
        self.id = id
        self.url = url
        self.pid = pid

        self.tmpdir = os.path.join('.', 'tmp', 'project%s' % pid)

        self.building = False
        self.success = True
        self.result = []

        self.startTime = 0
        self.totalTime = 0

    def msg(self, msg, add=False):
        if not add:
            self.result.append(msg)
        self.result[-1] = self.result[-1]+msg

    def open(self, cmd, **kwargs):
        kwargs['shell'] = True
        res = subprocess.Popen(cmd, **kwargs).wait()
        return not res

    def endJob(self, msg, failed=False, out=None):
        self.result.append(msg)
        if failed:
            print '--> BUILD FAILURE <--'
            files = []
        else:
            print '--> BUILD SUCCESS <--'
            files = [out]
        requests.post('http://'+main_addr+'/api/put_build/',
            files=files,
            data={
                'pid':self.pid, 
                'id':self.id,
                'success':int(self.success), 
                'result':'\n'.join(self.results), 
                'time':"%s" % (time.time()-self.start)})

    def startJob(self):
        if not os.path.exists(self.tmpdir):
            self.msg('Project temp directory does not exist; creating... ')
            try: os.mkdir(self.tmpdir)
            except:
                self.msg('[FAILED]', True)
                self.endJob("Problem creating temporary build directory (perm issues?)", failed=True)
            self.msg('[DONE', True)
        os.chdir(self.tmpdir)
        self.msg('Stashing local changes (just in case)... ')
        if not self.open('git stash'):
            self.msg('[FAILED]', True)
            self.endJob('Could not stash local changes (git problems?)', failed=True)
        self.msg('[DONE]', True)
        self.msg('Pulling latest version from git... ')
        if not self.open('git pull origin master'): #Eventually support moar branches
            self.msg('[FAILED]', True)
            self.endJob('Could not pull from git (git problems?)', failed=True)
        self.msg('[DONE]', True)
        if os.path.exists('cleanup.sh'):
            self.msg('Found cleanup script, running it... ')
            if not self.open('cleanup.sh'):
                self.msg('[FAILED]', True)
                self.endJob('Cleanup script failed!', failed=True)
            self.msg('[DONE]', True)
        if os.path.exists('build.sh'):
            self.msg('Found build script, running it... ')
            if not self.open('build.sh'):
                self.msg('[FAILED]', True)
                self.endJob('Build script failed!', failed=True)
            self.msg('[DONE]', True)
        else: self.endJob('No build script found!', failed=True)
        #@TODO Add test script?
        self.msg('Packaging build results... ')
        name = "%s_%s_%s_%s.tar.gz" % (platform.machine().lower(), platform.system().lower(), self.pid, self.id)
        if not self.open("tar -zcvf %s output" % (name, name)):
            self.msg('[FAILED]', True)
            self.endJob('Could not package build results!', failed=True)
        self.endJob('Build #%s of %s built with 0 errors!' % (self.id, self.pid), out=name)

def main():
    red = redis.Redis('hydr0.com')
    while True:
        build = red.blpop(['buildy.builds', 'buildy.sys.%s' % platform.system().lower(), 'buildy.arch.%s' % platform.machine().lower()])
        try:
            build = json.loads(build)
        except:
            print 'Could not load json data: %s' % build
            continue
        b = BuildJob(build['id'], build['pid'], build['git'])
        thread.start_new_thread(b.startJob, ())
main()
