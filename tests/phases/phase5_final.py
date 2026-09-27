from __future__ import annotations
import json, subprocess, sys, tempfile, time
from pathlib import Path
from genesis import Genesis
from genesis.retrieval import Retriever

ROOT=Path(__file__).resolve().parents[2]


def benchmark() -> dict:
    with tempfile.TemporaryDirectory() as td:
        root=Path(td)
        g=Genesis(state_path=root/'bench.db',workspace=root/'ws',enable_ollama=False)
        for i in range(1500):
            g.store.learn_fact(f'benchmark key {i}',f'value token group {i%50} item {i}',confidence=0.9)
        r=Retriever(g.store)
        queries=[f'benchmark key {i%1500}' for i in range(300)]
        t0=time.perf_counter()
        for q in queries:
            hit=r.search(q,limit=5)
            assert hit
        elapsed=time.perf_counter()-t0
        g.close()
        return {'queries':len(queries),'facts':1500,'elapsed_seconds':elapsed,'queries_per_second':len(queries)/elapsed}


def precheck():
    g=None
    with tempfile.TemporaryDirectory() as td:
        root=Path(td); g=Genesis(state_path=root/'state.db',workspace=root/'ws',enable_ollama=False)
        assert g.VERSION=='v0.1'
        assert g.identity['model_name']=='Genesis'
        assert g.identity['system_role']=='The Model'
        assert g.identity['minimum_engine']=='Aurora pre-v0.1'
        assert g.self_check()['ok'],g.self_check()
        assert not (ROOT/'genesis'/'engine.py').exists(), 'Model package must not masquerade as the Aurora Engine'
        assert (ROOT/'genesis'/'engine_boundary.py').exists()
        assert g.policy.summary()['name']=='Genesis Model Constitution'
        assert len(g.guardians.omegas)>=4
        assert g.capabilities.granted_level.startswith('C')
        g.close()
    print('PHASE5_PRECHECK=PASS')


def run_all():
    modules=[
        'tests.phases.phase2_integration',
        'tests.phases.phase3_adversarial',
        'tests.phases.phase4_recovery_integration',
    ]
    for mod in modules:
        p=subprocess.run([sys.executable,'-m',mod],cwd=ROOT,text=True,capture_output=True)
        if p.returncode:
            print(p.stdout); print(p.stderr,file=sys.stderr); raise SystemExit(p.returncode)
    p=subprocess.run([sys.executable,'verify.py'],cwd=ROOT,text=True,capture_output=True)
    if p.returncode:
        print(p.stdout); print(p.stderr,file=sys.stderr); raise SystemExit(p.returncode)
    print('PHASE5_FULL_VERIFICATION=PASS')


if __name__=='__main__':
    mode=sys.argv[1] if len(sys.argv)>1 else 'all'
    if mode in {'precheck','all'}: precheck()
    if mode in {'benchmark','all'}: print('BENCHMARK='+json.dumps(benchmark(),sort_keys=True))
    if mode in {'verify','all'}: run_all()
