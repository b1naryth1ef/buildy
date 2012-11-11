import sys, os, time
import socket, json, thread, urllib2, platform
import requests, subprocess, redis
import popen2
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
        self.output = []

        self.startTime = 0

    def msg(self, msg, add=False):
        if not add:
            self.result.append(msg)
            return 
        self.result[-1] = self.result[-1]+msg

    def open(self, cmd, **kwargs):
        kwargs['shell'] = True
        p = subprocess.Popen(cmd, **kwargs)
        res = p.wait()
        return not res

    def endJob(self, msg, failed=False, out=None):
        self.result.append(msg)
        if failed:
            self.success = False
            print '--> BUILD FAILURE <--'
            print '\n  '.join(['--------']+self.result)
            files = {}
        else:
            print '--> BUILD SUCCESS <--'
            files = {'build':out}
        r = requests.post('http://'+main_addr+'/api/put_build',
            files=files,
            data={
                'pid':self.pid, 
                'id':self.id,
                'success':int(self.success), 
                'result':'\n'.join(self.result), 
                'output':'\n'.join(self.output),
                'time':"%s" % (time.time()-self.startTime)})
        print 'Posted build: %s' % r.status_code
        os.chdir('../..')
    
    def startJob(self):
        if not os.path.exists(self.tmpdir):
            self.msg('Cloning git repo... ')
            if not self.open('git clone %s ./tmp/project%s' % (self.url, self.pid)):
                self.msg('[FAILED]', True)
                return self.endJob('Could not clone git repository!')
            os.chdir(self.tmpdir)
            self.msg('[DONE]', True)
        else:
            os.chdir(self.tmpdir)
            self.msg('Stashing local changes (just in case)... ')
            if not self.open('git stash'):
                self.msg('[FAILED]', True)
                return self.endJob('Could not stash local changes (git problems?)', failed=True)
            self.msg('[DONE]', True)
            self.msg('Pulling latest version from git... ')
            if not self.open('git pull origin master'): #Eventually support moar branches
                self.msg('[FAILED]', True)
                return self.endJob('Could not pull from git (git problems?)', failed=True)
            self.msg('[DONE]', True)
        if os.path.exists('cleanup.sh'):
            self.msg('Found cleanup script, running it... ')
            self.open('chmod +x cleanup.sh')
            if not self.open('./cleanup.sh'):
                self.msg('[FAILED]', True)
                return self.endJob('Cleanup script failed!', failed=True)
            self.msg('[DONE]', True)
        if os.path.exists('build.sh'):
            self.msg('Found build script, running it... ')
            self.open('chmod +x build.sh')
            if not self.open('./build.sh'):
                self.msg('[FAILED]', True)
                return self.endJob('Build script failed!', failed=True)
            self.msg('[DONE]', True)
        else: return self.endJob('No build script found!', failed=True)
        #@TODO Add test script?
        self.msg('Packaging build results... ')
        name = "%s_%s_%s_%s.tar.gz" % (platform.machine().lower(), platform.system().lower(), self.pid, self.id)
        if not self.open("tar -zcvf %s output" % (name)):
            self.msg('[FAILED]', True)
            return self.endJob('Could not package build results!', failed=True)
        self.endJob('Build #%s of %s built with 0 errors!' % (self.id, self.pid), out=os.path.join('.', name))
        

def main():
    red = redis.Redis('hydr0.com')
    while True:
        build = red.blpop(['buildy.builds', 'buildy.sys.%s' % platform.system().lower(), 'buildy.arch.%s' % platform.machine().lower()])
        try:
            build = json.loads(build[1])
        except:
            print 'Could not load json data: %s' % str(build)
            continue
        b = BuildJob(build['id'], build['pid'], build['git'])
        b.startJob()
        #thread.start_new_thread(b.startJob, ())
main()
