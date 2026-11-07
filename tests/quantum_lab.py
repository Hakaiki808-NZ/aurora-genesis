"""stdlib-only, offline quantum lab acceptance tests. Run: python -m tests.quantum_lab"""
from __future__ import annotations
import math
import unittest
from genesis.quantum_lab import (MAX_EVALUATIONS, MaxCutProblem, QuantumLabError,
                                 ReferenceAdmission, bell_reference, maxcut_reference,
                                 parse_problem, run_reference_job)

PERMIT = ReferenceAdmission(enabled=True, max_qubits=6, max_shots=4096, max_evaluations=MAX_EVALUATIONS)
TRIANGLE = MaxCutProblem(3, ((0, 1, 2.0), (1, 2, 2.0), (0, 2, 1.0)))


class QuantumLabTests(unittest.TestCase):
    def test_default_deny_and_seeded_bell(self):
        with self.assertRaises(QuantumLabError): bell_reference()
        result = bell_reference(admission=PERMIT, shots=1000, seed=11)
        self.assertAlmostEqual(result['probabilities']['00'], 0.5)
        self.assertAlmostEqual(result['probabilities']['11'], 0.5)
        self.assertEqual(result['probabilities']['01'], 0)
        self.assertEqual(result['probabilities']['10'], 0)
        self.assertEqual(sum(result['counts'].values()), 1000)
        self.assertEqual(set(result['counts']), {'00', '11'})
        self.assertEqual(result['counts'], bell_reference(admission=PERMIT, shots=1000, seed=11)['counts'])

    def test_maxcut_classical_baselines_and_normalization(self):
        result = maxcut_reference(TRIANGLE, admission=PERMIT, shots=1000, seed=31, grid_points=17)
        self.assertEqual(result['classical_optimum'], 4)
        self.assertEqual(result['classical_uniform_mean'], 2.5)
        self.assertEqual(result['classical_greedy_score'], 4)
        self.assertGreater(result['qaoa_expected_score'], 3.5)
        self.assertLessEqual(result['qaoa_expected_score'], result['classical_optimum'] + 1e-9)
        self.assertGreater(result['qaoa_probability_optimum'], 0.75)
        self.assertLessEqual(result['qaoa_probability_optimum'], 1)
        self.assertEqual(sum(result['sample_counts'].values()), 1000)
        self.assertFalse(result['quantum_advantage_claimed'])
        self.assertEqual(result['cloud_cost_usd'], 0)

    def test_four_vertex_problem(self):
        square=MaxCutProblem(4, ((0,1,1.),(1,2,1.),(2,3,1.),(3,0,1.)))
        out = maxcut_reference(square, admission=PERMIT, grid_points=9, shots=200)
        self.assertEqual(out['classical_optimum'], 4)
        self.assertGreaterEqual(out['qaoa_expected_score'], 2)
        self.assertEqual(out['classical_exact_evaluations'], 16)

    def test_bad_problem_rejected(self):
        bad = [
            {'qubits':True,'edges':[[0,1,1]]},
            {'qubits':3,'edges':[[0,3,1]]},
            {'qubits':3,'edges':[[1,1,1]]},
            {'qubits':3,'edges':[[0,1,1],[1,0,2]]},
            {'qubits':3,'edges':[[0,1,float('nan')]]},
            {'qubits':3,'edges':[[0,1,-1]]},
            {'qubits':3,'edges':[[0,1,True]]},
            {'qubits':3,'edges':[[0,1,'1']]},
            {'qubits':3,'edges':[[0,1,1]],'extra':'injection'},
        ]
        for data in bad:
            with self.subTest(data=str(data)), self.assertRaises(QuantumLabError):parse_problem(data)

    def test_remote_cost_injection_and_budget_rejected(self):
        base = {'kind':'bell','backend':'reference-cpu','shots':100,'seed':7,'max_cost_usd':0}
        accepted = run_reference_job(base, admission=PERMIT)
        self.assertEqual(accepted['backend'],'reference-cpu')
        for change in ({'backend':'aws-braket-qpu'}, {'max_cost_usd':1},
                       {'shots':999999}, {'shots':True}, {'seed':-1},
                       {'evil':'command'}, {'kind':'unknown'}, {'max_cost_usd':float('nan')}):
            with self.subTest(change=change), self.assertRaises(QuantumLabError):
                run_reference_job({**base,**change},admission=PERMIT)
        with self.assertRaises(QuantumLabError):run_reference_job(base)

    def test_maxcut_boundaries(self):
        problem = parse_problem({'qubits':3,'edges':[[0,1,2],[1,2,2],[0,2,1]]})
        self.assertEqual(problem,TRIANGLE)
        with self.assertRaises(QuantumLabError):
            maxcut_reference(problem,admission=PERMIT,grid_points=26)
        with self.assertRaises(QuantumLabError):
            maxcut_reference(problem,admission=ReferenceAdmission(enabled=True,max_qubits=2))
        with self.assertRaises(QuantumLabError):
            maxcut_reference(problem,admission=ReferenceAdmission(enabled=True,max_qubits=6,max_evaluations=10))

    def test_no_actual_engine_or_cloud_claim(self):
        out = maxcut_reference(TRIANGLE,admission=PERMIT,grid_points=7,shots=100)
        self.assertFalse(out['is_quantum_hardware'])
        self.assertFalse(out['quantum_advantage_claimed'])
        self.assertEqual(out['cloud_cost_usd'],0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
