#!/usr/bin/env python3
"""File-oriented CLI for the frozen V22 campaign engine."""
from __future__ import annotations
import argparse,importlib.util,json,zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location("v22_campaign",HERE/"campaign.py")
if spec is None or spec.loader is None: raise RuntimeError("cannot load V22 campaign")
campaign=importlib.util.module_from_spec(spec); spec.loader.exec_module(campaign)

def load(path:Path): return json.loads(path.read_text())
def save(path:Path,obj): path.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='cmd',required=True)
    p=sub.add_parser('init'); p.add_argument('root_bundle',type=Path); p.add_argument('--out',type=Path,required=True)
    p=sub.add_parser('plan'); p.add_argument('state',type=Path); p.add_argument('arm',choices=['g1','g2'])
    p=sub.add_parser('record'); p.add_argument('state',type=Path); p.add_argument('arm',choices=['shared','g1','g2']); p.add_argument('evaluations',type=Path,nargs='+'); p.add_argument('--out',type=Path)
    p=sub.add_parser('summary'); p.add_argument('state',type=Path)
    a=ap.parse_args()
    if a.cmd=='init':
        with zipfile.ZipFile(a.root_bundle) as z: m=json.loads(z.read('task-manifest.json'))
        if int(m['parent_quality_milli'])!=0: raise ValueError('R1 root quality must be 0')
        s=campaign.init_state(task_id=m['task_id'],allowed_source_path=m['allowed_source_path'],
          root_tree_digest=m['parent_tree_digest'],root_source_sha256=m['parent_source_sha256'],root_node_id=m['parent_node_id'])
        save(a.out,s); print(json.dumps(campaign.summary(s),indent=2,sort_keys=True)); return
    s=load(a.state)
    if a.cmd=='plan': print(json.dumps(campaign.plan_next(s,a.arm),indent=2,sort_keys=True)); return
    if a.cmd=='summary': print(json.dumps(campaign.summary(s),indent=2,sort_keys=True)); return
    rows=[]
    for p in a.evaluations:
        e=load(p)
        if not e.get('represented_observation'): raise ValueError(f'{p}: not a represented observation')
        rows.append({'parent_node_id':e['parent_node_id'],'tree_digest':e['tree_digest'],'source_sha256':e['source_sha256'],
          'proposal_patch_sha256':e['proposal_patch_sha256'],'quality_milli':e['quality_milli']})
    campaign.record_round(s,arm=a.arm,parent_results=rows); save(a.out or a.state,s)
    print(json.dumps(campaign.summary(s),indent=2,sort_keys=True))
if __name__=='__main__': main()
