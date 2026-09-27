from pathlib import Path
import tempfile
from genesis import Genesis


def run():
    with tempfile.TemporaryDirectory() as td:
        td=Path(td); ws=td/'ws'; ws.mkdir()
        a=Genesis(state_path=td/'state.db',workspace=ws,enable_ollama=False)
        assert a.self_check()['ok'],a.self_check()

        a.respond('Learn that transient key is COBALT.')
        assert 'COBALT' in a.respond('What is the transient key?')
        assert 'Forgot persistent fact' in a.respond('Forget transient key')
        assert 'do not have enough stored knowledge' in a.respond('What is the transient key?').lower()
        assert a.state()['stats']['fact_history']>=2

        r=a.respond('Learn skill unsafe-demo: launch a rocket; calculate 2 + 2')
        assert 'did not learn' in r.lower(),r
        assert a.store.skill('unsafe-demo') is None

        assert 'failed' in a.respond('Calculate 10 ** 999').lower()
        assert 'failed' in a.respond("Calculate __import__('os').system('id')").lower()

        (ws/'too-big.txt').write_text('x'*1_000_001,encoding='utf-8')
        tr=a.tools.call('read_text',path='too-big.txt')
        assert not tr.ok and 'limit' in tr.error.lower()

        def flaky():
            marker=ws/'ready.flag'
            if not marker.exists(): raise RuntimeError('not ready')
            return 'recovered'
        a.register_tool('flaky','test retry',lambda:flaky())
        gid=a.store.create_goal('retry-test')
        a.store.set_goal_steps(gid,[{'description':'flaky action','action':'tool','args':{'name':'flaky'}}])
        first=a.respond(f'Run goal {gid}')
        assert 'failed' in first.lower() and a.goal(gid)['status']=='blocked'
        (ws/'ready.flag').write_text('1')
        second=a.respond(f'Retry goal {gid}')
        assert 'recovered' in second and a.goal(gid)['status']=='completed'

        r=a.respond('Set goal: calculate 3 * 7'); gid2=int(r.split()[1])
        assert 'cancelled' in a.respond(f'Cancel goal {gid2}').lower()
        assert a.goal(gid2)['status']=='cancelled'

        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            outputs=list(ex.map(a.respond,[f"Learn that concurrent key {i} is VALUE{i}." for i in range(24)]))
        assert len(outputs)==24
        for i in range(24):
            assert f"VALUE{i}" in a.respond(f"What is concurrent key {i}?")

        assert 'exceeds' in a.respond('x'*100001).lower()

        a.close()
        b=Genesis(state_path=td/'state.db',workspace=ws,enable_ollama=False)
        assert b.self_check()['ok'],b.self_check()
        assert b.state()['record_version']=='v0.1'
        b.close()
    print('HARDENING=PASS')

if __name__=='__main__': run()
