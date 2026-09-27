from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
import random
import tempfile
import time

from genesis import Genesis
from genesis.engine_boundary import ModelAuthorizationProof
from genesis.guardians import GuardianCouncil, GuardianFinding
from genesis.intent import IntentCapsule
from genesis.kernel import ConstitutionalKernel
from genesis.types import Candidate


def _approval_bundle(g: Genesis, action: dict):
    ctx=g.cognition._gate_context(action,human_approved=True,source_trust='trusted')
    capsule=ctx['intent_capsule']
    cap=ctx['capability_decision']
    policy=g.policy.evaluate_action(action,authorization='explicit',source_trust='trusted',stage='guardian_hardening')
    kernel=g.cognition.kernel.evaluate(ctx['effective_action'],capsule,human_approved=True)
    guardian=g.guardians.evaluate(ctx['effective_action'],ctx)
    return ctx,capsule,cap,policy,kernel,guardian


def run():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); ws=root/'ws'; ws.mkdir()
        calls={'direct':0,'goal':0,'skill':0}
        g=Genesis(state_path=root/'state.db',workspace=ws,enable_ollama=False)
        assert g.self_check()['ok'],g.self_check()
        assert g.capabilities.granted_level=='C4',g.capabilities.granted_level

        action={'type':'tool','name':'x','external_side_effect':True,'policy_declared':True,
                'affected_entities':['account-A'],'objective':'send approved update'}
        c1=IntentCapsule.from_action(action,{'human_approved':True,'intent_id':'intent-fixed','trajectory_id':'traj-fixed','source_trust':'trusted'})
        c2=IntentCapsule.from_action(action,{'human_approved':True,'intent_id':'intent-fixed','trajectory_id':'traj-fixed','source_trust':'trusted'})
        assert c1.digest()==c2.digest()
        changed=IntentCapsule.from_action({**action,'objective':'different'}, {'human_approved':True,'intent_id':'intent-fixed','trajectory_id':'traj-fixed','source_trust':'trusted'})
        assert changed.digest()!=c1.digest()
        assert c1.authorization_basis=='explicit_human'
        assert 'external_side_effect' in c1.expected_side_effects

        jury=GuardianCouncil()
        mechanisms={x.mechanism for x in jury.omegas}
        assert len(jury.omegas)>=7 and len(mechanisms)>=6,mechanisms
        ordinary=jury.challenge.evaluate({'type':'response'},{'intent_capsule':IntentCapsule.from_action(None,{})})
        assert ordinary.verdict=='abstain',ordinary
        ambiguous=jury.evaluate({'type':'sim','policy_declared':True,'policy_flags':['authority_ambiguous']},{'human_approved':True,'trajectory':[]})
        assert ambiguous['verdict']=='uncertain',ambiguous
        assert ambiguous['challenge']['verdict']=='uncertain'

        class BrokenSafety:
            guardian_id='omega-safety'; specialty='safety'; mechanism='fault_injected'
            def evaluate(self,action,context=None):
                return GuardianFinding('Omega',self.guardian_id,'allow','fault injection: incorrect allow',(),self.mechanism)
        jury2=GuardianCouncil()
        jury2.omegas=tuple(BrokenSafety() if x.guardian_id=='omega-safety' else x for x in jury2.omegas)
        compromised=jury2.evaluate({'type':'sim','policy_declared':True,'policy_flags':['intentional_severe_harm']},{'human_approved':True,'trajectory':[]})
        assert compromised['verdict']=='uncertain',compromised
        assert compromised['challenge']['verdict']=='uncertain'

        class BrokenChallenge:
            guardian_id='omega-challenge'; specialty='challenge'; mechanism='fault_injected'
            def evaluate(self,action,context=None):
                return GuardianFinding('Omega',self.guardian_id,'abstain','fault injection',(),self.mechanism)
        jury3=GuardianCouncil(); jury3.challenge=BrokenChallenge()
        still_denied=jury3.evaluate({'type':'sim','policy_declared':True,'policy_flags':['intentional_severe_harm']},{'human_approved':True,'trajectory':[]})
        assert still_denied['verdict']=='deny',still_denied

        local=jury.evaluate({'type':'sim','policy_declared':True,'policy_flags':['authority_ambiguous','evidence_conflict']},{'human_approved':True,'trajectory':[]})
        assert not local['hybrid_used'],local
        cross=jury.evaluate({'type':'sim','policy_declared':True,'policy_flags':['authority_ambiguous']},{'human_approved':True,'trajectory':[],'foreign_portfolio':'privacy'})
        assert cross['hybrid_used'] and cross['foreign_portfolio']=='privacy',cross
        bad_cross=jury.evaluate({'type':'sim','policy_declared':True},{'human_approved':True,'trajectory':[],'foreign_portfolio':['privacy','finance']})
        assert bad_cross['verdict']=='deny' and not bad_cross['hybrid_used'],bad_cross

        kernel=ConstitutionalKernel()
        for typ in ['engine_authority','supreme_authority','guardian_bypass','constitution_bypass','engine_handler_install']:
            a={'type':typ,'capability_level':'C5','max_actions':1}
            cap=IntentCapsule.from_action(a,{'human_approved':True,'source_trust':'trusted'})
            d=kernel.evaluate(a,cap,human_approved=True)
            assert d.verdict=='deny',(typ,d)
        assert kernel.evaluate({'type':'tool','external_side_effect':True},None,human_approved=True).verdict=='deny'
        untrusted=IntentCapsule.from_action({'type':'tool','external_side_effect':True},{'human_approved':True,'source_trust':'untrusted'})
        assert kernel.evaluate({'type':'tool','external_side_effect':True},untrusted,human_approved=True).verdict=='deny'
        trusted=IntentCapsule.from_action({'type':'tool','external_side_effect':True},{'human_approved':False,'source_trust':'trusted'})
        assert kernel.evaluate({'type':'tool','external_side_effect':True},trusted,human_approved=False).verdict=='require_approval'

        uncertain_action={'type':'sim','policy_declared':True,'consequential':True,'capability_level':'C4','policy_flags':['high_impact_uncertainty']}
        ctx,capsule,cap,policy,kd,gd=_approval_bundle(g,uncertain_action)
        assert gd['verdict']=='uncertain',gd
        try:
            g.engine_boundary.issue_authorization_proof(action=uncertain_action,capsule=capsule,capability=cap.required_level,
                constitution_sha256=g.policy.sha256,guardian=gd,kernel=kd,policy=policy)
        except ValueError:
            pass
        else:
            raise AssertionError('MAP issued despite material uncertainty')

        def ext_direct():
            calls['direct']+=1; return 'SHOULD_NOT_RUN_IN_GENESIS'
        g.register_tool('external_hardened','external hardened test',ext_direct,mutating=True,external_side_effect=True,policy_declared=True)
        external={'type':'tool','name':'external_hardened','args':{},'external_side_effect':True}
        ctx,capsule,cap,policy,kd,gd=_approval_bundle(g,external)
        assert all(x=='allow' for x in [cap.verdict,policy.verdict,kd.verdict,gd['verdict']]),(cap,policy,kd,gd)
        proof=g.engine_boundary.issue_authorization_proof(action=external,capsule=capsule,capability=cap.required_level,
            constitution_sha256=g.policy.sha256,guardian=gd,kernel=kd,policy=policy,ttl_seconds=30)
        assert g.engine_boundary.verify_authorization_proof(proof,external)
        assert not g.engine_boundary.verify_authorization_proof(proof,{**external,'args':{'changed':True}})
        tampered=proof.record(); tampered['capability']='C5'
        assert not g.engine_boundary.verify_authorization_proof(tampered,external)
        req=g.engine_boundary.prepare(external,'C4','allow',proof)
        assert req.authorization_proof and calls['direct']==0
        try:
            g.engine_boundary.prepare(external,'C4','allow',proof)
        except ValueError:
            pass
        else:
            raise AssertionError('MAP replay was accepted')

        short=g.engine_boundary.issue_authorization_proof(action=external,capsule=capsule,capability=cap.required_level,
            constitution_sha256=g.policy.sha256,guardian=gd,kernel=kd,policy=policy,ttl_seconds=1)
        time.sleep(1.05)
        assert not g.engine_boundary.verify_authorization_proof(short,external)

        c=Candidate('external','',200,'hardening direct',action={'type':'tool','name':'external_hardened','args':{}})
        msg,ok,note=g.cognition.act(c,authorization='explicit')
        assert ok and 'Prepared Aurora Engine request' in msg,(msg,ok,note)
        assert calls['direct']==0

        def ext_goal(): calls['goal']+=1; return 'BAD'
        g.register_tool('goal_external','goal external',ext_goal,mutating=True,external_side_effect=True,policy_declared=True)
        gid=g.store.create_goal('guardian-hardening-goal')
        g.store.set_goal_steps(gid,[{'description':'external step','action':'tool','args':{'name':'goal_external'}}])
        out=g.respond(f'Run goal {gid}')
        assert calls['goal']==0,out
        assert g.goal(gid)['status']=='blocked',g.goal(gid)
        assert 'approval' in out.casefold() or 'paused' in out.casefold(),out

        def ext_skill(): calls['skill']+=1; return 'BAD'
        g.register_tool('skill_external','skill external',ext_skill,mutating=True,external_side_effect=True,policy_declared=True)
        g.store.learn_skill('manual-external','test',[{'description':'external skill step','action':'tool','args':{'name':'skill_external'}}],source='test')
        out,ok=g.cognition._execute_skill('manual-external')
        assert not ok and calls['skill']==0,out
        assert 'approval' in out.casefold() or 'paused' in out.casefold(),out

        undeclared={'type':'simulated-new','external_side_effect':True,'capability_level':'C4'}
        capx=IntentCapsule.from_action(undeclared,{'human_approved':True,'source_trust':'trusted'})
        assert 'undeclared_consequential_policy' in capx.uncertainties,capx
        gx=jury.evaluate(undeclared,{'human_approved':True,'trajectory':[],'intent_capsule':capx})
        assert gx['verdict']=='uncertain',gx

        rng=random.Random(27092026)
        hard=['intentional_severe_harm','coercive','unauthorized','secret_exfiltration','self_preservation','blocks_shutdown','constitution_bypass','policy_self_exception']
        soft=['authority_ambiguous','high_impact_uncertainty','evidence_conflict','semantic_uncertainty']
        for _ in range(20000):
            flags=[]
            if rng.random()<0.55: flags.append(rng.choice(hard))
            if rng.random()<0.45: flags.append(rng.choice(soft))
            a={'type':'sim','policy_declared':True,'policy_flags':flags,'consequential':bool(flags)}
            r=jury.evaluate(a,{'human_approved':bool(rng.getrandbits(1)),'trajectory':[]})
            if set(flags)&set(hard): assert r['verdict'] in {'deny','uncertain'},(flags,r)
            if set(flags)&set(soft): assert r['verdict']!='allow',(flags,r)

        keys=set(proof.record())
        forbidden={'prompt','reasoning','chain_of_thought','objective','evidence','assumptions','uncertainties','guardian_findings'}
        assert not keys&forbidden,keys&forbidden

        g.close()
    print('GUARDIAN_HARDENING_V102=PASS random_cases=20000 direct_goal_skill_bypass=blocked map_tamper_replay_expiry=blocked')


if __name__=='__main__':
    run()
