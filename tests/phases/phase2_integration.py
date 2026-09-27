from __future__ import annotations

import tempfile
from pathlib import Path
from genesis import Genesis
from genesis.capabilities import CapabilityController
from genesis.engine_boundary import EngineReceipt


def run():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        calls={"n":0}
        g=Genesis(state_path=root/'state.db', workspace=root/'ws', enable_ollama=False)
        assert g.identity['model_name']=='Genesis'
        assert g.VERSION=='v0.1'
        health=g.self_check(); assert health['ok'],health
        assert health['checks']['guardian_topology']
        assert health['checks']['engine_separation']
        assert g.policy.summary()['name']=='Genesis Model Constitution'
        assert g.policy.integrity_ok

        item=g.store.learn_fact('phase2 beacon','NORTHSTAR',truth_state='VERIFIED')
        assert item['truth_state']=='VERIFIED'
        assert g.store.get_fact('phase2 beacon')['truth_state']=='VERIFIED'
        assert g.store.set_fact_truth_state('phase2 beacon','DISPUTED')
        assert g.store.get_fact('phase2 beacon')['truth_state']=='DISPUTED'

        cap=CapabilityController('C5')
        assert cap.evaluate({'type':'engine_authority'}).verdict=='deny'
        assert cap.evaluate({'type':'sim','capability_level':'C4'},human_approved=False).verdict=='require_approval'
        assert cap.evaluate({'type':'sim','capability_level':'C5'},human_approved=True).verdict=='deny'
        assert cap.evaluate({'type':'sim','capability_level':'C5','max_actions':3},human_approved=True).verdict=='allow'

        finding=g.guardians.evaluate({'type':'simulated','policy_flags':['intentional_severe_harm']},{'human_approved':True,'trajectory':[]})
        assert finding['verdict']=='deny'
        assert finding['alpha']['guardian_type']=='Alpha'

        out=g.respond('Calculate 6 * 7')
        assert '42' in out,out
        tx=g.store.recent_actions(1)[0]
        assert tx['state']=='COMMITTED',tx

        def external_call():
            calls['n']+=1
            return 'executed'
        g.register_tool('external_test','external action',external_call,mutating=True,external_side_effect=True,policy_declared=True)
        from genesis.types import Candidate
        c=Candidate('external','',200,'test',action={'type':'tool','name':'external_test','args':{}})
        msg,ok,note=g.cognition.act(c,authorization='explicit')
        assert ok and 'Prepared Aurora Engine request' in msg,(msg,ok,note)
        assert calls['n']==0
        tx=g.store.recent_actions(1)[0]
        assert tx['state']=='PREPARED' and tx['engine_request_id'],tx

        req_id=tx['engine_request_id']
        from genesis.engine_boundary import EngineRequest
        req=EngineRequest(req_id,'Genesis v0.1','Aurora pre-v0.1','C4',{'type':'tool'},'allow')
        assert g.engine_boundary.validate_receipt(req,EngineReceipt(req_id,'COMMITTED','r1'))
        assert not g.engine_boundary.validate_receipt(req,EngineReceipt('wrong','COMMITTED','r2'))
        g.close()
    print('PHASE2_INTEGRATION=PASS')

if __name__=='__main__': run()
