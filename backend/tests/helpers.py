from datetime import date,timedelta
from src.config.database import Session
from src.models.entities import Event
AS_OF=date(2026,11,14)
def make_spec(loyal=100,churner=100):
 spec=[]
 for i in range(loyal):spec.append((f'LOY-{i:03}',date(2026,8,3)+timedelta(days=i%5),date(2026,11,14),5))
 for i in range(churner):spec.append((f'CHU-{i:03}',date(2026,8,3)+timedelta(days=i%5),date(2026,10,10),5))
 return spec
def events_of(spec):
 out=[]
 for ln,start,stop,step in spec:
  d=start
  while d<=stop:
   out.append({'code':f'{ln}-{d.isoformat()}','learner':ln,'occurred_at':d.isoformat()+'T02:00:00+00:00','course':'数据素养','note':''})
   d+=timedelta(days=step)
 return out
def snapshot_for(spec,as_of=AS_OF):
 return {'config':{'name':'测试方案','as_of':as_of.isoformat()},'events':events_of(spec)}
def seed_events(spec):
 with Session() as s:
  for e in events_of(spec):s.add(Event(**e))
  s.commit()
