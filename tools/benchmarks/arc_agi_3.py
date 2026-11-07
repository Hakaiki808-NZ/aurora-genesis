"""Fail-closed ARC-AGI-3 runner for the Genesis research model.

A valid harness run is not a proof of a trained Genesis model, and a
third-party model or random agent must never silently replace Genesis.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from unittest.mock import patch


class BenchmarkBlocked(RuntimeError):
    """A missing verification gate or invalid action prevents scoring."""


def frame_payload(observation):
    if observation is None or not hasattr(observation, "frame"):
        raise BenchmarkBlocked("missing_observation_frame")
    frames = [x.tolist() if hasattr(x, "tolist") else x for x in observation.frame]
    state = getattr(observation, "state", None)
    payload = {
        "frame": frames,
        "state": getattr(state, "name", str(state)),
        "levels_completed": getattr(observation, "levels_completed", None),
        "win_levels": getattr(observation, "win_levels", None),
    }
    if len(json.dumps(payload).encode("utf-8")) > 90000:
        raise BenchmarkBlocked("observation_exceeds_genesis_input_limit")
    return payload


def make_prompt(game, observation, actions, history):
    if not actions:
        raise BenchmarkBlocked("no_available_actions")
    return json.dumps({
        "game": game,
        "observation": frame_payload(observation),
        "actions": [{"name": a.name, "requires_xy": a.is_complex()} for a in actions],
        "previous_actions": history[-8:],
        "instructions": (
            "Explore an unfamiliar environment, infer the goal and choose one "
            "permitted action. Reply with only a JSON object, for example "
            '{"action":"ACTION1"} or {"action":"ACTION6","x":0,"y":0}. '
            "Do not invent available actions or game outcomes."
        ),
    }, separators=(",", ":"))


def parse_decision(raw, actions):
    try:
        proposal = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise BenchmarkBlocked("model_did_not_emit_action_json") from exc
    if not isinstance(proposal, dict) or not isinstance(proposal.get("action"), str):
        raise BenchmarkBlocked("invalid_action_schema")
    allowed = {action.name: action for action in actions}
    if proposal["action"] not in allowed:
        raise BenchmarkBlocked("model_selected_unavailable_action")
    action = allowed[proposal["action"]]
    if action.is_complex():
        if set(proposal) != {"action", "x", "y"}:
            raise BenchmarkBlocked("invalid_coordinate_action_schema")
        x, y = proposal["x"], proposal["y"]
        if type(x) is not int or type(y) is not int or not (0 <= x <= 63 and 0 <= y <= 63):
            raise BenchmarkBlocked("invalid_coordinates")
        return action, {"x": x, "y": y}
    if set(proposal) != {"action"}:
        raise BenchmarkBlocked("unexpected_action_arguments")
    return action, {}


class LocalReferenceGenesis:
    identity = "genesis-v0.1-symbolic-reference"
    provenance = "local_reference_not_neural_not_aws"

    def __init__(self):
        from genesis import Genesis
        self._temp = tempfile.TemporaryDirectory(prefix="genesis-arc-")
        base = Path(self._temp.name)
        # Prevent inherited CI settings from activating Ollama or Bedrock.
        with patch.dict(os.environ, {"GENESIS_GENERATOR": "none", "GENESIS_BEDROCK_ENABLE": "0"}):
            self.model = Genesis(
                state_path=base / "state.sqlite3",
                workspace=base / "workspace",
                enable_ollama=False,
            )
        if self.model.cognition.backend.available():
            self.close()
            raise BenchmarkBlocked("unexpected_generator_in_reference_mode")

    def choose(self, prompt):
        return self.model.respond(prompt)

    def close(self):
        if hasattr(self, "model"):
            self.model.close()
        self._temp.cleanup()


class DenyRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise BenchmarkBlocked("private_endpoint_redirect_refused")


class KyroHttpsGenesis:
    identity = "kyro-private-genesis"
    provenance = "remote_model_unverified_requires_provenance_review"

    def __init__(self, url, bearer):
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise BenchmarkBlocked("private_genesis_endpoint_must_be_https")
        if not parsed.path or not bearer:
            raise BenchmarkBlocked("private_endpoint_or_bearer_missing")
        self.url = url
        self.bearer = bearer

    def choose(self, prompt):
        body = json.dumps({"message": prompt, "trace": False}).encode("utf-8")
        request = urllib.request.Request(
            self.url, data=body, method="POST",
            headers={
                "Authorization": "Bearer " + self.bearer,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.build_opener(DenyRedirect()).open(request, timeout=25) as response:
                content = response.read(32769)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise BenchmarkBlocked("private_genesis_endpoint_unavailable") from exc
        if len(content) > 32768:
            raise BenchmarkBlocked("genesis_response_too_large")
        try:
            answer = json.loads(content)["answer"]
        except (ValueError, TypeError, KeyError) as exc:
            raise BenchmarkBlocked("unexpected_genesis_chat_response") from exc
        if not isinstance(answer, str):
            raise BenchmarkBlocked("unexpected_genesis_answer_type")
        return answer

    def close(self):
        pass


def play_game(arcade, agent, game, max_actions):
    env = arcade.make(game, save_recording=False)
    if env is None:
        raise BenchmarkBlocked("arc_game_unavailable")
    observation = env.reset()
    if observation is None:
        raise BenchmarkBlocked("arc_reset_failed")
    actions_taken = []
    status = "action_cap"
    for _ in range(max_actions):
        state = getattr(getattr(observation, "state", None), "name", None)
        if state in ("WIN", "GAME_OVER"):
            status = state.lower()
            break
        allowed = list(env.action_space)
        action, data = parse_decision(
            agent.choose(make_prompt(game, observation, allowed, actions_taken)), allowed
        )
        observation = env.step(action, data=data)
        actions_taken.append({"action": action.name, **data})
        if observation is None:
            raise BenchmarkBlocked("arc_step_failed")
    else:
        state = getattr(getattr(observation, "state", None), "name", None)
        if state in ("WIN", "GAME_OVER"):
            status = state.lower()
    return {"status": status, "actions": actions_taken}


def play_live(agent, game, max_actions):
    if not os.environ.get("ARC_API_KEY"):
        raise BenchmarkBlocked("arc_api_key_missing")
    if importlib.util.find_spec("arc_agi") is None:
        raise BenchmarkBlocked("official_arc_agi_toolkit_not_installed")
    from arc_agi import Arcade, OperationMode
    arcade = Arcade(operation_mode=OperationMode.ONLINE)
    try:
        outcome = play_game(arcade, agent, game, max_actions)
    finally:
        try:
            scorecard = arcade.close_scorecard()
        except Exception:
            scorecard = None
    outcome["official_score"] = getattr(scorecard, "score", None)
    outcome["official_scorecard_available"] = scorecard is not None
    return outcome


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", default="ls20")
    parser.add_argument("--max-actions", type=int, default=8)
    parser.add_argument("--agent", choices=("local-reference", "kyro-https"), default="local-reference")
    parser.add_argument("--live", action="store_true", help="Explicit opt-in to the ARC service")
    parser.add_argument("--output", default="arc_agi_3_result.json")
    args = parser.parse_args(argv)
    record = {
        "benchmark": "ARC-AGI-3",
        "game": args.game,
        "max_actions": args.max_actions,
        "agent": args.agent,
        "result": "NOT_RUN",
        "official_score": None,
        "official_scorecard_available": False,
    }
    start = time.monotonic()
    agent = None
    try:
        if not re.fullmatch(r"[a-zA-Z0-9]{4}", args.game):
            raise BenchmarkBlocked("invalid_game_id")
        if not 1 <= args.max_actions <= 100:
            raise BenchmarkBlocked("action_budget_out_of_range")
        if not args.live:
            raise BenchmarkBlocked("live_run_not_authorized")
        if args.agent == "kyro-https":
            agent = KyroHttpsGenesis(os.getenv("KYRO_ARC_URL", ""), os.getenv("KYRO_ARC_TOKEN", ""))
        else:
            agent = LocalReferenceGenesis()
        record["model_identity"] = agent.identity
        record["provenance"] = agent.provenance
        outcome = play_live(agent, args.game, args.max_actions)
        record.update(outcome)
        record["result"] = "COMPLETED"
    except BenchmarkBlocked as exc:
        record["result"] = "BLOCKED"
        record["blocker"] = str(exc)
    except Exception as exc:
        record["result"] = "ERROR"
        record["error_type"] = type(exc).__name__
    finally:
        if agent:
            agent.close()
        record["wall_seconds"] = round(time.monotonic() - start, 3)
        path = Path(args.output)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(record, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(record, sort_keys=True))
    return 0 if record["result"] == "COMPLETED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
