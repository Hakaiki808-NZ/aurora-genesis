from pathlib import Path
import tempfile
from genesis import Genesis


def run():
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); ws=td/'ws'; ws.mkdir()
        a=Genesis(state_path=td/'state.db',workspace=ws)

        # Natural singular/plural article handling and multi-hop inference.
        a.respond('Whales are mammals.')
        a.respond('Mammals are animals.')
        r=a.respond('Is a whale an animal?')
        assert r.startswith('Yes.'),r
        assert '(inferred;' in r,r

        # Workspace knowledge ingestion becomes persistent model knowledge.
        (ws/'knowledge.txt').write_text('Orion is a constellation. Constellation is a sky object.\nThe project beacon is LUMEN.',encoding='utf-8')
        r=a.respond('Ingest file knowledge.txt')
        assert 'learned' in r.lower(),r
        assert 'LUMEN' in a.respond('What is the project beacon?')
        assert a.respond('Is Orion a sky object?').startswith('Yes.')

        # Learned multi-step executable skill.
        r=a.respond('Learn skill proof: calculate 6 * 7; write note skill.txt saying skill-complete')
        assert 'skill proof' in r.lower(),r
        r=a.respond('Use skill proof')
        assert '42' in r and "'bytes': 14" in r
        assert (ws/'skill.txt').read_text(encoding='utf-8')=='skill-complete'

        # Chosen action occurs after decision persistence, and outcome is reflected.
        t=a.respond_with_trace('Calculate 100 / 4')
        assert t['answer']=='25.0'
        assert t['trace']['outcome']=='success'
        last=a.state()['last_decision']
        assert last['chosen_action']=='calculate'

        # Failed tools remain bounded and are reflected as failures.
        t=a.respond_with_trace("Calculate __import__('os').system('id')")
        assert t['trace']['outcome']=='failure'
        assert 'Tool failed' in t['answer']

        # Goal state is resumable and inspectable.
        r=a.respond('Set goal: calculate 12 * 12')
        gid=int(r.split()[1]); assert any(g['id']==gid for g in a.state()['active_goals'])
        assert '144' in a.respond(f'Continue goal {gid}')
        assert not any(g['id']==gid for g in a.state()['active_goals'])

        a.close()
    print('REFINEMENT=PASS')

if __name__=='__main__': run()
