from sqlalchemy import Column,Integer,String,JSON,Text,ForeignKey,Float,UniqueConstraint
from src.config.database import Base
class User(Base):
 __tablename__='users'
 id=Column(Integer,primary_key=True);email=Column(String(100),unique=True,nullable=False);password=Column(String(200));role=Column(String(20))
class Event(Base):
 __tablename__='events'
 id=Column(Integer,primary_key=True);code=Column(String(60),unique=True,nullable=False);learner=Column(String(60),nullable=False,index=True);occurred_at=Column(String(40),nullable=False);course=Column(String(40));note=Column(Text,default='')
class Cohort(Base):
 __tablename__='cohorts'
 id=Column(Integer,primary_key=True);name=Column(String(100));start_week=Column(String(10));end_week=Column(String(10));as_of=Column(String(10));horizon=Column(Integer);state=Column(String(20),default='queued');result=Column(JSON,nullable=True);error=Column(Text,default='')
class Meta(Base):
 __tablename__='meta'
 key=Column(String(40),primary_key=True);value=Column(String(200))
class RiskScheme(Base):
 __tablename__='risk_schemes'
 id=Column(Integer,primary_key=True);name=Column(String(100));as_of=Column(String(10));state=Column(String(20),default='queued');threshold=Column(Float,nullable=True);rationale=Column(Text,default='');event_version=Column(Integer,default=0);result=Column(JSON,nullable=True);error=Column(Text,default='')
class RiskScore(Base):
 __tablename__='risk_scores'
 id=Column(Integer,primary_key=True);scheme_id=Column(Integer,ForeignKey('risk_schemes.id'),index=True);learner=Column(String(60),index=True);score=Column(Float);level=Column(String(10));event_version=Column(Integer);train_range=Column(String(80));status=Column(String(20),default='valid');reason=Column(String(300),default='')
class Intervention(Base):
 __tablename__='interventions'
 id=Column(Integer,primary_key=True);cohort_id=Column(Integer,ForeignKey('cohorts.id'));scheme_id=Column(Integer,ForeignKey('risk_schemes.id'),nullable=True);source=Column(String(10),default='cohort');cohort_week=Column(String(10));week_index=Column(Integer);note=Column(Text);members=Column(JSON);status=Column(String(20),default='draft')
 __table_args__=(UniqueConstraint('source','scheme_id',name='uq_intervention_source_scheme'),)
class Audit(Base):
 __tablename__='audits'
 id=Column(Integer,primary_key=True);actor=Column(String(100));action=Column(String(200));created=Column(String(40))
