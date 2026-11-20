import os,json
from pathlib import Path
from src.services.analysis import calculate
from src.services.risk import evaluate
ARTIFACTS=os.environ.get('ARTIFACTS_DIR','/artifacts')
def process_cohort(s,row):
 snapshot=row.result['snapshot'];row.state='running';s.commit()
 try:
  row.result={**calculate(snapshot),'snapshot':snapshot};row.state='done'
  Path(ARTIFACTS,str(row.id)+'.json').write_text(json.dumps(row.result,ensure_ascii=False))
 except Exception as e:row.state='failed';row.error=str(e)
 s.commit()
def process_risk(s,row):
 snapshot=row.result['snapshot'];row.state='running';s.commit()
 try:
  row.result={**evaluate(snapshot),'snapshot':snapshot};row.state='evaluated'
  Path(ARTIFACTS,'risk-'+str(row.id)+'.json').write_text(json.dumps(row.result,ensure_ascii=False))
 except Exception as e:row.state='failed';row.error=str(e)
 s.commit()
