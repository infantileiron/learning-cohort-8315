from datetime import date,datetime,timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict
import hashlib,json,math
TZ=ZoneInfo('Asia/Shanghai')
LABEL_DAYS=14
STEP_DAYS=14
TRAIN_CUTOFFS=3
MIN_VALID=30
MIN_CLASS=8
FEATURES=['recency_days','active_14','active_28','total_days','tenure_days','last_gap']
def learn_days(events,as_of):
 days=defaultdict(set);future=0
 for e in events:
  ts=datetime.fromisoformat(e['occurred_at'].replace('Z','+00:00'))
  if ts.tzinfo is None:raise ValueError('事件缺少时区')
  d=ts.astimezone(TZ).date()
  if d>as_of:future+=1;continue
  days[e['learner']].add(d)
 return days,future
def features(ds,cutoff):
 past=sorted(d for d in ds if d<=cutoff)
 if not past:return None
 gap=(past[-1]-past[-2]).days if len(past)>1 else (cutoff-past[0]).days
 return [(cutoff-past[-1]).days,sum(1 for d in past if d>cutoff-timedelta(days=LABEL_DAYS)),sum(1 for d in past if d>cutoff-timedelta(days=2*LABEL_DAYS)),len(past),(cutoff-past[0]).days,gap]
def label(ds,cutoff):
 return 0 if any(cutoff<d<=cutoff+timedelta(days=LABEL_DAYS) for d in ds) else 1
def group(learner):
 return int(hashlib.sha256(learner.encode()).hexdigest(),16)%5<4
def build_samples(days,train_cutoffs,valid_cutoff):
 train=[];valid=[]
 for learner,ds in days.items():
  if group(learner):
   for cutoff in train_cutoffs:
    x=features(ds,cutoff)
    if x is not None:train.append((learner,x,label(ds,cutoff)))
  else:
   x=features(ds,valid_cutoff)
   if x is not None:valid.append((learner,x,label(ds,valid_cutoff)))
 return train,valid
def logreg_train(X,Y,epochs=600,rate=0.5,l2=0.001):
 n=len(X);m=len(X[0])
 mean=[sum(x[j] for x in X)/n for j in range(m)]
 sd=[(sum((x[j]-mean[j])**2 for x in X)/n)**.5 or 1.0 for j in range(m)]
 Z=[[(x[j]-mean[j])/sd[j] for j in range(m)] for x in X]
 w=[0.0]*m;b=0.0
 for _ in range(epochs):
  gw=[0.0]*m;gb=0.0
  for z,y in zip(Z,Y):
   p=1.0/(1.0+math.exp(-(sum(wj*zj for wj,zj in zip(w,z))+b)));e=p-y
   for j in range(m):gw[j]+=e*z[j]
   gb+=e
  for j in range(m):w[j]-=rate*(gw[j]/n+l2*w[j])
  b-=rate*gb/n
 return w,b,mean,sd
def logreg_predict(model,x):
 w,b,mean,sd=model
 t=sum(wj*(xj-mj)/sj for wj,xj,mj,sj in zip(w,x,mean,sd))+b
 return 1.0/(1.0+math.exp(-t))
def threshold_table(probs,labels):
 table=[]
 for k in range(1,20):
  t=round(k*0.05,2);tp=fp=fn=tn=0
  for p,y in zip(probs,labels):
   pos=p>=t
   if pos and y:tp+=1
   elif pos:fp+=1
   elif y:fn+=1
   else:tn+=1
  table.append(dict(threshold=t,tp=tp,fp=fp,fn=fn,tn=tn,precision=round(tp/(tp+fp),4) if tp+fp else None,recall=round(tp/(tp+fn),4) if tp+fn else None,fp_rate=round(fp/(fp+tn),4) if fp+tn else None,fn_rate=round(fn/(fn+tp),4) if fn+tp else None))
 return table
def evaluate(snapshot):
 cfg=snapshot['config'];as_of=date.fromisoformat(cfg['as_of'])
 days,future=learn_days(snapshot['events'],as_of)
 if not days:raise ValueError('截至日以前没有有效学习事件，请核对时间和输入')
 valid_cutoff=as_of-timedelta(days=LABEL_DAYS)
 train_cutoffs=[as_of-timedelta(days=LABEL_DAYS*(k+2)) for k in range(TRAIN_CUTOFFS)]
 train,valid=build_samples(days,train_cutoffs,valid_cutoff)
 if not valid:raise ValueError('验证观察期内没有在册学员，无法评估')
 if not train:raise ValueError('历史观察期不足，无法训练基线模型')
 model=logreg_train([x for _,x,_ in train],[y for *_,y in train])
 probs=[logreg_predict(model,x) for _,x,_ in valid]
 labels=[y for *_,y in valid]
 table=threshold_table(probs,labels)
 positives=sum(labels);negatives=len(labels)-positives
 gaps=[]
 if len(labels)<MIN_VALID:gaps.append(f'验证样本{len(labels)}条，少于{MIN_VALID}条下限')
 if positives<MIN_CLASS:gaps.append(f'验证期真实流失{positives}人，少于{MIN_CLASS}人下限')
 if negatives<MIN_CLASS:gaps.append(f'验证期未流失{negatives}人，少于{MIN_CLASS}人下限')
 full=[(ln,x,y)for cutoff in train_cutoffs+[valid_cutoff]for ln,ds in days.items()for x in[features(ds,cutoff)]if x is not None for y in[label(ds,cutoff)]]
 final=logreg_train([x for _,x,_ in full],[y for *_,y in full])
 scores=[dict(learner=ln,score=round(logreg_predict(final,features(ds,as_of)),4))for ln,ds in sorted(days.items())if features(ds,as_of) is not None]
 train_range=f'{train_cutoffs[-1].isoformat()}..{as_of.isoformat()}'
 return dict(as_of=cfg['as_of'],label_days=LABEL_DAYS,valid_cutoff=valid_cutoff.isoformat(),train_cutoffs=[c.isoformat() for c in train_cutoffs],train_range=train_range,train_samples=len(train),train_learners=len({ln for ln,_,_ in train}),valid_samples=len(valid),valid_learners=len({ln for ln,_,_ in valid}),positives=positives,negatives=negatives,isolation='按学员哈希分组：验证学员与训练学员完全不重叠；训练cutoff早于验证cutoff，特征只用cutoff以前数据，标签只用cutoff后14天完整观察期',thresholds=table,evidence_sufficient=not gaps,evidence_gaps=gaps,scores=scores,feature_names=FEATURES,future_events_excluded=future,event_count=len(snapshot['events']),timezone='Asia/Shanghai',checksum=hashlib.sha256(json.dumps(snapshot,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),method='以截至日以前学习预测未来14天均无学习（流失）。标签仅取观察期完整的cutoff；按时间前推回测：训练cutoff早于验证cutoff，同一学员只属一侧。标准化逻辑回归(L2)。阈值为高风险界线：误报=预测流失实际回访，漏报=预测安全实际流失。')
