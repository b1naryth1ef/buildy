from collections import deque
import socket, json, thread
import sys, os, time, urllib2
import requests, subprocess

acpt_addr = ['127.0.0.1']
main_addr = "hydr0.com:5000"#"127.0.0.1:5001"
our_addr = "127.0.0.1:5001"
out_addr = "hydr0.com/builds/"
web_dir = "/var/www/builds"

class Job():
    def __init__(self, bid, bcode, info):
        self.building = False
        self.bid = bid
        self.bcode = bcode
        self.info = info

        self.success = True
        self.result = None

    def _build(self):
        org = os.getcwd()
        self.building = True
        try: 
            if not subprocess.Popen('git clone %s' % (self.info['git'],), shell=True).wait() == 0:
                self.success = False
                self.result = "Could not clone repository!"
            else:
                os.chdir(os.path.join(org, self.info['dir']))
                for i in self.info['actions']:
                    if i['type'] == 'sh':
                        p = subprocess.Popen(i['action'], shell=True)
                        code = p.wait()
                        if code != i['exitcode']:
                            self.success = False
                            self.result = "Error on action: %s" % i['action']
                            break
                if self.info['result']['type'] == "files" and self.success:
                    if not subprocess.Popen("tar -zcvf build_%s.tar.gz output" % (self.bid,), shell=True).wait() == 0:
                        self.success = False
                        self.result = "Could not package output!"
                    else: 
                        subprocess.Popen('mv build_%s.tar.gz %s' % (self.bid, web_dir), shell=True)
                        self.result = out_addr+"build_%s.tar.gz" % (self.bid)
                os.chdir(org)
                print 'Removing dir: ', subprocess.Popen('rm -rf %s' % self.info['dir'], shell=True).wait()
        except: 
            self.success = False
            self.result = "Unknown error in build!"
        self.done()

    def done(self):
        self.building = False
        requests.post('http://'+main_addr+'/api/buildfin/', data={'bid':self.bid, 'bcode':self.bcode, 'success':self.success, 'result':self.result})
        print 'Done!'

    def build(self):
        thread.start_new_thread(self._build, ())

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
            try:
                data = json.loads(data)
                if data['a'] == "build":
                    print 'Building!'
                    with open(os.path.join('projfiles', str(data['id'])+'.proj'), 'r') as f:
                        b = Job(data['job'], data['bcode'], json.load(f))
                        b.build()
            except:
                print 'Faild!'
                client.close()
try: serverThread()
except KeyboardInterrupt: 
    sock.close()
