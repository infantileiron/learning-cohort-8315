import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
url=os.environ['DATABASE_URL']
kw={'pool_pre_ping':True}
if url.startswith('sqlite'):
 from sqlalchemy.pool import StaticPool
 kw={'connect_args':{'check_same_thread':False},'poolclass':StaticPool}
engine=create_engine(url,**kw)
Session=sessionmaker(bind=engine,expire_on_commit=False)
Base=declarative_base()
def db():
 with Session() as s: yield s
