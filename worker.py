from collections import deque
import socket, json, thread
import sys, os, time, urllib2

acpt_addr = ['127.0.0.1']
actions = {}
b = Builder(sys.argv[1])

class Builder():
    def __init__(self, name):
        self.name = name
        self.throttle = [0, False] #Time in secs, enabled
        self.cur_action = [None, 0, 0] #action, start, end
        self.building = False
        self.q = deque()

    def build(self, jobid, action, callback=None):
        job = []
        for item in action:
            self.cur_action = [action['name'], time.time(), 0]
            p = Popen(action['exec'], shell=True)
            p.wait()
            self.cur_action[2] = time.time()
            job.append(self.cur_action)

def Action(name):
    def deco(func):
        actions[name] = func
        return func
    return deco

@Action('status')
def checkStatus(c, obj):
    c.send(json.dumps({'response':'GOOD', 'data':{'status':b.building, 'queuesize':len(b.q), 'throttle':b.throttle}}))

def parser(c, data):
    if data['action'] in actions.keys():
        actions[data['action']](c, data)
    else:
        c.send(json.dumps({'response':'BAD', 'error':2}))

def serverThread():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 7650))
    sock.listen(1)
    while True:
        client, address = sock.accept()
        if not address in acpt_adrr: client.close()
        data = client.recv(2048)
        if data:
            try:
                parser(client, json.loads(data))
            except:
                client.send(json.dumps({'response':'BAD', 'error':1}))

thread.start_new_thread(serverThread, ())
while True: time.sleep(5)

#NOTES:
#ERRORS:
#1: incomplete/corrupted json data
#2: unknown/incorrect api call