import sys, os, time
import socket, json, thread, urllib2
import requests, subprocess, redis
from collections import deque

acpt_addr = ['127.0.0.1']
main_addr = "build.hydr0.com"
#cleanup = []
#out_addr = "http://build.hydr0.com/builds/"
#web_dir = "/var/www/buildy/builds"

class Break(Exception): pass

class Job():
    def __init__(self, bid, bcode, bdir, info):
        self.building = False
        self.bid = bid
        self.bname = bdir
        self.bcode = bcode
        self.info = info
        self.buildf = None

        self.output = []
        self.cleanup = []

        self.success = True
        self.result = None

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
        self.done()
        for i in self.cleanup:
            print 'Removing %s' % i
            self.open('rm -rf %s' % i)

    def done(self):
        print 'Build finished... Success: %s | Result: %s' % (self.success, self.result)
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
            })

    def build(self):
        thread.start_new_thread(self._build, ())

def main():
    red = redis.StrictRedis()
    pub = red.pubsub()
    pub.subscribe('buildyjobs')
    for i in pub.listen():
        print i

def serverThread():
    global sock
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 7660))
    sock.listen(2)
    while True:
        client, addr = sock.accept()
        if not addr[0] in acpt_addr: 
            print 'Denied from %s' % addr
            client.close()
            continue
        data = client.recv(2048)
        if data:
            if 1==1:
                data = json.loads(data)
                if data['a'] == "build":
                    print 'Building!'
                    with open(os.path.join('projfiles', str(data['id'])+'.proj'), 'r') as f:
                        b = Job(data['job'], data['bcode'], data['dir'], json.load(f))
                        b.build()
            #except:
            #    print 'Faild!'
            #    client.close()
main()
