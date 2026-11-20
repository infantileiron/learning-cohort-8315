from datetime import date,timedelta
from src.services.risk import features,label,build_samples,threshold_table,evaluate,learn_days,LABEL_DAYS
from tests.helpers import make_spec,snapshot_for,AS_OF
def d(s):return date.fromisoformat(s)
def test_features_ignore_events_after_cutoff():
 cutoff=d('2026-10-31');base={d('2026-10-20'),d('2026-10-31')}
 with_future=base|{d('2026-11-05'),d('2026-11-12')}
 assert features(base,cutoff)==features(with_future,cutoff)
 x=features(base,cutoff)
 assert x[0]==0 and x[3]==2
def test_features_cutoff_day_counts_and_recency():
 cutoff=d('2026-10-31')
 assert features({d('2026-10-31')},cutoff)[0]==0
 assert features({d('2026-10-30')},cutoff)[0]==1
 assert features({d('2026-11-01')},cutoff) is None
def test_label_window_boundary():
 cutoff=d('2026-10-31')
 assert label({cutoff},cutoff)==1
 assert label({cutoff+timedelta(days=LABEL_DAYS)},cutoff)==0
 assert label({cutoff+timedelta(days=LABEL_DAYS+1)},cutoff)==1
 assert label({cutoff+timedelta(days=1)},cutoff)==0
def test_labels_only_from_complete_observation():
 rep=evaluate(snapshot_for(make_spec(40,40)))
 valid=d(rep['valid_cutoff'])
 assert valid+timedelta(days=LABEL_DAYS)==AS_OF
 for c in rep['train_cutoffs']:
  assert d(c)+timedelta(days=LABEL_DAYS)<=AS_OF
  assert d(c)<valid
def test_learner_isolation_between_train_and_valid():
 days,_=learn_days([{'learner':f'L-{i}','occurred_at':'2026-10-01T02:00:00+00:00'} for i in range(50)],AS_OF)
 train,valid=build_samples(days,[d('2026-09-19'),d('2026-10-03'),d('2026-10-17')],d('2026-10-31'))
 train_learners={ln for ln,_,_ in train};valid_learners={ln for ln,_,_ in valid}
 assert train_learners and valid_learners
 assert not train_learners&valid_learners
def test_future_events_excluded_from_learning_days():
 events=[{'learner':'A','occurred_at':'2026-11-10T02:00:00+00:00'},{'learner':'A','occurred_at':'2026-11-20T02:00:00+00:00'},{'learner':'B','occurred_at':'2026-12-01T02:00:00+00:00'}]
 days,future=learn_days(events,AS_OF)
 assert future==2 and set(days)=={'A'} and days['A']=={d('2026-11-10')}
def test_threshold_table_counts():
 probs=[0.9,0.8,0.4,0.1];labels=[1,0,1,0]
 table=threshold_table(probs,labels)
 row=next(t for t in table if t['threshold']==0.5)
 assert (row['tp'],row['fp'],row['fn'],row['tn'])==(1,1,1,1)
 assert row['precision']==0.5 and row['recall']==0.5
 assert len(table)==19
def test_evidence_insufficient_when_samples_small():
 spec=[(f'S-{i}',date(2026,8,3),date(2026,11,14),7) for i in range(10)]
 rep=evaluate(snapshot_for(spec))
 assert rep['evidence_sufficient'] is False
 assert any('验证样本' in g for g in rep['evidence_gaps'])
def test_evaluate_ranks_churners_above_loyals():
 rep=evaluate(snapshot_for(make_spec()))
 assert rep['evidence_sufficient'] is True
 scores={s['learner']:s['score'] for s in rep['scores']}
 chu=[v for k,v in scores.items() if k.startswith('CHU')]
 loy=[v for k,v in scores.items() if k.startswith('LOY')]
 assert min(chu)>max(loy)
 mid=next(t for t in rep['thresholds'] if t['threshold']==0.5)
 assert mid['recall']>=0.9 and mid['precision']>=0.9
