"""Tests for pi-council's council.py using a fake `pi` executable.

Run:  python3 -m unittest discover -s tests   (from the pi-council skill dir)
"""
import io
import json
import os
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import council  # noqa: E402

FAKE_PI_PY = r"""#!/usr/bin/env python3
import json, os, sys, time

argv = sys.argv[1:]
log = os.environ.get("PI_FAKE_ARGV_LOG")
if log:
    with open(log, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(argv) + "\n")
model = ""
for i, a in enumerate(argv):
    if a == "--model" and i + 1 < len(argv):
        model = argv[i + 1]
if "badmodel" in model:
    print('Error: Model "%s" not found.' % model, file=sys.stderr)
    sys.exit(1)
print("noise line that is not json")
print(json.dumps({"type": "session", "version": 3, "id": "fake-session-" + model,
                  "timestamp": "t", "cwd": os.getcwd()}), flush=True)
if "sleepy" in model:
    time.sleep(30)  # simulates a lane that hangs; killed by the lane timeout
    sys.exit(0)
prompt = sys.stdin.read()
events = [
    {"type": "agent_start"},
    {"type": "message_end", "message": {
        "role": "assistant",
        "content": [{"type": "tool_call", "name": "read"}],
        "usage": {"input": 4, "output": 1, "cost": {"total": 0.0004}},
        "stopReason": "toolUse", "timestamp": 0}},
    {"type": "message_end", "message": {
        "role": "assistant",
        "content": [{"type": "text",
                     "text": "reply-from-" + model + " plen=" + str(len(prompt))}],
        "usage": {"input": 10, "output": 5, "cacheRead": 0, "totalTokens": 15,
                  "cost": {"total": 0.001}},
        "stopReason": "stop", "timestamp": 0}},
    {"type": "turn_end"},
    {"type": "agent_end"},
]
for ev in events:
    print(json.dumps(ev))
"""


def make_fake_pi(directory: Path) -> Path:
    """Create an executable fake `pi`; returns the path to point PI_COUNCIL_PI_BIN at."""
    py_script = directory / "fake_pi.py"
    py_script.write_text(FAKE_PI_PY, encoding="utf-8")
    if os.name == "nt":
        cmd = directory / "pi.cmd"
        cmd.write_text('@echo off\npython "%~dp0fake_pi.py" %*\n', encoding="utf-8")
        return cmd
    py_script.chmod(py_script.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return py_script


class CouncilTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.state = root / "state"
        self.workspace = root / "ws"
        self.workspace.mkdir()
        self.argv_log = root / "argv.log"
        fake_pi = make_fake_pi(root)
        env = {
            "PI_COUNCIL_STATE_HOME": str(self.state),
            "PI_COUNCIL_PI_BIN": str(fake_pi),
            "PI_FAKE_ARGV_LOG": str(self.argv_log),
        }
        patcher = mock.patch.dict(os.environ, env)
        patcher.start()
        self.addCleanup(patcher.stop)

    def run_council(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = council.main(argv)
        return code, out.getvalue(), err.getvalue()

    def last_argv(self):
        lines = self.argv_log.read_text(encoding="utf-8").strip().splitlines()
        return json.loads(lines[-1])

    def all_argvs(self):
        return [json.loads(l) for l in
                self.argv_log.read_text(encoding="utf-8").strip().splitlines()]

    @staticmethod
    def get_output_path(stdout: str) -> str:
        for line in stdout.splitlines():
            if line.startswith("output_path="):
                return line.split("=", 1)[1]
        raise AssertionError(f"no output_path in stdout: {stdout}")

    def read_result(self, stdout: str) -> str:
        return Path(self.get_output_path(stdout)).read_text(encoding="utf-8")

    # ------------------------------------------------------------ test cases

    def test_success_parallel(self):
        code, out, _ = self.run_council(
            ["review this", "--models", "a/m1,b/m2,c/m3", "-w", str(self.workspace)])
        self.assertEqual(code, council.EXIT_OK)
        self.assertIn("status=completed", out)
        result = self.read_result(out)
        for model in ("a/m1", "b/m2", "c/m3"):
            self.assertIn(f"reply-from-{model}", result)
        self.assertIn("| a/m1 | ok |", result)
        self.assertNotIn("failed=", out)
        # Prompt reached the lane via stdin (fake pi echoes the prompt length).
        self.assertIn("plen=", result)
        # Usage is accumulated across tool-call and text messages (0.0004+0.001).
        self.assertIn("$0.0014", result)

    def test_partial_failure(self):
        code, out, _ = self.run_council(
            ["review this", "--models", "a/m1,badmodel/x,c/m3", "-w", str(self.workspace)])
        self.assertEqual(code, council.EXIT_OK)
        self.assertIn("status=partial", out)
        self.assertIn("failed=badmodel/x", out)
        result = self.read_result(out)
        self.assertIn("reply-from-a/m1", result)
        self.assertIn("reply-from-c/m3", result)
        self.assertIn("failed", result)  # status table records the failure

    def test_all_lanes_failed(self):
        code, out, _ = self.run_council(
            ["review this", "--models", "badmodel/x", "-w", str(self.workspace)])
        self.assertEqual(code, council.EXIT_FAILED)
        self.assertIn("status=failed", out)

    def test_cold_start_and_config_lifecycle(self):
        code, out, _ = self.run_council(["task one", "-w", str(self.workspace)])
        self.assertEqual(code, council.EXIT_CONFIG_REQUIRED)
        self.assertIn("status=config_required", out)

        code, _, _ = self.run_council(
            ["task one", "--models", "a/m1,b/m2", "--save", "-w", str(self.workspace)])
        self.assertEqual(code, council.EXIT_OK)
        config = json.loads((self.state / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(config["schema"], council.CONFIG_SCHEMA)
        self.assertEqual(config["models"], ["a/m1", "b/m2"])

        # Subsequent run silently uses the saved lineup.
        code, out, _ = self.run_council(["task two", "-w", str(self.workspace)])
        self.assertEqual(code, council.EXIT_OK)
        self.assertIn("models=a/m1,b/m2", out)

        # One-off --models override must not touch the saved config.
        code, out, _ = self.run_council(
            ["task three", "--models", "c/m9", "-w", str(self.workspace)])
        self.assertEqual(code, council.EXIT_OK)
        self.assertIn("models=c/m9", out)
        config = json.loads((self.state / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(config["models"], ["a/m1", "b/m2"])

    def test_failing_lineup_is_not_saved(self):
        # A typo'd lineup must not become the persisted default, even with --save.
        code, _, err = self.run_council(
            ["task", "--models", "badmodel/x", "--save", "-w", str(self.workspace)])
        self.assertEqual(code, council.EXIT_FAILED)
        self.assertFalse((self.state / "config.json").exists())
        self.assertIn("lineup not saved", err)

    def test_corrupt_config(self):
        self.state.mkdir(parents=True)
        (self.state / "config.json").write_text("[]", encoding="utf-8")
        with self.assertRaises(SystemExit):
            self.run_council(["task", "-w", str(self.workspace)])

    def test_command_assembly_is_read_only(self):
        code, _, _ = self.run_council(
            ["check args", "--models", "a/m1", "-w", str(self.workspace)])
        self.assertEqual(code, council.EXIT_OK)
        argv = self.last_argv()
        self.assertIn("-p", argv)
        self.assertIn("--mode", argv)
        self.assertIn("--no-session", argv)
        # --no-extensions must NOT be passed: it would break custom providers
        # registered via user-level extensions (e.g. litellm gateways), while the
        # read-only guarantee already comes from the --tools allowlist.
        self.assertNotIn("--no-extensions", argv)
        self.assertIn("--no-approve", argv)
        tools = argv[argv.index("--tools") + 1].split(",")
        self.assertEqual(set(tools), {"read", "grep", "find", "ls"})
        self.assertFalse({"write", "edit", "bash", "powershell"} & set(tools))
        # The prompt travels via stdin and never appears in argv.
        self.assertNotIn("check args", json.dumps(argv))

    def test_timeout_kills_lane_and_salvages_events(self):
        code, out, _ = self.run_council(
            ["slow task", "--models", "a/sleepy,b/m2", "--timeout", "2",
             "-w", str(self.workspace)])
        self.assertEqual(code, council.EXIT_OK)
        self.assertIn("status=partial", out)
        self.assertIn("failed=a/sleepy", out)
        run_dir = Path([l.split("=", 1)[1] for l in out.splitlines()
                        if l.startswith("run_dir=")][0])
        events = (run_dir / "a-sleepy.events.jsonl").read_text(encoding="utf-8")
        self.assertIn("fake-session-a/sleepy", events)  # partial output salvaged

    def test_synthesis_runs_without_tools(self):
        code, out, _ = self.run_council(
            ["task", "--models", "a/m1", "--synthesize", "s/chair",
             "-w", str(self.workspace)])
        self.assertEqual(code, council.EXIT_OK)
        result = self.read_result(out)
        self.assertIn("## Synthesis — s/chair", result)
        self.assertIn("reply-from-s/chair", result)
        chair_argv = self.all_argvs()[-1]
        self.assertIn("--no-tools", chair_argv)
        self.assertNotIn("--tools", chair_argv)

    def test_synthesis_skipped_when_all_lanes_fail(self):
        code, out, _ = self.run_council(
            ["task", "--models", "badmodel/x", "--synthesize", "s/chair",
             "-w", str(self.workspace)])
        self.assertEqual(code, council.EXIT_FAILED)
        result = self.read_result(out)
        self.assertIn("synthesis skipped: no successful lanes", result)
        # The chair must not be launched at all.
        self.assertEqual(len(self.all_argvs()), 1)

    def test_parse_events_robustness(self):
        stream = "\n".join([
            "garbage not json",
            "{broken json",
            json.dumps({"type": "session", "id": "s-1"}),
            json.dumps({"type": "message_end", "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "first"}],
                "usage": {"input": 1, "output": 1}}}),
            json.dumps({"type": "message_end", "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": "final answer"}],
                "usage": {"input": 5, "output": 2, "cost": {"total": 0.5}}}}),
            # Tool-call-only assistant message must not clobber the reply,
            # but its usage still counts toward the totals.
            json.dumps({"type": "message_end", "message": {
                "role": "assistant",
                "content": [{"type": "tool_call", "name": "read"}],
                "usage": {"input": 6, "output": 3, "cost": {"total": 0.1}}}}),
            json.dumps({"type": "agent_end"}),
        ])
        reply, session_id, usage = council.parse_events(stream)
        self.assertEqual(reply, "final answer")  # last text-bearing assistant message wins
        self.assertEqual(session_id, "s-1")
        self.assertEqual(usage["input"], 12)     # accumulated across all messages
        self.assertEqual(usage["output"], 6)
        self.assertAlmostEqual(usage["cost"]["total"], 0.6)


if __name__ == "__main__":
    unittest.main()
