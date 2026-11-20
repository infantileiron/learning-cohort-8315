import os,time,logging
from pathlib import Path
import redis
from src.config.database import Session
from src.models.entities import Cohort,RiskScheme
from src.services.jobs import process_cohort,process_risk
r=redis.Redis.from_url(os.environ['REDIS_URL'])
with Session() as recovery:
 for pending in recovery.query(Cohort).filter(Cohort.state.in_(['queued','running'])).all():
  pending.state='queued';r.rpush('cohort:jobs',pending.id)
 for pending in recovery.query(RiskScheme).filter(RiskScheme.state.in_(['queued','running'])).all():
  pending.state='queued';r.rpush('risk:jobs',pending.id)
 recovery.commit()
while True:
 Path('/tmp/heartbeat').touch()
 try:
  item=r.blpop(['cohort:jobs','risk:jobs'],timeout=3)
  if not item:continue
  kind=item[0].decode() if isinstance(item[0],bytes) else item[0]
  with Session() as s:
   if kind=='risk:jobs':
    row=s.get(RiskScheme,int(item[1]))
    if not row or row.state!='queued':continue
    process_risk(s,row)
   else:
    row=s.get(Cohort,int(item[1]))
    if not row or row.state!='queued':continue
    process_cohort(s,row)
 except Exception:logging.exception('worker');time.sleep(2)
