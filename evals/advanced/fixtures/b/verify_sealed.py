"""Sealed quantitative checks. Do not disclose case-level results before freeze."""
import hashlib
import itertools
import json
from datetime import date
from pathlib import Path

ROOT=Path(__file__).parent
cases=json.loads((ROOT/'cases.json').read_text())
rubrics=json.loads((ROOT/'rubric.json').read_text())
assert len(cases)==12
assert [c['id'] for c in cases]==[f'B{i:02}' for i in range(19,31)]
for c in cases:
    assert c['split']=='holdout'
    assert 400<=len(c['prompt'].split())<=1000
    assert 'synthetic' in c['prompt'].lower()
    assert set(c['constraints'])=={'language'}
    assert c['constraints']['language'] in {'English','German','Simplified Chinese'}
    assert all(s in c['prompt'] for s in c['source_ids'])
    assert len(rubrics[c['id']]['must_include'])>=6
    assert set(rubrics[c['id']])=={'must_include','must_not','critical_errors','source_expectations','verification'}

checks={}
decay=100*(0.5)**(30/10)
assert decay==12.5
checks['B19']={'type':'calibrated decay execution','half_lives':3,'predicted_reporter_if_production_stops':decay,'reported_reporter':13,'absolute_difference':13-decay,'limit':'No assay precision or statistical significance is invented.'}

assert 30000+25000==55000
assert 30000+25000+35000==90000
assert (date(2026,5,5)-date(2026,4,20)).days==15
checks['B20']={'type':'aggregation/date calculation','april_related_value':55000,'if_elm_related_total':90000,'if_elm_separate_value':35000,'first_to_last_departure_days':15,'digital_value_excluded':20000,'limit':'Elm agreement identity and Beech certification remain unknown/unapproved in the supplied packet.'}

opening_accounts=50+10+5
opening_revenue=50*20+10*100+5*1000
surviving_accounts=45+9+4
gross_retained=45*20+9*100+4*1000
net_retained=45*20+9*100+6000
new_accounts=20+2
new_revenue=20*20+2*100
assert (opening_accounts,opening_revenue,surviving_accounts,gross_retained,net_retained)==(65,7000,58,5800,7800)
assert surviving_accounts+new_accounts==80 and net_retained+new_revenue==8400
assert gross_retained+(5*20+1*100+1*1000)==opening_revenue
checks['B21']={'type':'cohort reconciliation','opening_accounts':65,'survivors':58,'canceled_accounts':7,'closing_accounts':80,'opening_recurring_revenue':7000,'same_cohort_closing_revenue':7800,'expansion_excluded_revenue':5800,'new_recurring_revenue':600,'all_closing_recurring_revenue':8400,'account_retention':58/65,'net_revenue_retention':7800/7000,'gross_revenue_retention':5800/7000,'total_revenue_growth_ratio':8400/7000}

initial=100*10
treated=50*12
comparison=50*18
diluted=100*6
assert (initial,treated,comparison,diluted)==(1000,600,900,600)
assert initial-treated-350==50
checks['B24']={'type':'material accounting','initial_mg':initial,'treated_liquid_mg':treated,'comparison_liquid_mg':comparison,'diluted_liquid_mg':diluted,'liquid_plus_filter_accounted_mg':treated+350,'unaccounted_mg':initial-treated-350,'observed_liquid_contrast_mg':comparison-treated,'limit':'No unmeasured fate or general causal effect is assigned to the missing material.'}

def schedule(scanner_order,review_order,a_ocr=6):
    scanner_time={'A':5,'B':3}
    ocr_time={'A':a_ocr,'B':3}
    review_time={'A':2,'B':3}
    release={}
    scanner=[]
    t=0
    for job in scanner_order:
        scanner.append({'job':job,'start':t,'end':t+scanner_time[job]})
        t+=scanner_time[job]
        release[job]=t+ocr_time[job]
    reviews=[]
    completed={}
    t=0
    for job in review_order:
        t=max(t,release[job])
        reviews.append({'job':job,'start':t,'end':t+review_time[job]})
        t+=review_time[job]
        completed[job]=t
    return {'scanner':scanner,'ocr_finish':release,'review':reviews,'complete':completed,'makespan':max(completed.values()),'deadlines_met':completed['A']<=13 and completed['B']<=16}
nominal=[schedule(s,r) for s in itertools.permutations('AB') for r in itertools.permutations('AB')]
assert min(s['makespan'] for s in nominal)==16
feasible=[s for s in nominal if s['deadlines_met']]
assert len(feasible)==1 and feasible[0]['complete']=={'A':13,'B':16}
expedited=schedule('AB','AB',a_ocr=4)
assert expedited['complete']=={'A':11,'B':14}
assert 1+4+9+2==16
checks['B25']={'type':'exhaustive resource-order schedules','nominal_schedules':nominal,'expedited_A_first':expedited,'ordinary_A_earliest_worst_case_finish':16,'total_effort_hours':(1+4+6+2)+(1+2+3+3),'limit':'Nominal schedules and a worst-case bound are not probabilities or monetary valuations.'}

scenarios={
    'baseline':{'price':15,'production_cost':10,'tax':0,'damage':3,'admin':0},
    'tax':{'price':20,'production_cost':10,'tax':5,'damage':3,'admin':200},
    'clean':{'price':17,'production_cost':12,'tax':0,'damage':0,'admin':80},
}
for s in scenarios.values():
    s['buyer_surplus']=(22-s['price'])*100
    s['producer_contribution']=(s['price']-s['production_cost']-s['tax'])*100
    s['council_net']=s['tax']*100-s['admin']
    s['nuisance_cost']=s['damage']*100
    s['distribution_sum']=s['buyer_surplus']+s['producer_contribution']+s['council_net']-s['nuisance_cost']
    s['resource_surplus']=2200-s['production_cost']*100-s['nuisance_cost']-s['admin']
    assert s['distribution_sum']==s['resource_surplus']
assert [scenarios[k]['resource_surplus'] for k in ('baseline','tax','clean')]==[900,700,920]
checks['B26']={'type':'transfer/resource reconciliation','scenarios':scenarios,'clean_increment_over_baseline':20}

assert 160/2000==0.08 and 200/2000==0.10
assert 5-1==4
checks['B28']={'type':'assignment arithmetic','assigned_error_rate':160/2000,'unassigned_error_rate':200/2000,'rate_difference_percentage_points':100*(160/2000-200/2000),'assigned_person_assigned_peers':4,'unassigned_person_assigned_peers':5,'limit':'No peer-effect sign, uncertainty interval, or universal-rollout causal effect is inferred.'}

class Receiver:
    def __init__(self):self.keys={};self.reservations=0
    def post(self,key,payload,time,account='acct',route='/reserve'):
        scope=(account,route,key)
        old=self.keys.get(scope)
        if old and time-old['time']<24*3600:
            if old['payload']!=payload:return (409,None)
            return (200,old['reservation'])
        self.reservations+=1
        reservation=f'R{self.reservations}'
        self.keys[scope]={'payload':payload,'time':time,'reservation':reservation}
        return (200,reservation)
attempt_receiver=Receiver()
attempt_receiver.post('A1','E8',0)
attempt_receiver.post('A2','E8',60)
assert attempt_receiver.reservations==2
stable_receiver=Receiver()
first_result=stable_receiver.post('E8','fixed-body',0)
assert stable_receiver.post('E8','fixed-body',60)==first_result
assert stable_receiver.reservations==1
assert stable_receiver.post('E8','changed-body',120)==(409,None)
stable_receiver.post('E8','fixed-body',36*3600)
assert stable_receiver.reservations==2
checks['B29']={'type':'receiver retry/expiration simulation','attempt_keys_one_minute_reservations':2,'stable_key_one_minute_reservations':1,'changed_payload_in_retention_status':409,'stable_key_after_36_hours_total_reservations':2,'mark_before_send_counterexample':{'outbox_marked_sent':True,'crash_before_network_send':True,'remote_effects':0},'limit':'Simulation implements supplied fictional contract, not an actual distributed protocol audit.'}

tables=[]
for both in range(1001):
    cells={'both':both,'A_only':600-both,'B_only':500-both,'neither':1000-600-500+both}
    if min(cells.values())>=0:
        assert sum(cells.values())==1000
        assert cells['both']+cells['A_only']==600
        assert cells['both']+cells['B_only']==500
        tables.append(cells)
assert len(tables)==401
assert tables[0]=={'both':100,'A_only':500,'B_only':400,'neither':0}
assert tables[-1]=={'both':500,'A_only':100,'B_only':0,'neither':400}
assert {t['both']>300 for t in tables}=={False,True}
checks['B30']={'type':'exhaustive feasible2x2-table enumeration','feasible_overlap_values':len(tables),'minimum_overlap':100,'maximum_overlap':500,'low_witness':tables[0],'high_witness':tables[-1],'independence_assumption_overlap':1000*0.6*0.5,'exactly_300_triggers':300>300,'trigger_identified':False}

manual=['B22','B23','B27']
for cid in manual:
    checks[cid]={'type':'manual source-and-rubric consistency review','status':'reviewed during original authoring','dimensions':['No missing fact silently supplied.','Current/observed source scope distinguished from interpretation and publicity.','At least six meaningful essential criteria.','Alternative readings/paths retained where the packet does not discriminate.'],'limit':'Author review, not independent response evaluation.'}

verification={'status':'passed','fixture_origin':'Original synthetic educational fixtures; no real niche facts, generated model responses, or prior benchmark material used.','research':{'performed':False,'reason':'All source packets are fictional and self-contained.'},'schema':{'cases':12,'holdout':12,'constraints':'language-only dictionaries','essential_criteria_min':min(len(r['must_include']) for r in rubrics.values()),'word_count_method':'Python str.split whitespace tokens','word_counts':{c['id']:len(c['prompt'].split()) for c in cases},'source_ids_present':True},'checks':dict(sorted(checks.items())),'file_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ('cases.json','rubric.json')},'handling':'Sealed case-level contents and calculations must remain under sealed/ until freeze.'}
(ROOT/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'passed','holdout_cases':12,'executed_case_checks':len(checks)-len(manual),'manual_source_reviews':len(manual),'min_words':min(len(c['prompt'].split()) for c in cases),'max_words':max(len(c['prompt'].split()) for c in cases)}))
