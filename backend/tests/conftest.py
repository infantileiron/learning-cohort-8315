import os,sys,tempfile
os.environ['DATABASE_URL']='sqlite:///:memory:'
os.environ['REDIS_URL']='redis://localhost:6379/0'
os.environ['JWT_SECRET']='test-secret'
os.environ['ARTIFACTS_DIR']=tempfile.mkdtemp()
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pytest
from fastapi.testclient import TestClient
from src.config.database import Base,engine,Session
from src.main import app
from src.services import queue,jobs
from src.models.entities import User,Cohort,RiskScheme
from src.utils.security import hash_password
def sync_push(kind,i):
 with Session() as s:
  model={'risk:jobs':RiskScheme,'cohort:jobs':Cohort}[kind]
  row=s.get(model,i)
  if not row or row.state!='queued':return
  (jobs.process_risk if kind=='risk:jobs' else jobs.process_cohort)(s,row)
@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
 Base.metadata.drop_all(engine);Base.metadata.create_all(engine)
 monkeypatch.setattr(queue,'push',sync_push)
 yield
 Base.metadata.drop_all(engine)
@pytest.fixture
def client():
 return TestClient(app)
@pytest.fixture
def users():
 with Session() as s:
  for role in ('admin','analyst','viewer'):
   s.add(User(email=role+'@demo.local',role=role,password=hash_password('Demo123!')))
  s.commit()
def login(client,email='analyst@demo.local'):
 r=client.post('/auth/login',json={'email':email,'password':'Demo123!'})
 assert r.status_code==200,r.text
 return {'Authorization':'Bearer '+r.json()['token']}
