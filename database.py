from peewee import *

database = SqliteDatabase('data.db', threadlocals=True)

class BaseModel(Model):
    class Meta:
        database = database

class Project(BaseModel):
    name = CharField()
    repo_name = CharField()
    git = CharField()
    b_win = IntegerField()
    b_fail = IntegerField()
    desc = CharField()
    active = BooleanField()

class Build(BaseModel):
    project = ForeignKeyField(Project, "builds")
    commit = CharField()
    commit_by = CharField()
    commit_url = CharField()
    bnum = IntegerField()
    burl = CharField()
    code = IntegerField()
    finished = BooleanField()
    success = BooleanField()
    downloads = IntegerField()

def createStuffz():
    Project.create_table(True)
    Build.create_table(True)
    test = Project.create(name="2D2", repo_name="neeks_engine", desc="2DEngine2 is a game and gui engine written by neek", git="git@hydr0.com:neeks_engine.git", active=True)
    test2 = Project.create(name="McL33tz", desc="A minecraft client mod that we use to hax nubs and make them babies ragequit", git="git@hydr0.com:mcl33tz.git", active=True)

if __name__ == '__main__':
    createStuffz()