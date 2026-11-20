from datetime import date
from src.config.database import Session
from src.models.entities import RiskScore,Intervention
from tests.conftest import login
from tests.helpers import make_spec,seed_events
def add_event(client,h,code,learner,when='2026-11-02T09:00:00+08:00'):
 r=client.post('/events',json={'code':code,'learner':learner,'occurred_at':when,'course':'数据素养','note':''},headers=h)
 assert r.status_code==200,r.text
 return r.json()
def create_scheme(client,h,name='基线方案'):
 r=client.post('/risk/schemes',json={'name':name,'as_of':'2026-11-14'},headers=h)
 assert r.status_code==200,r.text
 sid=r.json()['id']
 body=client.get(f'/risk/schemes/{sid}',headers=h).json()
 assert body['state']=='evaluated',body.get('error')
 return sid
def publish(client,h,sid,threshold=0.5):
 r=client.post(f'/risk/schemes/{sid}/publish',json={'threshold':threshold,'rationale':'优先召回流失学员，误报成本仅为一次辅导'},headers=h)
 assert r.status_code==200,r.text
 return r.json()
def publish_flow(client,h):
 seed_events(make_spec())
 sid=create_scheme(client,h)
 publish(client,h,sid)
 return sid
def test_scheme_lifecycle_and_scores_binding(client,users):
 h=login(client)
 sid=publish_flow(client,h)
 schemes=client.get('/risk/schemes',headers=h).json()
 assert schemes[0]['state']=='published' and schemes[0]['threshold']==0.5
 detail=client.get(f'/risk/schemes/{sid}',headers=h).json()
 rep=detail['result']
 assert rep['evidence_sufficient'] and rep['train_samples']>0 and rep['valid_samples']>=30
 assert len(rep['thresholds'])==19 and rep['isolation']
 scores=client.get(f'/risk/schemes/{sid}/scores',headers=h).json()
 assert scores['materialized'] is True and scores['event_version']==0
 assert all(s['status']=='valid' and s['train_range']==rep['train_range'] and s['event_version']==0 for s in scores['scores'])
 levels={s['learner']:s['level'] for s in scores['scores']}
 assert levels['CHU-000']=='high' and levels['LOY-000']=='low'
def test_publish_rejected_when_evidence_insufficient(client,users):
 h=login(client)
 seed_events([(f'S-{i}',date(2026,8,3),date(2026,11,14),7) for i in range(10)])
 sid=create_scheme(client,h)
 detail=client.get(f'/risk/schemes/{sid}',headers=h).json()
 assert detail['result']['evidence_sufficient'] is False
 r=client.post(f'/risk/schemes/{sid}/publish',json={'threshold':0.5,'rationale':'证据不足仍尝试发布'},headers=h)
 assert r.status_code==409 and '证据不足' in r.json()['detail']
def test_publish_rejects_threshold_outside_table(client,users):
 h=login(client)
 seed_events(make_spec())
 sid=create_scheme(client,h)
 r=client.post(f'/risk/schemes/{sid}/publish',json={'threshold':0.37,'rationale':'表外阈值没有评估依据'},headers=h)
 assert r.status_code==422
def test_publish_interleaving_with_source_update(client,users):
 h=login(client)
 seed_events(make_spec())
 sid=create_scheme(client,h)
 add_event(client,h,'FIX-1','LOY-000')
 r=client.post(f'/risk/schemes/{sid}/publish',json={'threshold':0.5,'rationale':'交错发布应被拒绝'},headers=h)
 assert r.status_code==409 and '源数据已更新' in r.json()['detail']
 r=client.post(f'/risk/schemes/{sid}/retry',json={},headers=h)
 assert r.status_code==200
 body=client.get(f'/risk/schemes/{sid}',headers=h).json()
 assert body['state']=='evaluated' and body['event_version']==1
 publish(client,h,sid)
def test_scores_invalidated_by_event_correction(client,users):
 h=login(client)
 sid=publish_flow(client,h)
 add_event(client,h,'FIX-2','LOY-000')
 scores=client.get(f'/risk/schemes/{sid}/scores',headers=h).json()['scores']
 by_learner={s['learner']:s for s in scores}
 assert by_learner['LOY-000']['status']=='invalidated'
 assert '事件版本v1' in by_learner['LOY-000']['reason']
 assert by_learner['LOY-001']['status']=='valid'
 assert by_learner['CHU-000']['status']=='valid'
def test_draft_blocked_after_invalidation_and_recovers_after_retrain(client,users):
 h=login(client)
 sid=publish_flow(client,h)
 add_event(client,h,'FIX-3','CHU-000')
 r=client.post(f'/risk/schemes/{sid}/draft',json={'note':'失效后起草应被拒绝'},headers=h)
 assert r.status_code==409 and '评分失效' in r.json()['detail']
 sid2=create_scheme(client,h,'重训方案')
 publish(client,h,sid2)
 old=client.get(f'/risk/schemes/{sid}',headers=h).json()
 assert old['state']=='superseded'
 scores=client.get(f'/risk/schemes/{sid2}/scores',headers=h).json()['scores']
 assert all(s['status']=='valid' for s in scores)
 r=client.post(f'/risk/schemes/{sid2}/draft',json={'note':'重训发布后按当前高风险名单起草'},headers=h)
 assert r.status_code==200 and r.json()['members']
def test_draft_idempotent_and_members_match_high_risk(client,users):
 h=login(client)
 sid=publish_flow(client,h)
 scores=client.get(f'/risk/schemes/{sid}/scores',headers=h).json()['scores']
 high={s['learner'] for s in scores if s['level']=='high'}
 r1=client.post(f'/risk/schemes/{sid}/draft',json={'note':'第一次起草高风险辅导'},headers=h)
 assert r1.status_code==200
 r2=client.post(f'/risk/schemes/{sid}/draft',json={'note':'失败重试不重复起草'},headers=h)
 assert r2.status_code==200 and r2.json()['id']==r1.json()['id']
 assert set(r1.json()['members'])==high and len(high)>0
 risk_drafts=[i for i in client.get('/interventions',headers=h).json() if i['source']=='risk']
 assert len(risk_drafts)==1
def test_approved_retained_and_stale_draft_cleaned(client,users):
 h=login(client);admin=login(client,'admin@demo.local')
 sid=publish_flow(client,h)
 r=client.post(f'/risk/schemes/{sid}/draft',json={'note':'待签核的高风险辅导'},headers=h)
 iv=r.json()['id']
 ok=client.post(f'/interventions/{iv}/approve',json={},headers=admin)
 assert ok.status_code==200
 add_event(client,h,'FIX-4','LOY-005')
 sid2=create_scheme(client,h,'第二版')
 publish(client,h,sid2)
 kept=[i for i in client.get('/interventions',headers=h).json() if i['id']==iv]
 assert kept and kept[0]['status']=='approved'
 r=client.post(f'/risk/schemes/{sid2}/draft',json={'note':'新版方案的未签核草案'},headers=h)
 assert r.status_code==200
 draft_id=r.json()['id']
 add_event(client,h,'FIX-5','LOY-006')
 sid3=create_scheme(client,h,'第三版')
 publish(client,h,sid3)
 gone=[i for i in client.get('/interventions',headers=h).json() if i['id']==draft_id]
 assert not gone
 kept=[i for i in client.get('/interventions',headers=h).json() if i['id']==iv]
 assert kept and kept[0]['status']=='approved'
def test_approve_blocked_when_scores_stale(client,users):
 h=login(client);admin=login(client,'admin@demo.local')
 sid=publish_flow(client,h)
 iv=client.post(f'/risk/schemes/{sid}/draft',json={'note':'签核前发生数据更正'},headers=h).json()['id']
 add_event(client,h,'FIX-6','LOY-007')
 r=client.post(f'/interventions/{iv}/approve',json={},headers=admin)
 assert r.status_code==409 and '重新起草' in r.json()['detail']
def test_viewer_cannot_create_or_publish(client,users):
 h=login(client)
 seed_events(make_spec())
 sid=create_scheme(client,h)
 v=login(client,'viewer@demo.local')
 assert client.post('/risk/schemes',json={'name':'越权','as_of':'2026-11-14'},headers=v).status_code==403
 assert client.post(f'/risk/schemes/{sid}/publish',json={'threshold':0.5,'rationale':'越权发布尝试'},headers=v).status_code==403
 assert client.get('/risk/schemes',headers=v).status_code==200
