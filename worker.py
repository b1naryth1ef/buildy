import sys, os, time
import socket, json, thread, urllib2
import requests, subprocess, redis
from collections import deque

acpt_addr = ['127.0.0.1']
main_addr = "build.hydr0.com"
CUR_BUILDS = {}
#cleanup = []
#out_addr = "http://build.hydr0.com/builds/"
#web_dir = "/var/www/buildy/builds"

class Break(Exception): pass

class Job():
    def __init__(self, jobid, projid, jobcode, jobdir, info):
        self.building = False
        self.bid = jobid
        self.pid = projid
        self.bname = jobdir
        self.bcode = jobcode
        self.info = info
        self.buildf = None

        self.output = []
        self.cleanup = []

        self.success = True
        self.result = None

        self.start = 0

    def open(self, cmd, **kwargs):
        nice = kwargs.get('nice')
        if nice != None: del kwargs['nice']
        kwargs['shell'] = True
        res = subprocess.Popen(cmd, **kwargs).wait()
        if nice:
            return res
        return res == 0

    def fail(self, msg):
        self.result = msg
        self.success = False
        return msg

    def action(self, acts):
        for i in acts:
            if i['type'] == 'sh':
                res = self.open(i['action'], nice=True)
                if res not in i['exitcode']:
                    raise Break(self.fail('Error on action: %s' % i['action']))
            elif i['type'] == 'chdir':
                os.chdir(i['action'])
        else: return True

    def _build(self):
        self.start = time.time()
        org = os.getcwd()
        d = os.path.join(org, self.info['dir'])
        self.building = True
        setup = False
        try:
            if not os.path.exists(d) or self.info['type'] == 'dynamic':
                if not self.open('git clone %s' % self.info['git']):
                    raise Break(self.fail("Could not clone git repo!"))
                if self.info['type'] == 'static': setup = True

            os.chdir(d)

            if setup:
                self.action(self.info['setup'])

            if not self.open("git pull origin master"):
                raise Break(self.fail('Could not update git repo!'))
            
            self.action(self.info['actions'])

            if not self.open("tar -zcvf build%s.tar.gz output; mv build%s.tar.gz .." % (self.bid, self.bid)):
                Break(self.fail("Could not package build!"))
            os.chdir(org)

            self.cleanup.append('build%s.tar.gz' % self.bid)
            self.cleanup.append(self.info['dir'])
            self.buildf = open('build%s.tar.gz' % self.bid, 'rb')
        except:
            if self.success:
                self.success = False
                self.result = "Unknown build error!"
        try: self.done()
        except: pass
        finally:
            for i in self.cleanup:
                print 'Removing %s' % i
                self.open('rm -rf %s' % i)

    def done(self):
        print 'Build finished in %ss... Success: %s | Result: %s' % (time.time()-self.start, self.success, self.result)
        self.building = False
        if self.buildf: files = {'build':self.buildf}
        else: files = {}
        requests.post('http://'+main_addr+'/api/buildfin/', 
            files=files,
            data={
                'bid':self.bid, 
                'bcode':self.bcode, 
                'success':int(self.success), 
                'result':self.result or "", 
                'time':"%.2f" % time.time()-self.start
            })

    def build(self):
        thread.start_new_thread(self._build, ())

def main():
    red = redis.StrictRedis()
    pub = red.pubsub()
    pub.subscribe('buildyjobs')
    for i in pub.listen():
        print 'Running job...'
        try: d = json.loads(i['data'])
        except: 
            print "Could not load json data: %s" % i
            continue
        with open(os.path.join('projfiles', str(d['projid'])+'.proj'), 'r') as f:
            job = Job(d['jobid'], d['projid'], d['bcode'], d['dir'], json.load(f))
            job.build()
main()
