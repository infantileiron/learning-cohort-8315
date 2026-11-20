from datetime import date,timedelta
from tests.conftest import login
from tests.helpers import make_spec,seed_events
def window_spec():
 spec=[]
 for i in range(30):spec.append((f'IN-{i:03}',date(2026,9,22)+timedelta(days=i%4),date(2026,11,14),5))
 for i in range(20):spec.append((f'OUT-{i:03}',date(2026,9,22)+timedelta(days=i%4),date(2026,10,10),5))
 return spec
def test_existing_cohort_flow_still_works(client,users):
 h=login(client);admin=login(client,'admin@demo.local')
 seed_events(window_spec())
 r=client.post('/cohorts',json={'name':'回归队列','start_week':'2026-09-21','end_week':'2026-11-09','as_of':'2026-11-14','horizon':3},headers=h)
 assert r.status_code==200,r.text
 cid=r.json()['id']
 detail=client.get(f'/cohorts/{cid}',headers=h).json()
 assert detail['state']=='done',detail.get('error')
 row=detail['result']['rows'][0]
 cell=next(c for c in row['cells'] if c['week_index']>0 and c['mature'] and c['missing'])
 r=client.post('/interventions',json={'cohort_id':cid,'cohort_week':row['cohort_week'],'week_index':cell['week_index'],'note':'回归：成熟周未回访辅导'},headers=h)
 assert r.status_code==200,r.text
 iv=r.json()
 assert iv['source']=='cohort' and iv['members']==cell['missing']
 ok=client.post(f"/interventions/{iv['id']}/approve",json={},headers=admin)
 assert ok.status_code==200 and ok.json()['status']=='approved'
def probe_version(client,h):
 return client.post('/risk/schemes',json={'name':'版本探针','as_of':'2026-11-14'},headers=h).json()['event_version']
def test_event_version_bumps_only_on_real_change(client,users):
 h=login(client)
 seed_events(make_spec(30,30))
 assert probe_version(client,h)==0
 body={'code':'IDEM-1','learner':'LOY-000','occurred_at':'2026-11-03T09:00:00+08:00','course':'数据素养','note':''}
 assert client.post('/events',json=body,headers=h).status_code==200
 assert probe_version(client,h)==1
 again=client.post('/events',json=body,headers=h)
 assert again.status_code==200
 assert probe_version(client,h)==1
 ev=client.get('/events',headers=h).json()
 rec=next(e for e in ev if e['code']=='IDEM-1')
 body['occurred_at']='2026-11-04T09:00:00+08:00'
 assert client.put(f"/events/{rec['id']}",json=body,headers=h).status_code==200
 assert probe_version(client,h)==2
