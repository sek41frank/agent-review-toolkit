import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import review


CONFIG = {
    "scanner": {"model": "deepseek/deepseek-flash#low"},
    "reviewer": {"model": "opencode/claude-sonnet-5#medium"},
}

STUB = r'''#!/usr/bin/env python3
import json, os, pathlib, sys, time
args = sys.argv[1:]
control = json.loads(pathlib.Path(__file__).with_name("control.json").read_text(encoding="utf-8"))
if control.get("argv_capture"):
    with open(control["argv_capture"], "a", encoding="utf-8") as f:
        f.write(json.dumps(args) + "\n")
if control.get("config_capture"):
    with open(control["config_capture"], "a", encoding="utf-8") as f:
        f.write(json.dumps({"args": args, "config": os.environ.get("OPENCODE_CONFIG_CONTENT"), "autoupdate": os.environ.get("OPENCODE_DISABLE_AUTOUPDATE"), "env_seen": {key: os.environ.get(key) for key in control.get("env_audit", [])}}) + "\n")
mode = control.get("mode", "success")
if args == ["--version"]:
    print(control.get("version", "opencode v2.0.19"))
    sys.exit(control.get("version_code", 0))
if args == ["run", "--help"]:
    print(control.get("run_help", "run --standalone --agent --model --format --file"))
    sys.exit(control.get("help_code", 0))
if args == ["session", "export", "--help"]:
    print(control.get("export_help", "session export --standalone"))
    sys.exit(control.get("help_code", 0))
if args[0] == "run":
    agent = args[args.index("--agent") + 1]
    request = args[args.index("--model") + 1]
    packet = pathlib.Path(args[args.index("--file") + 1])
    assert packet.is_absolute() and packet.is_file()
    if agent == "reviewer" and control.get("reviewer_capture"):
        pathlib.Path(control["reviewer_capture"]).write_text(packet.read_text(encoding="utf-8"), encoding="utf-8")
    sid = "session-" + agent
    answer = "x" * (32 * 1024 + 1) if mode == "long_scanner" and agent == "scanner" else "REVIEW PACKET from " + agent
    events = [
        {"type": "step_start", "sessionID": sid},
        {"type": "text", "part": {"text": "" if mode == "empty" else answer}},
    ]
    print("\n".join(json.dumps(item) for item in events), flush=True)
    if mode == "timeout":
        time.sleep(30)
    if mode == "nonzero":
        sys.exit(7)
else:
    sid = args[-1]
    agent = sid.removeprefix("session-")
    request = control.get("requests", {}).get(agent, "provider/model#variant")
    model_path, separator, variant = request.partition("#")
    provider, model_id = model_path.split("/", 1)
    actual = {"id": model_id, "providerID": provider}
    if separator:
        actual["variant"] = variant
    else:
        actual["variant"] = "stub-default"
    if mode == "mismatch" and agent == "scanner":
        actual["id"] = "wrong-model"
    if mode == "bad_id" and agent == "scanner":
        sid = "wrong-session"
    answer = "x" * (32 * 1024 + 1) if mode == "long_scanner" and agent == "scanner" else "REVIEW PACKET from " + agent
    if mode == "empty_export" and agent == "scanner":
        answer = ""
    if mode == "response_mismatch" and agent == "scanner":
        answer = "different response"
    assistant = {"type": "assistant", "agent": agent, "model": actual, "finish": "stop", "content": [{"type": "text", "text": answer}]}
    if mode == "tool" and agent == "scanner":
        assistant["content"] = [{"type": "tool", "name": "read_file"}]
    print(json.dumps({"info": {"id": sid, "agent": agent, "model": actual, "cost": 0.01}, "messages": [assistant]}))
'''


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.packet = self.root / "packet.md"
        self.packet.write_text("Original material.\n", encoding="utf-8")
        self.cli_dir = self.root / "tools"
        self.cli_dir.mkdir()
        self.cli = self.cli_dir / "opencode"
        self.cli.write_text(STUB, encoding="utf-8")
        self.cli.chmod(0o700)
        self.argv_log = self.root / "argv.jsonl"
        self.config_log = self.root / "config.jsonl"
        self.control = self.cli_dir / "control.json"

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, output="out", mode="success", timeout=2, packet=None, config=None, cli=None, extra_control=None, extra_env=None):
        config = config or CONFIG
        control = {
            "mode": mode,
            "requests": {name: value["model"] for name, value in config.items()},
            "argv_capture": str(self.argv_log),
            "config_capture": str(self.config_log),
            "reviewer_capture": str(self.root / "reviewer-input.md"),
            "env_audit": ["HOME", "PATH", "OPENCODE_CONFIG_CONTENT", "OPENCODE_DISABLE_AUTOUPDATE", "SYNTHETIC_SECRET", "SYNTHETIC_API_KEY", "SYNTHETIC_TOKEN", "WORKFLOW_TEST_ROOT"],
        }
        control.update(extra_control or {})
        self.control.write_text(json.dumps(control), encoding="utf-8")
        selected_cli = cli if cli is not None else str(self.cli)
        with patch.dict(os.environ, extra_env or {}):
            return review.run_review(str(packet or self.packet), str(self.root / output), review.parse_config(config), timeout, selected_cli)

    def read_result(self, output="out"):
        return json.loads((self.root / output / "result.json").read_text(encoding="utf-8"))

    def model_calls(self):
        calls = [json.loads(line) for line in self.argv_log.read_text(encoding="utf-8").splitlines()]
        return [
            args for args in calls
            if args and ((args[0] == "run" and args != ["run", "--help"])
                         or (args[0] == "session" and args != ["session", "export", "--help"]))
        ]

    def test_success_records_verified_models_cost_hash_and_review_index(self):
        self.assertEqual(self.invoke(), 0)
        result = self.read_result()
        self.assertEqual(result["status"], "REVIEW_COMPLETED")
        self.assertEqual(result["stages"][0]["session_id"], "session-scanner")
        self.assertEqual(result["stages"][1]["actual_model"]["agent"], "reviewer")
        self.assertEqual(result["stages"][0]["api_cost"], {"info.cost": 0.01})
        self.assertEqual(len(result["packet_sha256"]), 64)
        self.assertEqual(stat.S_IMODE((self.root / "out").stat().st_mode), 0o700)
        for name in ("scanner.text.md", "reviewer.text.md", "scanner.export.json", "reviewer.export.json", "REVIEW.md"):
            self.assertTrue((self.root / "out" / name).is_file())
        self.assertIn("does not mean", (self.root / "out" / "REVIEW.md").read_text(encoding="utf-8"))
        invocations = [json.loads(line) for line in self.config_log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(len(invocations), 7)
        for invocation in invocations:
            config = json.loads(invocation["config"])
            self.assertEqual(set(config["agents"]), {"scanner", "reviewer"})
            for agent in config["agents"].values():
                self.assertEqual(agent["steps"], 3)
                self.assertEqual(agent["permissions"], [{"action": "*", "resource": "*", "effect": "deny"}])
            self.assertEqual(invocation["autoupdate"], "1")
        run_args = [args for args in self.model_calls() if args[0] == "run"]
        self.assertEqual(len(run_args), 2)
        for args in run_args:
            self.assertIn("--standalone", args)
            packet_path = Path(args[args.index("--file") + 1])
            self.assertTrue(packet_path.is_absolute())
            self.assertTrue(packet_path.is_file())
        self.assertIn("Original material.", (self.root / "reviewer-input.md").read_text(encoding="utf-8"))
        self.assertIn("REVIEW PACKET from scanner", (self.root / "reviewer-input.md").read_text(encoding="utf-8"))

    def test_packet_content_and_injected_instruction_never_enter_argv(self):
        self.packet.write_text("SENSITIVE_MATERIAL_X\nINJECTED_DIRECTIVE_X\n", encoding="utf-8")
        self.assertEqual(self.invoke(), 0)
        args = "\n".join(json.dumps(item) for item in self.model_calls())
        self.assertNotIn("SENSITIVE_MATERIAL_X", args)
        self.assertNotIn("INJECTED_DIRECTIVE_X", args)

    def test_child_environment_allowlist_excludes_synthetic_secrets(self):
        synthetic = {"SYNTHETIC_SECRET": "fake-secret", "SYNTHETIC_API_KEY": "fake-api-key", "SYNTHETIC_TOKEN": "fake-token", "WORKFLOW_TEST_ROOT": "fake-path"}
        self.assertEqual(self.invoke(extra_env=synthetic), 0)
        invocations = [json.loads(line) for line in self.config_log.read_text(encoding="utf-8").splitlines()]
        for invocation in invocations:
            seen = invocation["env_seen"]
            self.assertTrue(seen["PATH"])
            self.assertTrue(seen["HOME"])
            self.assertTrue(seen["OPENCODE_CONFIG_CONTENT"])
            self.assertEqual(seen["OPENCODE_DISABLE_AUTOUPDATE"], "1")
            for key in synthetic:
                self.assertIsNone(seen[key])

    def test_oversized_scanner_text_never_starts_reviewer(self):
        self.assertEqual(self.invoke(mode="long_scanner"), 1)
        result = self.read_result()
        self.assertEqual(result["failure_code"], "scanner_text_too_large")
        run_calls = [args for args in self.model_calls() if args[0] == "run"]
        self.assertEqual(len(run_calls), 1)
        self.assertEqual(run_calls[0][run_calls[0].index("--agent") + 1], "scanner")

    def test_actual_model_mismatch_fails(self):
        self.assertEqual(self.invoke(mode="mismatch"), 1)
        result = self.read_result()
        self.assertEqual(result["status"], "FAILED")
        self.assertEqual(result["stages"][0]["failure_code"], "export_identity_mismatch")

    def test_export_session_must_match_run_session(self):
        self.assertEqual(self.invoke(mode="bad_id"), 1)
        self.assertEqual(self.read_result()["stages"][0]["failure_code"], "export_session_mismatch")

    def test_export_assistant_text_must_be_nonempty_and_match_run(self):
        self.assertEqual(self.invoke(output="empty-export", mode="empty_export"), 1)
        self.assertEqual(self.read_result("empty-export")["stages"][0]["failure_code"], "assistant_empty")
        self.assertEqual(self.invoke(output="different", mode="response_mismatch"), 1)
        self.assertEqual(self.read_result("different")["stages"][0]["failure_code"], "run_export_mismatch")

    def test_empty_text_fails(self):
        self.assertEqual(self.invoke(mode="empty"), 1)
        self.assertEqual(self.read_result()["failure_code"], "run_empty_text")

    def test_timeout_and_nonzero_exit_fail_without_retry(self):
        self.assertEqual(self.invoke(output="timed", mode="timeout", timeout=1), 1)
        self.assertEqual(self.read_result("timed")["stages"][0]["failure_code"], "timeout")
        self.argv_log.unlink(missing_ok=True)
        self.assertEqual(self.invoke(output="nonzero", mode="nonzero"), 1)
        self.assertEqual(self.read_result("nonzero")["stages"][0]["failure_code"], "nonzero_exit")
        calls = [args for args in self.model_calls() if args[0] == "run"]
        self.assertEqual(len(calls), 1)

    def test_tool_call_in_export_is_rejected(self):
        self.assertEqual(self.invoke(mode="tool"), 1)
        self.assertEqual(self.read_result()["stages"][0]["failure_code"], "tool_call_rejected")

    def test_report_failure_cannot_return_success(self):
        with patch.object(review, "_reports", side_effect=OSError("write failed")):
            self.assertEqual(self.invoke(), 1)

    def test_failed_review_index_marks_unproduced_files_without_dead_links(self):
        self.assertEqual(self.invoke(mode="nonzero"), 1)
        result = self.read_result()
        self.assertEqual(result["status"], "FAILED")
        report = (self.root / "out" / "REVIEW.md").read_text(encoding="utf-8")
        self.assertIn("Status: `FAILED`", report)
        self.assertIn("Response: not produced", report)
        self.assertIn("Export: not produced", report)
        links = re.findall(r"\[[^\]]+\]\(([^)]+)\)", report)
        self.assertTrue(links)
        for target in links:
            self.assertTrue((self.root / "out" / target).is_file(), target)
        self.assertNotIn("[scanner.text.md](scanner.text.md)", report)
        self.assertNotIn("[scanner.export.json](scanner.export.json)", report)

    def test_existing_output_and_symlinks_are_rejected(self):
        self.assertEqual(self.invoke(), 0)
        before = (self.root / "out" / "result.json").read_bytes()
        with self.assertRaises(review.ReviewError) as caught:
            review.run_review(str(self.packet), str(self.root / "out"), review.parse_config(CONFIG), 2, str(self.cli))
        self.assertEqual(caught.exception.code, "output_exists")
        self.assertEqual((self.root / "out" / "result.json").read_bytes(), before)
        packet_link = self.root / "packet-link.md"
        packet_link.symlink_to(self.packet)
        self.assertEqual(self.invoke(output="link-out", packet=packet_link), 1)
        self.assertEqual(self.read_result("link-out")["failure_code"], "packet_symlink")
        real_parent = self.root / "real-parent"
        real_parent.mkdir()
        parent_link = self.root / "parent-link"
        parent_link.symlink_to(real_parent, target_is_directory=True)
        with self.assertRaises(review.ReviewError) as caught:
            review.run_review(str(self.packet), str(parent_link / "new-out"), review.parse_config(CONFIG), 2, str(self.cli))
        self.assertEqual(caught.exception.code, "output_symlink_parent")

    def test_model_variant_is_optional_and_actual_default_variant_is_recorded(self):
        config = {"scanner": {"model": "provider/scan-model"}, "reviewer": {"model": "provider/review-model"}}
        self.assertEqual(self.invoke(config=config), 0)
        result = self.read_result()
        for stage in result["stages"]:
            self.assertEqual(stage["actual_model"]["model"]["variant"], "stub-default")
            self.assertNotIn("variant", review.parse_config(config)[stage["name"]]["actual"])

    def test_relative_cli_path_is_resolved_before_child_cwd_changes(self):
        previous = Path.cwd()
        try:
            os.chdir(self.root)
            self.assertEqual(self.invoke(output="relative-out", cli="tools/opencode"), 0)
        finally:
            os.chdir(previous)

    def test_v1_cli_is_rejected_before_model_call_and_failure_is_saved(self):
        self.assertEqual(self.invoke(extra_control={"version": "opencode v1.9.9"}), 1)
        result = self.read_result()
        self.assertEqual(result["failure_code"], "cli_v2_required")
        self.assertEqual(result["cli"]["version"], "opencode v1.9.9")
        self.assertEqual(result["cli"]["compatible"], False)
        self.assertEqual(self.model_calls(), [])

    def test_missing_help_capability_is_rejected_and_recorded(self):
        self.assertEqual(self.invoke(extra_control={"run_help": "run --agent --model --format --file"}), 1)
        result = self.read_result()
        self.assertEqual(result["failure_code"], "cli_unsupported")
        self.assertIn("run --standalone", result["failure_detail"])
        self.assertEqual(self.model_calls(), [])

    def test_config_requires_two_models_and_valid_model_syntax(self):
        for bad in (
            {"scanner": {"model": "provider/model"}},
            {"scanner": {"model": "provider/model#"}, "reviewer": {"model": "provider/review"}},
            {"scanner": {"model": "provider/model#one#two"}, "reviewer": {"model": "provider/review"}},
            {"scanner": {"model": "provider/model"}, "reviewer": {"model": "provider/review"}, "other": {}},
        ):
            with self.assertRaises(review.ReviewError):
                review.parse_config(bad)

    def test_check_cli_runs_capability_probe_only(self):
        self.control.write_text(json.dumps({"mode": "success", "argv_capture": str(self.argv_log), "config_capture": str(self.config_log)}), encoding="utf-8")
        info = review.check_cli(str(self.cli), timeout=2)
        self.assertEqual(info["major"], 2)
        self.assertTrue(info["compatible"])
        calls = [json.loads(line) for line in self.argv_log.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(calls, [["--version"], ["run", "--help"], ["session", "export", "--help"]])

    def test_fifo_packet_and_config_fail_without_blocking(self):
        fifo = self.root / "input.fifo"
        os.mkfifo(fifo)
        module_dir = str(Path(review.__file__).resolve().parent)
        checks = (
            ("packet", f"review._read_packet({str(fifo)!r})"),
            ("config", f"review.load_config({str(fifo)!r})"),
        )
        for expected, expression in checks:
            code = (
                "import sys; sys.dont_write_bytecode=True; sys.path.insert(0, "
                + repr(module_dir)
                + "); import review\ntry:\n "
                + expression
                + "\nexcept review.ReviewError as exc:\n print(exc.code)\n"
            )
            completed = subprocess.run(
                [sys.executable, "-B", "-c", code],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("not_regular", completed.stdout)

    def test_keyboard_interrupt_kills_child_process_group_and_reports_interrupted(self):
        output = self.root / "interrupt-output"
        output.mkdir(mode=0o700)
        process = Mock(pid=43127)
        process.wait.side_effect = KeyboardInterrupt()
        with patch.object(review.subprocess, "Popen", return_value=process), patch.object(review, "_kill_group") as kill:
            with self.assertRaises(review.ReviewError) as caught:
                review._run(["stub"], output, "stdout", "stderr", 1, {})
        self.assertEqual(caught.exception.code, "interrupted")
        kill.assert_called_once_with(process)

    def test_probe_timeout_kills_grandchild_and_preserves_diagnostics(self):
        ready = self.root / "grandchild-ready"
        stopped = self.root / "grandchild-stopped"
        pids_path = self.root / "probe-pids.json"
        child_code = (
            "import pathlib,signal,sys,time\n"
            "ready=pathlib.Path(sys.argv[1]); stopped=pathlib.Path(sys.argv[2])\n"
            "def stop(signum, frame):\n stopped.write_text('stopped')\n raise SystemExit(0)\n"
            "signal.signal(signal.SIGTERM, stop)\n"
            "ready.write_text('ready')\n"
            "time.sleep(30)\n"
        )
        parent_code = (
            "#!/usr/bin/env python3\n"
            "import json,os,pathlib,signal,subprocess,sys,time\n"
            "root=pathlib.Path(__file__).resolve().parent\n"
            "child=None\n"
            "def stop(signum, frame):\n"
            " global child\n"
            " if child is not None:\n"
            "  try: child.wait(timeout=2)\n"
            "  except subprocess.TimeoutExpired:\n"
            "   child.kill(); child.wait()\n"
            " raise SystemExit(128+signum)\n"
            "signal.signal(signal.SIGTERM, stop)\n"
            "child=subprocess.Popen([sys.executable,'-c',"
            + repr(child_code)
            + ",str(root/'grandchild-ready'),str(root/'grandchild-stopped')])\n"
            "deadline=time.monotonic()+2\n"
            "while not (root/'grandchild-ready').exists() and time.monotonic()<deadline: time.sleep(0.01)\n"
            "(root/'probe-pids.json').write_text(json.dumps({'parent':os.getpid(),'grandchild':child.pid}))\n"
            "print('probe stdout before timeout',flush=True)\n"
            "print('probe stderr before timeout',file=sys.stderr,flush=True)\n"
            "time.sleep(30)\n"
        )
        probe_cli = self.root / "probe-cli"
        probe_cli.write_text(parent_code, encoding="utf-8")
        probe_cli.chmod(0o700)
        try:
            self.assertEqual(
                review.run_review(
                    str(self.packet),
                    str(self.root / "probe-timeout"),
                    review.parse_config(CONFIG),
                    1,
                    str(probe_cli),
                ),
                1,
            )
            result = json.loads((self.root / "probe-timeout" / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(result["failure_code"], "cli_preflight_timeout")
            self.assertEqual(result["failure_detail"], "version")
            self.assertIn("probe stdout before timeout", (self.root / "probe-timeout" / "cli.version.stdout.txt").read_text(encoding="utf-8"))
            self.assertIn("probe stderr before timeout", (self.root / "probe-timeout" / "cli.version.stderr.txt").read_text(encoding="utf-8"))
            self.assertTrue(ready.is_file())
            self.assertTrue(stopped.is_file())
            pids = json.loads(pids_path.read_text(encoding="utf-8"))

            def running(pid):
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    return False
                stat_path = Path(f"/proc/{pid}/stat")
                if stat_path.exists():
                    return stat_path.read_text(encoding="utf-8").split()[2] != "Z"
                return True

            deadline = time.monotonic() + 2
            while time.monotonic() < deadline and (running(pids["parent"]) or running(pids["grandchild"])):
                time.sleep(0.02)
            self.assertFalse(running(pids["parent"]))
            self.assertFalse(running(pids["grandchild"]))
        finally:
            if pids_path.exists():
                pids = json.loads(pids_path.read_text(encoding="utf-8"))
                try:
                    os.killpg(pids["parent"], signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def test_probe_keyboard_interrupt_kills_process_group(self):
        process = Mock(pid=43128)
        process.wait.side_effect = KeyboardInterrupt()
        with patch.object(review.subprocess, "Popen", return_value=process) as popen, patch.object(review, "_kill_group") as kill:
            with self.assertRaises(review.ReviewError) as caught:
                review._capture_probe("stub", ["--version"], "version", 1, None)
        self.assertEqual(caught.exception.code, "interrupted")
        self.assertIn("CLI preflight: version", caught.exception.detail)
        self.assertTrue(popen.call_args.kwargs["start_new_session"])
        kill.assert_called_once_with(process)


if __name__ == "__main__":
    unittest.main()
