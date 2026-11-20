from fastapi import HTTPException
from src.models.entities import RiskScheme,RiskScore,Intervention
from src.services.versions import locked_event_version
def ensure(s,i):
 r=s.get(RiskScheme,i)
 if not r:raise HTTPException(404,'流失风险方案不存在')
 return r
def lock(s,i):
 r=s.query(RiskScheme).filter(RiskScheme.id==i).with_for_update().first()
 if not r:raise HTTPException(404,'流失风险方案不存在')
 return r
def publish(s,scheme,threshold,rationale):
 if scheme.state!='evaluated':raise HTTPException(409,'仅已评估方案可发布')
 rep=scheme.result or {}
 if not rep.get('evidence_sufficient'):raise HTTPException(409,'证据不足，拒绝发布：'+'；'.join(rep.get('evidence_gaps',[])or['验证样本不足']))
 offered={t['threshold'] for t in rep.get('thresholds',[])}
 if offered and round(threshold,2) not in offered:raise HTTPException(422,'阈值需取自评估阈值表，发布页展示的误报/漏报才有依据')
 if locked_event_version(s)!=scheme.event_version:raise HTTPException(409,'源数据已更新，评估已过时，请重新评估后再发布')
 for old in s.query(RiskScheme).filter(RiskScheme.state=='published',RiskScheme.id!=scheme.id).all():
  old.state='superseded'
  for sc in s.query(RiskScore).filter(RiskScore.scheme_id==old.id,RiskScore.status=='valid').all():
   sc.status='invalidated';sc.reason=f'方案被#{scheme.id}换版，评分失效'
  for d in s.query(Intervention).filter(Intervention.source=='risk',Intervention.scheme_id==old.id,Intervention.status=='draft').all():
   s.delete(d)
 scheme.state='published';scheme.threshold=round(threshold,2);scheme.rationale=rationale
 for row in rep.get('scores',[]):
  p=row['score'];level='high' if p>=scheme.threshold else('medium' if p>=scheme.threshold*0.6 else 'low')
  s.add(RiskScore(scheme_id=scheme.id,learner=row['learner'],score=p,level=level,event_version=scheme.event_version,train_range=rep.get('train_range','')))
 return scheme
def draft(s,scheme,note):
 if scheme.state!='published':raise HTTPException(409,'仅已生效方案可起草辅导')
 if locked_event_version(s)!=scheme.event_version:raise HTTPException(409,'源数据已更新，评分失效，待重训发布新版本后再起草')
 members=[sc.learner for sc in s.query(RiskScore).filter(RiskScore.scheme_id==scheme.id,RiskScore.status=='valid',RiskScore.level=='high').order_by(RiskScore.score.desc(),RiskScore.learner).all()]
 if not members:raise HTTPException(409,'当前没有高风险学员，无需起草辅导')
 existing=s.query(Intervention).filter(Intervention.source=='risk',Intervention.scheme_id==scheme.id).first()
 if existing:
  if existing.status!='draft':raise HTTPException(409,'该方案辅导已签核保留，不可重复起草')
  existing.members=members;existing.note=note
  return existing
 r=Intervention(source='risk',scheme_id=scheme.id,note=note,members=members,status='draft')
 s.add(r)
 return r
def check_approval_fresh(s,intervention):
 if intervention.source!='risk':return
 scheme=s.get(RiskScheme,intervention.scheme_id)
 if not scheme or scheme.state!='published' or locked_event_version(s)!=scheme.event_version:
  raise HTTPException(409,'评分已失效或方案已换版，请按当前高风险名单重新起草后再签核')
