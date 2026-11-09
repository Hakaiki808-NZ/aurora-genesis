"""Experimental, offline-only quantum research methods for Genesis.

Pure Python CPU statevector reference. Zero cloud calls, no tool registration,
no Aurora privileges, and no claim of quantum advantage.

IMPORTANT: ReferenceAdmission is an isolated test gate, NOT a cryptographic
Aurora authorization proof. The production Aurora Controller must independently
validate admission and dispatch before enabling real quantum services.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import cos, isfinite, pi, sin, sqrt
from cmath import exp
from random import Random
from time import perf_counter
from typing import Any, Mapping

MAX_QUBITS = 6
MAX_SHOTS = 4096
MAX_GRID_POINTS = 25
MAX_EVALUATIONS = 625
MAX_EDGES = 15


class QuantumLabError(ValueError):
    """Input or admission is invalid; no work was performed."""


@dataclass(frozen=True)
class ReferenceAdmission:
    """Host-injected prototype policy only, not actual Aurora authority."""

    enabled: bool = False
    max_qubits: int = 4
    max_shots: int = 1024
    max_evaluations: int = 289


@dataclass(frozen=True)
class MaxCutProblem:
    qubits: int
    edges: tuple[tuple[int, int, float], ...]

    def validate(self) -> None:
        if type(self.qubits) is not int or not 2 <= self.qubits <= MAX_QUBITS:
            raise QuantumLabError(f"qubits must be an integer in [2, {MAX_QUBITS}]")
        if not isinstance(self.edges, tuple) or not 1 <= len(self.edges) <= MAX_EDGES:
            raise QuantumLabError("edges must be a nonempty bounded tuple")
        seen: set[tuple[int, int]] = set()
        for edge in self.edges:
            if not isinstance(edge, tuple) or len(edge) != 3:
                raise QuantumLabError("each edge must be (vertex_i, vertex_j, positive_weight)")
            i, j, weight = edge
            if type(i) is not int or type(j) is not int or not 0 <= i < self.qubits or not 0 <= j < self.qubits or i == j:
                raise QuantumLabError("invalid edge vertices")
            if type(weight) not in (int, float) or not isfinite(weight) or not 0 < weight <= 1000:
                raise QuantumLabError("edge weights must be finite and positive")
            key = tuple(sorted((i, j)))
            if key in seen:
                raise QuantumLabError("duplicate edges are not allowed")
            seen.add(key)


def parse_problem(payload: Mapping[str, Any]) -> MaxCutProblem:
    """Validate an untrusted model-generated payload; reject unknown keys."""
    if not isinstance(payload, Mapping) or set(payload) != {"qubits", "edges"}:
        raise QuantumLabError("problem must contain only qubits and edges")
    raw = payload["edges"]
    if not isinstance(raw, (tuple, list)):
        raise QuantumLabError("edges must be an array")
    # Keep types intact: booleans and numeric strings do not become valid ints.
    problem = MaxCutProblem(payload["qubits"], tuple(tuple(e) if isinstance(e, (tuple, list)) else e for e in raw))
    problem.validate()
    return problem


def _authorize(admission: ReferenceAdmission | None, *, qubits: int, shots: int, evaluations: int) -> None:
    if not isinstance(admission, ReferenceAdmission) or admission.enabled is not True:
        raise QuantumLabError("DENIED: no host-injected local reference admission")
    if type(shots) is not int or not 1 <= shots <= MAX_SHOTS or shots > admission.max_shots:
        raise QuantumLabError("DENIED: shot budget exceeded")
    if type(evaluations) is not int or not 1 <= evaluations <= MAX_EVALUATIONS or evaluations > admission.max_evaluations:
        raise QuantumLabError("DENIED: evaluation budget exceeded")
    if qubits > MAX_QUBITS or qubits > admission.max_qubits:
        raise QuantumLabError("DENIED: qubit budget exceeded")


def _measure(probs: list[float], shots: int, seed: int) -> dict[str, int]:
    rng = Random(seed)
    counts = [0] * len(probs)
    # A seed and independent uniform samples make every test reproducible.
    cumulative = []
    total = 0.0
    for p in probs:
        total += p
        cumulative.append(total)
    for _ in range(shots):
        u = rng.random()
        for idx, threshold in enumerate(cumulative):
            if u <= threshold or idx == len(probs) - 1:
                counts[idx] += 1
                break
    bits = (len(probs) - 1).bit_length()
    return {format(idx, f"0{bits}b"): n for idx, n in enumerate(counts) if n}


def bell_reference(*, admission: ReferenceAdmission | None = None, shots: int = 1000, seed: int = 7) -> dict[str, Any]:
    """Simulate H on qubit 0 followed by controlled-X(0 -> 1)."""
    _authorize(admission, qubits=2, shots=shots, evaluations=1)
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise QuantumLabError("seed must be a bounded integer")
    t0 = perf_counter()
    state = [complex(1, 0), 0j, 0j, 0j]
    # Little-endian: q0 corresponds to the 1 bit of basis index.
    inv_root2 = 1 / sqrt(2)
    state[0], state[1] = (state[0] + state[1]) * inv_root2, (state[0] - state[1]) * inv_root2
    state[1], state[3] = state[3], state[1]
    probabilities = [abs(a)**2 for a in state]
    if abs(sum(probabilities) - 1) > 1e-12:
        raise RuntimeError("state not normalized")
    return {"kind": "bell", "backend": "reference-cpu", "shots": shots, "seed": seed,
            "probabilities": dict(zip(("00", "01", "10", "11"), probabilities)),
            "counts": _measure(probabilities, shots, seed),
            "elapsed_seconds": round(perf_counter() - t0, 6), "cloud_cost_usd": 0,
            "is_quantum_hardware": False}


def _cut_costs(problem: MaxCutProblem) -> list[float]:
    return [sum(weight for i, j, weight in problem.edges if bool(idx & (1 << i)) != bool(idx & (1 << j)))
            for idx in range(1 << problem.qubits)]


def _qaoa_probabilities(costs: list[float], qubits: int, gamma: float, beta: float) -> list[float]:
    n_states = 1 << qubits
    state = [exp(-1j * gamma * value) / sqrt(n_states) for value in costs]
    c, s = cos(beta), sin(beta)
    for bit in range(qubits):
        mask = 1 << bit
        for idx in range(n_states):
            if not idx & mask:
                other = idx | mask
                a, b = state[idx], state[other]
                state[idx] = c * a - 1j * s * b
                state[other] = c * b - 1j * s * a
    probabilities = [abs(a)**2 for a in state]
    if abs(sum(probabilities) - 1) > 1e-9:
        raise RuntimeError("non-unitary QAOA result")
    return probabilities


def _classical_greedy(costs: list[float], qubits: int) -> tuple[float, int]:
    # Deterministic hill climbing from the all-zero cut and its single-bit neighbors.
    starts = [0] + [1 << i for i in range(qubits)]
    best = (float('-inf'), 0)
    evaluations = 0
    for start in starts:
        index = start
        while True:
            candidates = [index] + [index ^ (1 << i) for i in range(qubits)]
            evaluations += len(candidates)
            selected = max(candidates, key=lambda k: (costs[k], -k))
            if selected == index or costs[selected] <= costs[index]:
                break
            index = selected
        if costs[index] > best[0]:
            best = (costs[index], index)
    return best[0], evaluations


def maxcut_reference(problem: MaxCutProblem, *, admission: ReferenceAdmission | None = None,
                     shots: int = 1000, seed: int = 7, grid_points: int = 17) -> dict[str, Any]:
    """One-layer QAOA versus exact enumeration and deterministic greedy baseline.

    CPU statevector parameters are grid searched, so this method does not claim
    advantage or comparable wall clock to real QPUs; shots are sampled only
    for the final chosen state.
    """
    problem.validate()
    if type(grid_points) is not int or not 3 <= grid_points <= MAX_GRID_POINTS:
        raise QuantumLabError("grid_points must be in [3, 25]")
    if type(seed) is not int or not 0 <= seed <= 2**32 - 1:
        raise QuantumLabError("seed must be a bounded integer")
    _authorize(admission, qubits=problem.qubits, shots=shots, evaluations=grid_points**2)
    t0 = perf_counter()
    costs = _cut_costs(problem)
    optimum = max(costs)
    exact_best_bits = [format(idx, f"0{problem.qubits}b") for idx, score in enumerate(costs) if abs(score - optimum) < 1e-9]
    classical_greedy, greedy_evals = _classical_greedy(costs, problem.qubits)
    best_expected, best_gamma, best_beta, best_probs = -float('inf'), 0.0, 0.0, []
    for gi in range(grid_points):
        gamma = (2 * pi * gi) / (grid_points - 1)
        for bi in range(grid_points):
            beta = (pi * bi) / (grid_points - 1)
            probs = _qaoa_probabilities(costs, problem.qubits, gamma, beta)
            expected = sum(p * score for p, score in zip(probs, costs))
            if expected > best_expected:
                best_expected, best_gamma, best_beta, best_probs = expected, gamma, beta, probs
    probability_optimal = sum(p for p, score in zip(best_probs, costs) if abs(score-optimum) < 1e-9)
    counts = _measure(best_probs, shots, seed)
    return {"kind": "maxcut", "backend": "reference-cpu", "qubits": problem.qubits,
            "edges": [list(edge) for edge in problem.edges], "shots": shots, "seed": seed,
            "grid_points": grid_points, "qaoa_parameter_evaluations": grid_points**2,
            "classical_exact_evaluations": 1 << problem.qubits,
            "classical_greedy_evaluations": greedy_evals,
            "classical_optimum": optimum, "classical_best_cuts": exact_best_bits,
            "classical_uniform_mean": sum(costs)/len(costs),
            "classical_greedy_score": classical_greedy,
            "qaoa_expected_score": best_expected,
            "qaoa_probability_optimum": probability_optimal,
            "qaoa_best_gamma": best_gamma, "qaoa_best_beta": best_beta,
            "sample_counts": counts, "elapsed_seconds": round(perf_counter()-t0,6),
            "cloud_cost_usd": 0, "is_quantum_hardware": False,
            "quantum_advantage_claimed": False}


def run_reference_job(payload: Mapping[str, Any], *, admission: ReferenceAdmission | None = None) -> dict[str, Any]:
    """Local-only job dispatcher; rejects additional fields, remote backends, and budgets."""
    if not isinstance(payload, Mapping):
        raise QuantumLabError("job must be an object")
    keys = {"kind", "backend", "shots", "seed", "grid_points", "problem", "max_cost_usd"}
    if set(payload) - keys or not {"kind", "backend", "shots", "seed", "max_cost_usd"}.issubset(payload):
        raise QuantumLabError("invalid quantum job fields")
    if payload["backend"] != "reference-cpu" or type(payload["max_cost_usd"]) not in (int, float) or payload["max_cost_usd"] != 0:
        raise QuantumLabError("DENIED: paid or remote quantum execution unavailable")
    if payload["kind"] == "bell":
        if "problem" in payload or "grid_points" in payload:
            raise QuantumLabError("unexpected Bell job fields")
        return bell_reference(admission=admission, shots=payload["shots"], seed=payload["seed"])
    if payload["kind"] == "maxcut":
        if "problem" not in payload or "grid_points" not in payload:
            raise QuantumLabError("missing Max-Cut fields")
        return maxcut_reference(parse_problem(payload["problem"]), admission=admission,
                                shots=payload["shots"], seed=payload["seed"], grid_points=payload["grid_points"])
    raise QuantumLabError("unsupported job kind")
