from peewee import *
import bcrypt
from datetime import datetime
from utils import niceDate

database = SqliteDatabase('data.db', threadlocals=True)

class BaseModel(Model):
    class Meta:
        database = database

class User(BaseModel):
    username = CharField()
    password = CharField()

class Project(BaseModel):
    name = CharField()
    author = ForeignKeyField(User, related_name="projects")
    desc = CharField()
    url = CharField()
    repo_type = CharField()
    repo_name = CharField()
    repo_url = CharField()
    config = CharField(default="")
    active = BooleanField(default=True)

    def getBuildId(self):
        q = [i.build_id for i in Build.select(Build.build_id).where((Build.project == self))]
        if len(q):
            return max(q)+1
        return 1

    def getFails(self, l=False):
        q = [i for i in Build.select().where((Build.project==self) & (Build.success == False) & (Build.built == True))]
        if l: return len(q)
        return q

    def getWins(self, l=False):
        q = [i for i in Build.select().where((Build.project==self) & (Build.success == True) & (Build.built == True))]
        if l: return len(q)
        return q

    def getTotal(self):
        return len([i for i in Build.select().where(Build.project==self)])

    def getUnbuilt(self):
        return len([i for i in Build.select().where((Build.project==self) & (Build.built == False))])

    def getpc(self):
        builds = [i for i in Build.select().where((Build.project==self) & (Build.built == True))]
        if not len(builds): return 0, 0
        winpc = 100*(len([i for i in builds if i.success == True]))/(len(builds))
        failpc = 100*(len([i for i in builds if i.success == False]))/(len(builds))
        return winpc, failpc

class Commit(BaseModel):
    project = ForeignKeyField(Project, related_name="commits")
    info = CharField(null=True)
    sha = CharField(null=True)
    author = CharField(null=True)
    url = CharField(null=True)

    def getShort(self):
        return self.sha[:6]

class Build(BaseModel):
    project = ForeignKeyField(Project, related_name="builds")
    commit = ForeignKeyField(Commit, related_name="builds")
    result = CharField(null=True)
    build_id = IntegerField(default=0)
    build_url = CharField(null=True)

    built = BooleanField(default=False)
    success = BooleanField(default=False)
    time = DateTimeField()
    finish_time = DateTimeField(null=True)

    def getCreated(self):
        if self.time:
            return niceDate(self.time)+" ago"

    def getFinished(self):
        if self.finish_time:
            return niceDate(self.finish_time)+" ago"
        return 'Unfinished'

    def getDuration(self):
        if self.time and self.finish_time:
            return niceDate(self.finish_time, fromDate=self.time)
        return ''

def createStuffz():
    User.create_table(True)
    Project.create_table(True)
    Commit.create_table(True)
    Build.create_table(True)

if __name__ == '__main__':
    createStuffz()
    if not len([i for i in User.select()]):
        u = User(username="root", password=bcrypt.hashpw('admin', bcrypt.gensalt()))
        u.save()
        m = Project(name='Neeks Engine', author=u, desc="An awesome 2D engine based on Allegro and Chipmunk, written in C.", 
            url="http://git.hydr0.com/neeks_engine", repo_name="neeks_engine", repo_type="gl", repo_url="git@hydr0.com:neeks_engine.git")
        m.save()
