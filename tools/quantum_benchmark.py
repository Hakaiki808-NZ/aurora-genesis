"""Run repeatable, no-cloud-cost quantum/classical Max-Cut comparisons.

Run from repo root: python -m tools.quantum_benchmark
Produces console JSON. No credentials or remote services.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from genesis.quantum_lab import MaxCutProblem, ReferenceAdmission, maxcut_reference

PERMIT = ReferenceAdmission(enabled=True, max_qubits=6, max_shots=2048, max_evaluations=289)
GRAPHS = {
    "triangle3": MaxCutProblem(3, ((0,1,2.0),(1,2,2.0),(0,2,1.0))),
    "square4": MaxCutProblem(4, ((0,1,1.0),(1,2,1.0),(2,3,1.0),(3,0,1.0))),
    "ring5_chords": MaxCutProblem(5, ((0,1,1.0),(1,2,1.0),(2,3,1.0),(3,4,1.0),(4,0,1.0),(0,2,0.5),(1,3,0.5))),
    "bipartite6": MaxCutProblem(6, tuple((i,j,1.0) for i in range(3) for j in range(3,6))),
}

def run() -> dict:
    tests=[]
    for name, graph in GRAPHS.items():
        out=maxcut_reference(graph,admission=PERMIT,shots=1024,seed=20261107,grid_points=17)
        tests.append({"name":name,"qubits":out["qubits"],"edges":len(graph.edges),
                      "classical_optimum":out["classical_optimum"],
                      "classical_greedy":out["classical_greedy_score"],
                      "uniform_random_expectation":out["classical_uniform_mean"],
                      "qaoa_expected":round(out["qaoa_expected_score"],6),
                      "qaoa_p_optimum":round(out["qaoa_probability_optimum"],6),
                      "classical_exact_evaluations":out["classical_exact_evaluations"],
                      "qaoa_grid_evaluations":out["qaoa_parameter_evaluations"],
                      "elapsed_seconds":out["elapsed_seconds"]})
    return {"type":"reference-cpu-only", "backend":"Python statevector (no QPU)",
            "date_utc":datetime.now(timezone.utc).isoformat(),
            "quantum_advantage_demonstrated":False,
            "cost_usd":0,"graphs":tests}

if __name__=='__main__':
    print(json.dumps(run(),indent=2))
