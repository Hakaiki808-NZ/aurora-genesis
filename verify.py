from __future__ import annotations
import subprocess, sys, platform, json
from pathlib import Path

ROOT=Path(__file__).resolve().parent
TESTS=['tests.acceptance','tests.regression','tests.refinement','tests.hardening','tests.api_test','tests.constitutional','tests.constitution_stress','tests.guardian_hardening_v102','tests.phases.phase2_integration','tests.phases.phase3_adversarial','tests.phases.phase4_recovery_integration']

def main():
    results=[]
    for t in TESTS:
        p=subprocess.run([sys.executable,'-m',t],cwd=ROOT,text=True,capture_output=True)
        results.append({'test':t,'ok':p.returncode==0,'stdout':p.stdout.strip(),'stderr':p.stderr.strip()})
        print(f"[{ 'PASS' if p.returncode==0 else 'FAIL' }] {t}")
        if p.stdout.strip(): print(p.stdout.strip())
        if p.returncode!=0:
            if p.stderr.strip(): print(p.stderr.strip(),file=sys.stderr)
            raise SystemExit(p.returncode)
    out={'model':'Genesis v0.1','version':'v0.1','python':platform.python_version(),'platform':platform.platform(),'results':results}
    (ROOT/'verification.json').write_text(json.dumps(out,indent=2),encoding='utf-8')
    print('VERIFICATION=PASS')

if __name__=='__main__': main()
