"""Independent, deterministic checks of the synthetic open fixtures."""
import hashlib
import hmac
import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT=Path(__file__).parent
cases=json.loads((ROOT/'cases.json').read_text())
rubrics=json.loads((ROOT/'rubric.json').read_text())
checks={}

assert len(cases)==18
assert [c['id'] for c in cases]==[f'B{i:02}' for i in range(1,19)]
allowed_constraints={'language','max_words','min_words','require_table','forbid_table','no_code_change','exact_sentences'}
for i,c in enumerate(cases,1):
    assert c['split']==('development' if i<=12 else 'validation')
    assert 400<=len(c['prompt'].split())<=1000
    assert 'synthetic' in c['prompt'].lower()
    assert isinstance(c['constraints'],dict) and not(set(c['constraints'])-allowed_constraints)
    assert c['constraints']['language'] in {'English','German','Simplified Chinese'}
    assert all(s in c['prompt'] for s in c['source_ids'])
    assert len(rubrics[c['id']]['must_include'])>=6
    assert set(rubrics[c['id']])=={'must_include','must_not','critical_errors','source_expectations','verification'}

checks['B03']={'type':'date comparison','agreement_before_cutoff':[date(2026,3,29)<date(2026,4,2),date(2026,4,1)<date(2026,4,2)],'physical_delivery_before_cutoff':[date(2026,6,3)<date(2026,6,1),date(2026,5,31)<date(2026,6,1)],'birch_filing_by_deadline':date(2026,7,10)<=date(2026,7,15)}
assert checks['B03']['physical_delivery_before_cutoff']==[False,True]

baseline={'receipts':1000+400,'sales':900+360,'waste':100+40}
trial={'receipts':800+600,'sales':760+570,'waste':40+30}
for record in (baseline,trial):
    assert record['receipts']==record['sales']+record['waste']
    record['sell_through']=record['sales']/record['receipts']
    record['contribution']=record['sales']*10-record['receipts']*6
assert baseline['contribution']==4200 and trial['contribution']==4900
checks['B04']={'type':'inventory and contribution reconciliation','baseline':baseline,'trial':trial,'contribution_change':trial['contribution']-baseline['contribution'],'limit':'No unmet demand is inferred from stockout hours.'}

def sign(path):
    body=b'{"reference":"R7","amount":40}'
    message='POST\n'+path+'\n10:00:00\n'+hashlib.sha256(body).hexdigest()
    return hmac.new(b'synthetic-verification-key',message.encode(),'sha256').digest()
t1,t2='/tenants/T1/orders','/tenants/T2/orders'
assert sign(t1)==sign(t1) and sign(t1)!=sign(t2)
assert all(0<=t<=60 for t in (8,15,20,25))
membership={'T1':True,'T2':False}
assert membership['T1'] and not membership['T2']
checks['B06']={'type':'toy HMAC and membership trace','same_bytes_same_signature':True,'path_change_changes_expected_signature':True,'all_incident_offsets_inside_window':True,'membership_T1':True,'membership_T2':False,'limit':'Toy key only; validates supplied control-flow explanation, not a real service implementation.'}

discharge_electric=2*10
discharge_useful=8*10
assert discharge_electric+70==discharge_useful+10
recharge_electric=18*5
assert recharge_electric==70+20
assert discharge_electric+recharge_electric==discharge_useful+10+20
checks['B07']={'type':'energy balances','discharge_electric_kWh':discharge_electric,'discharge_useful_kWh':discharge_useful,'recharge_electric_kWh':recharge_electric,'cycle_input_kWh':110,'cycle_loss_kWh':30,'cycle_useful_efficiency':80/110,'installation_efficiency':80/113}

assert 120+600-540==180
checks['B08']={'type':'finite-window accounting','arrival_rate_per_second':600/600,'completion_rate_per_second':540/600,'backlog_growth':60,'time_integrated_unfinished_job_seconds':150*600,'conditional_clearance_seconds':180/(540/600),'limit':'Clearance requires sustained completion rate and no admissions; completed-job durations include boundary time and cannot determine unfinished work ages.'}
assert checks['B08']['conditional_clearance_seconds']==200

checks['B10']={'type':'composition and standardization','baseline_pooled':110/200,'tool_pooled':79/220,'easy_before':90/100,'easy_after':19/20,'hard_before':20/100,'hard_after':60/200,'hard_share_before':100/200,'hard_share_after':200/220,'baseline_mix_standardized_tool':0.5*(19/20)+0.5*(60/200)}
assert math.isclose(checks['B10']['baseline_mix_standardized_tool'],0.625)

def update(epoch,tombstone,revision,request_epoch):
    if request_epoch!=epoch:return (409,revision)
    if tombstone:return (410,revision)
    return (200,revision+1)
assert update(5,True,0,4)==(409,0)
assert update(5,True,0,5)==(410,0)
assert update(5,False,8,5)==(200,9)
checks['B11']={'type':'provided-handler branch execution','stale_epoch_status':409,'current_tombstone_status':410,'current_live_status':200,'limit':'Scoped to supplied handler; not an audit of unprovided import or restore paths.'}

def workshop(capacity,block_fee):
    feasible=[]
    for s in range(101):
        for r in range(31):
            if s+2*r<=capacity:
                contribution=70*s+130*r
                feasible.append((contribution-2000-block_fee,s,r,contribution))
    return max(feasible)
existing=workshop(120,0)
expanded=workshop(150,1200)
assert existing==(6300,100,10,8300)
assert expanded==(7050,100,25,10250)
assert 80*100+20*180==11600 and 80*70+20*130==8200
checks['B13']={'type':'exhaustive integer enumeration','enumerated_candidate_pairs_per_capacity':101*31,'best_existing':{'profit':existing[0],'standard':existing[1],'rush':existing[2],'contribution':existing[3]},'best_expanded':{'profit':expanded[0],'standard':expanded[1],'rush':expanded[2],'contribution':expanded[3]},'incremental_profit':expanded[0]-existing[0]}

publication=date(2026,9,4)
day=publication
working=[]
while len(working)<5:
    day+=timedelta(days=1)
    if day.weekday()<5 and day!=date(2026,9,10):working.append(day)
assert [d.day for d in working]==[7,8,9,11,14]
converted={name:(datetime.fromisoformat(value)+timedelta(hours=2)).isoformat() for name,value in {'delta_portal':'2026-09-14T15:03:00','echo_portal':'2026-09-07T14:45:00','foxtrot_portal':'2026-09-15T09:40:00'}.items()}
assert date(2026,8,31)+timedelta(days=7)==date(2026,9,7)
checks['B14']={'type':'working days and clock conversion','counted_working_days':[d.isoformat() for d in working],'local_portal_receipts':converted,'calendar_note':'2026 represents the weekday pattern explicitly supplied in the synthetic prompt; no historical event is asserted.','limit':'No upload-attempt fact inferred from a generic outage screenshot.'}

additive=5+(6-5)+(7-5)
interaction=38-6-7+5
assert additive==8 and interaction==30
checks['B15']={'type':'additive comparison','additive_expected_colonies':additive,'reported_combined_colonies':38,'departure_from_additivity':interaction,'limit':'No statistical significance inferred from condition means without tank-level results.'}

checks['B16']={'type':'assignment/completer arithmetic and decision rule','assignment_new':120/160,'assignment_existing':112/160,'completer_new':72/80,'completer_existing':108/144,'noncompleter_new_passes':120-72,'noncompleter_new_total':160-80,'noncompleter_existing_passes':112-108,'noncompleter_existing_total':160-144,'lower_bound_above_margin':-5>-4}
assert checks['B16']['noncompleter_new_passes']==48
assert checks['B16']['noncompleter_existing_passes']==4
assert not checks['B16']['lower_bound_above_margin']

body='{"units":1,"units":40,"label":"test"}'
def first_wins(pairs):
    parsed={}
    for key,value in pairs:parsed.setdefault(key,value)
    return parsed
first=json.loads(body,object_pairs_hook=first_wins)
last=json.loads(body)
assert first['units']==1 and last['units']==40
assert first['units']<=10<last['units']
checks['B18']={'type':'actual JSON parser execution','first_wins_units':first['units'],'last_wins_units':last['units'],'gateway_cap_passes':first['units']<=10,'executed_units_exceed_cap':last['units']>10}

qualitative_ids=['B01','B02','B05','B09','B12','B17']
for cid in qualitative_ids:
    checks[cid]={'type':'manual source-and-rubric consistency review','status':'reviewed during original authoring','dimensions':['No supplied hypothesis or proposal promoted to an observed fact.','No explicitly missing fact silently filled.','At least six substantive semantic requirements in rubric.','No real niche factual claims require outside sourcing.'],'limit':'This is an author review, not an independent model-response evaluation.'}

verification={'status':'passed','fixture_origin':'All packets are original synthetic educational fixtures. No real source facts or generated model responses were used.','research':{'performed':False,'reason':'No real niche facts are essential; source IDs refer only to the supplied synthetic packets.'},'schema':{'cases':18,'development':12,'validation':6,'constraints':'language-only dictionaries','essential_criteria_min':min(len(r['must_include']) for r in rubrics.values()),'word_count_method':'Python str.split whitespace tokens','word_counts':{c['id']:len(c['prompt'].split()) for c in cases},'source_ids_present':True},'checks':dict(sorted(checks.items())),'file_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('cases.json','rubric.json')},'holdout_handling':'No holdout prompt, rubric, category detail, or verification result is included here. Holdout verification is stored only under sealed/.'}
(ROOT/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'passed','open_cases':18,'executed_case_checks':len(checks)-len(qualitative_ids),'manual_source_reviews':len(qualitative_ids),'min_words':min(len(c['prompt'].split()) for c in cases),'max_words':max(len(c['prompt'].split()) for c in cases)}))
