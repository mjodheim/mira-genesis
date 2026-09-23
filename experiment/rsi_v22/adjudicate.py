#!/usr/bin/env python3
"""Final frozen V22 G1/G2 adjudication from completed campaign states."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from utility import TaskOutcome,global_utility,strictly_better

def arm_outcome(state,arm):
    a=state['arms'][arm]
    if not a['stopped']: raise ValueError(f"{state['task_id']} {arm} is not stopped")
    best=int(a['best_quality_milli'])
    return TaskOutcome(best_quality_milli=best,represented_requests=int(a['represented_requests']),
        rounds=int(a['rounds']),solved_without_regression=(best==1000))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('states',type=Path,nargs=3); ap.add_argument('--out',type=Path); a=ap.parse_args()
    states=[json.loads(p.read_text()) for p in a.states]
    if len({s['task_id'] for s in states})!=3: raise ValueError('exactly three distinct tasks required')
    rows=[]; g1=[]; g2=[]; wins=0
    for s in states:
        x=arm_outcome(s,'g1'); y=arm_outcome(s,'g2'); g1.append(x); g2.append(y)
        ux=x.process_utility(); uy=y.process_utility(); win=strictly_better(uy,ux); wins+=int(win)
        rows.append({'task_id':s['task_id'],'g1_process_utility':ux,'g2_process_utility':uy,'g2_strictly_better':win,
          'g1_best_quality_milli':x.best_quality_milli,'g2_best_quality_milli':y.best_quality_milli,
          'g1_requests':x.represented_requests,'g2_requests':y.represented_requests,'g1_rounds':x.rounds,'g2_rounds':y.rounds})
    u1=global_utility(g1); u2=global_utility(g2); solved=sum(int(x.solved_without_regression) for x in g2)
    positive=(solved==3 and wins>=2 and strictly_better(u2,u1))
    result={'schema':'mira-genesis-rsi-v22-final-adjudication-v1','tasks':rows,'g1_global_utility':u1,'g2_global_utility':u2,
      'g2_tasks_solved_without_regression':solved,'g2_strict_process_wins':wins,'v22_positive':positive}
    text=json.dumps(result,indent=2,sort_keys=True)+'\n'; print(text,end='')
    if a.out: a.out.write_text(text)
if __name__=='__main__': main()
