from peewee import *

database = SqliteDatabase('data.db', threadlocals=True)

class BaseModel(Model):
    class Meta:
        database = database

class Project(BaseModel):
    name = CharField()
    repo_name = CharField()
    git = CharField()
    b_win = IntegerField(null=True)
    b_fail = IntegerField(null=True)
    desc = CharField()
    active = BooleanField(null=True)

class Commit(BaseModel):
    info = CharField()
    sha = CharField()
    by = CharField()
    url = CharField()

class Build(BaseModel):
    project = ForeignKeyField(Project, "builds")
    commit = ForeignKeyField(Commit, "builds")
    result = CharField()
    bnum = IntegerField(null=True)
    burl = CharField()
    code = IntegerField(null=True)
    finished = BooleanField(null=True)
    success = BooleanField(null=True)
    downloads = IntegerField(null=True)
    time = IntegerField(null=True)

def createStuffz():
    Project.create_table(True)
    Commit.create_table(True)
    Build.create_table(True)
    test = Project.create(name="2D2", repo_name="neeks_engine", desc="2DEngine2 is a game and gui engine written by neek", git="git@hydr0.com:neeks_engine.git", active=True)
    test2 = Project.create(name="MCL33tz", repo_name="MCL33tz", desc="A minecraft client mod that we use to hax nubs and make them babies ragequit", git="git@hydr0.com:mcl33tz.git", active=True)

if __name__ == '__main__':
    createStuffz()