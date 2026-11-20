from src.models.entities import Meta,RiskScore
def _ensure(s):
 r=s.get(Meta,'event_version')
 if not r:r=Meta(key='event_version',value='0');s.add(r);s.flush()
 return r
def event_version(s):
 r=s.get(Meta,'event_version')
 return int(r.value) if r else 0
def locked_event_version(s):
 _ensure(s)
 r=s.query(Meta).filter(Meta.key=='event_version').with_for_update().first()
 return int(r.value)
def bump_event_version(s):
 r=_ensure(s)
 r.value=str(int(r.value)+1)
 return int(r.value)
def invalidate_scores(s,learners,version):
 targets=[x for x in learners if x]
 n=0
 if not targets:return n
 for score in s.query(RiskScore).filter(RiskScore.status=='valid',RiskScore.learner.in_(targets)).all():
  score.status='invalidated';score.reason=f'学员学习事件在事件版本v{version}发生新增/修订，评分失效，待重训发布新版本后恢复';n+=1
 return n
