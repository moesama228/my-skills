#!/usr/bin/env python3
"""pi-council: dispatch one task to multiple LLMs in parallel via the pi CLI.

Each lane is an independent `pi -p --mode json` process pinned to one model,
restricted to read-only tools (read, grep, find, ls). The prompt is fed via
stdin. Opinions are collected into per-lane Markdown files plus a combined
result.md. Pure stdlib, runs on macOS / Linux / Windows.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import secrets
import shutil
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

READ_ONLY_TOOLS = "read,grep,find,ls"
CONFIG_SCHEMA = "pi-council.config.v1"
DEFAULT_TIMEOUT = 600
MAX_FOCUS_FILES = 4

EXIT_OK = 0
EXIT_FAILED = 1
# 2 is deliberately skipped: argparse uses it for CLI usage errors.
EXIT_CONFIG_REQUIRED = 3

COMMON_PREAMBLE = (
    "You are one member of an expert council of independent AI models. "
    "You run in a strictly READ-ONLY environment: never create, modify, or "
    "delete anything; investigate only with your read/grep/find/ls tools. "
    "Answer in the same language as the task. Format your final answer in Markdown."
)

MODE_PREAMBLES = {
    "discuss": (
        "The council is discussing a question or proposal. Give your reasoned "
        "position, the key trade-offs, and alternatives worth considering. "
        "Be specific and opinionated."
    ),
    "brainstorm": (
        "The council is brainstorming. Maximize diversity and novelty of ideas: "
        "offer several clearly distinct angles and avoid converging on the obvious."
    ),
    "review": (
        "The council is reviewing a proposal or plan. Identify strengths, risks, "
        "gaps, and concrete improvements, then end with a clear verdict."
    ),
    "code-review": (
        "The council is reviewing code. Investigate with your read-only tools and "
        "report bugs, security issues, performance concerns, and maintainability "
        "problems, citing file:line for each finding. Order findings by severity."
    ),
}


# ---------------------------------------------------------------- paths / config

def state_home() -> Path:
    env = os.environ.get("PI_COUNCIL_STATE_HOME")
    if env:
        return Path(env)
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA")
        return (Path(base) if base else Path.home() / "AppData" / "Local") / "pi-council"
    xdg = os.environ.get("XDG_STATE_HOME")
    return (Path(xdg) if xdg else Path.home() / ".local" / "state") / "pi-council"


def load_config(path: Path):
    """Return the saved model list, or None when no config exists."""
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("root must be an object")
        models = data.get("models")
        if not isinstance(models, list) or not all(isinstance(m, str) for m in models):
            raise ValueError("bad models field")
        models = [m for m in (m.strip() for m in models) if m]
        if not models:
            raise ValueError("empty models list")
        return models
    except (ValueError, OSError) as exc:
        raise SystemExit(
            f"[ERROR] Config file is corrupt: {path} ({exc}). "
            "Fix it or delete it and re-run with --models a,b,c --save."
        )


def save_config(path: Path, models) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"schema": CONFIG_SCHEMA, "models": models}
    tmp = path.with_name(f"{path.stem}.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


# ---------------------------------------------------------------- pi invocation

def pi_command_prefix():
    """Resolve the pi executable; wrap .cmd/.bat shims with cmd /c on Windows."""
    override = os.environ.get("PI_COUNCIL_PI_BIN")
    exe = override or shutil.which("pi")
    if not exe:
        raise SystemExit(
            "[ERROR] pi CLI not found on PATH. Install it first: "
            "npm install -g @earendil-works/pi-coding-agent (see https://pi.dev)."
        )
    if os.name == "nt" and exe.lower().endswith((".cmd", ".bat")):
        return ["cmd", "/c", exe]
    return [exe]


def build_lane_argv(model: str, files, tools=READ_ONLY_TOOLS):
    """Assemble the pi command. The prompt itself travels via stdin, never argv."""
    argv = ["-p", "--mode", "json"]
    if tools is None:
        argv.append("--no-tools")
    else:
        argv += ["--tools", tools]
    argv += [
        "--no-session",
        # NOTE: do not add --no-extensions here. The read-only guarantee comes from
        # the --tools allowlist (it also blocks extension-registered tools), while
        # user-level extensions may be required to resolve custom providers/models
        # (e.g. litellm gateways). --no-approve still blocks project-local resources.
        "--no-approve",
        "--model", model,
    ]
    argv += ["@" + f for f in files]
    return argv


def slugify(model: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", model).strip("-") or "model"


def _add_usage(total: dict, usage: dict) -> None:
    """Accumulate one message's usage into the run totals (one nesting level)."""
    for key, value in usage.items():
        if isinstance(value, (int, float)):
            total[key] = total.get(key, 0) + value
        elif isinstance(value, dict):
            sub = total.setdefault(key, {})
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, (int, float)):
                    sub[sub_key] = sub.get(sub_key, 0) + sub_value


def parse_events(text: str):
    """Extract (final_reply, session_id, usage) from pi's NDJSON event stream.

    The final reply is the text of the last text-bearing assistant `message_end`
    event. Usage is accumulated across ALL assistant messages — a lane typically
    spends most of its tokens on intermediate tool-call turns, so keeping only
    the last message's usage underreports cost several-fold.
    Tolerates non-JSON noise lines interleaved in the stream.
    """
    reply = ""
    session_id = None
    usage = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        ev_type = ev.get("type")
        if ev_type == "session" and session_id is None:
            session_id = ev.get("id")
        elif ev_type == "message_end":
            msg = ev.get("message") or {}
            if msg.get("role") != "assistant":
                continue
            if msg.get("usage"):
                _add_usage(usage, msg["usage"])
            texts = [
                c.get("text", "")
                for c in msg.get("content") or []
                if isinstance(c, dict) and c.get("type") == "text"
            ]
            texts = [t for t in texts if t]
            # Skip tool-call-only assistant messages: they carry no text and
            # must not clobber a real reply captured earlier.
            if texts:
                reply = "\n".join(texts)
    return reply, session_id, usage


def _kill_tree(proc) -> None:
    """Kill a lane process including its children (pi spawns grandchildren that
    would otherwise keep running — and burning tokens — after a timeout)."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True)
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass


def run_lane(model: str, prefix, files, prompt: str, workspace: Path,
             timeout: int, run_dir: Path, slug: str, tools=READ_ONLY_TOOLS):
    """Run one pi process for one model; never raises, returns a result dict."""
    events_path = run_dir / f"{slug}.events.jsonl"
    argv = prefix + build_lane_argv(model, files, tools=tools)
    started = time.monotonic()
    error = None
    stdout = ""
    stderr = ""
    popen_kwargs = dict(
        cwd=str(workspace),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True
    proc = None
    try:
        proc = subprocess.Popen(argv, **popen_kwargs)
        try:
            stdout, stderr = proc.communicate(input=prompt, timeout=timeout)
        except subprocess.TimeoutExpired:
            error = f"timeout after {timeout}s"
            _kill_tree(proc)
            # Collect whatever the lane produced before being killed.
            out, err = proc.communicate()
            stdout = out or ""
            stderr = err or ""
    except OSError as exc:
        error = f"failed to launch pi: {exc}"
    elapsed = time.monotonic() - started

    try:
        events_path.write_text(stdout, encoding="utf-8")
    except OSError:
        pass

    reply, session_id, usage = parse_events(stdout)
    if error is None:
        if proc.returncode != 0:
            tail = "\n".join(stderr.strip().splitlines()[-5:])
            error = f"pi exited with code {proc.returncode}" + (f": {tail}" if tail else "")
        elif not reply.strip():
            error = f"pi produced no assistant reply (see {events_path})"

    return {
        "model": model,
        "slug": slug,
        "ok": error is None,
        "error": error,
        "reply": reply,
        "session_id": session_id,
        "usage": usage,
        "elapsed": elapsed,
        "events_path": events_path,
    }


# ---------------------------------------------------------------- reporting

def fmt_tokens(usage) -> str:
    if not usage:
        return "-"
    inp = usage.get("input", 0) + usage.get("cacheRead", 0)
    out = usage.get("output", 0)
    return f"{inp}/{out}"


def fmt_cost(usage) -> str:
    cost = (usage or {}).get("cost") or {}
    total = cost.get("total")
    return f"${total:.4f}" if isinstance(total, (int, float)) else "-"


def write_lane_report(run_dir: Path, lane) -> Path:
    path = run_dir / f"{lane['slug']}.md"
    lines = [
        f"# {lane['model']}",
        "",
        f"- status: {'ok' if lane['ok'] else 'failed'}",
        f"- elapsed: {lane['elapsed']:.1f}s",
        f"- tokens (in/out): {fmt_tokens(lane['usage'])}",
        f"- cost: {fmt_cost(lane['usage'])}",
        f"- session: {lane['session_id'] or '-'}",
        "",
    ]
    if lane["ok"]:
        lines += ["## Opinion", "", lane["reply"], ""]
    else:
        lines += ["## Error", "", lane["error"] or "unknown error", ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def write_result(run_dir: Path, task: str, mode: str, lanes, synthesis,
                 synthesis_note=None) -> Path:
    path = run_dir / "result.md"
    lines = [
        f"# Pi Council — {mode}",
        "",
        "## Task",
        "",
        task,
        "",
        "## Status",
        "",
        "| Model | Status | Elapsed | Tokens (in/out) | Cost |",
        "| --- | --- | --- | --- | --- |",
    ]
    for lane in lanes:
        status = "ok" if lane["ok"] else f"failed ({lane['error']})"
        lines.append(
            f"| {lane['model']} | {status} | {lane['elapsed']:.1f}s "
            f"| {fmt_tokens(lane['usage'])} | {fmt_cost(lane['usage'])} |"
        )
    lines.append("")
    for lane in lanes:
        if not lane["ok"]:
            continue
        lines += [f"## Opinion — {lane['model']}", "", lane["reply"], ""]
    if synthesis is not None:
        lines += [f"## Synthesis — {synthesis['model']}", ""]
        if synthesis["ok"]:
            lines += [synthesis["reply"], ""]
        else:
            lines += [f"(synthesis failed: {synthesis['error']})", ""]
    elif synthesis_note:
        lines += ["## Synthesis", "", f"({synthesis_note})", ""]
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ---------------------------------------------------------------- main

def parse_models_arg(raw: str):
    models = []
    for item in raw.split(","):
        item = item.strip()
        if item and item not in models:
            models.append(item)
    return models


def build_prompt(mode: str, task: str) -> str:
    return f"{COMMON_PREAMBLE}\n\n{MODE_PREAMBLES[mode]}\n\nTask:\n{task}"


def build_synthesis_prompt(task: str, lanes) -> str:
    parts = [
        COMMON_PREAMBLE,
        "",
        "You are the chair of the council. All member opinions are below. "
        "Synthesize them: state the consensus, the genuine disagreements, and "
        "your final recommendation. Do not merely list the opinions.",
        "",
        "Task:",
        task,
        "",
    ]
    for lane in lanes:
        if lane["ok"]:
            parts += [f"=== Opinion from {lane['model']} ===", lane["reply"], ""]
    return "\n".join(parts)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="council.py",
        description="Dispatch one task to multiple LLMs in parallel via pi (read-only).",
    )
    parser.add_argument("task", nargs="?", help="task text (or use -t / stdin)")
    parser.add_argument("-t", "--task", dest="task_flag", help="task text")
    parser.add_argument("-m", "--mode", default="discuss",
                        choices=sorted(MODE_PREAMBLES), help="council scenario")
    parser.add_argument("--models", help="comma-separated provider/model list; "
                                         "overrides the saved lineup for this run")
    parser.add_argument("--save", action="store_true",
                        help="persist --models as the saved lineup")
    parser.add_argument("-f", "--file", action="append", default=[],
                        help=f"focus file embedded into the prompt (repeatable, max {MAX_FOCUS_FILES}); "
                             "relative paths resolve against --workspace")
    parser.add_argument("-w", "--workspace", default=".",
                        help="working directory for every lane (default: cwd)")
    parser.add_argument("--synthesize", metavar="MODEL",
                        help="after collecting opinions, ask MODEL to synthesize them")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"per-lane timeout in seconds (default: {DEFAULT_TIMEOUT}); "
                             "raise it for slow thinking-heavy models")
    parser.add_argument("-o", "--output", help="result.md path (default: <run_dir>/result.md)")
    args = parser.parse_args(argv)

    task = (args.task_flag or args.task or "").strip()
    if not task and not sys.stdin.isatty():
        task = sys.stdin.read().strip()
    if not task:
        print("[ERROR] Task text is empty. Pass a positional arg, -t, or stdin.", file=sys.stderr)
        return EXIT_FAILED

    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        print(f"[ERROR] Workspace does not exist: {workspace}", file=sys.stderr)
        return EXIT_FAILED

    if len(args.file) > MAX_FOCUS_FILES:
        print(f"[ERROR] At most {MAX_FOCUS_FILES} focus files are supported.", file=sys.stderr)
        return EXIT_FAILED
    files = []
    for ref in args.file:
        resolved = (workspace / ref).resolve() if not os.path.isabs(ref) else Path(ref)
        if not resolved.is_file():
            print(f"[ERROR] Focus file not found: {ref}", file=sys.stderr)
            return EXIT_FAILED
        files.append(str(resolved))

    home = state_home()
    config_path = home / "config.json"
    saved_models = load_config(config_path)
    if args.save and not args.models:
        print("[ERROR] --save requires --models.", file=sys.stderr)
        return EXIT_FAILED
    persist = False
    if args.models:
        models = parse_models_arg(args.models)
        if not models:
            print("[ERROR] --models parsed to an empty list.", file=sys.stderr)
            return EXIT_FAILED
        # Persist after the run and only when at least one lane succeeded —
        # a typo'd lineup must not become the saved default.
        persist = args.save or saved_models is None
    elif saved_models is not None:
        models = saved_models
    else:
        print("status=config_required")
        print(f"config_path={config_path}")
        print("[ERROR] No council lineup configured. Ask the user for a model list, "
              "then re-run with --models provider/a,provider/b --save. "
              "`pi --list-models` shows what is available.", file=sys.stderr)
        return EXIT_CONFIG_REQUIRED

    prefix = pi_command_prefix()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_dir = home / "runs" / f"run-{stamp}-{secrets.token_hex(4)}"
    run_dir.mkdir(parents=True, exist_ok=True)

    prompt = build_prompt(args.mode, task)
    started = time.monotonic()

    lanes = []
    slugs = {}
    print(f"[council] dispatching {len(models)} lanes: {', '.join(models)}", file=sys.stderr)
    with ThreadPoolExecutor(max_workers=len(models)) as pool:
        futures = {}
        for model in models:
            base = slugify(model)
            n = slugs.get(base, 0) + 1
            slugs[base] = n
            slug = base if n == 1 else f"{base}-{n}"
            futures[pool.submit(run_lane, model, prefix, files, prompt,
                                workspace, args.timeout, run_dir, slug)] = model
        for future in as_completed(futures):
            lane = future.result()
            lanes.append(lane)
            if lane["ok"]:
                print(f"[council] {lane['model']} done ({lane['elapsed']:.0f}s)", file=sys.stderr)
            else:
                print(f"[council] {lane['model']} FAILED: {lane['error']}", file=sys.stderr)
    lanes.sort(key=lambda l: models.index(l["model"]))

    for lane in lanes:
        write_lane_report(run_dir, lane)

    synthesis = None
    synthesis_note = None
    if args.synthesize:
        ok_lanes = [l for l in lanes if l["ok"]]
        if ok_lanes:
            print(f"[council] synthesizing with {args.synthesize}", file=sys.stderr)
            # The chair only reads embedded opinions: no tools, which also keeps
            # untrusted opinion text one step away from any tool surface.
            synthesis = run_lane(args.synthesize, prefix, [],
                                 build_synthesis_prompt(task, ok_lanes),
                                 workspace, args.timeout, run_dir,
                                 slugify(args.synthesize) + "-synthesis",
                                 tools=None)
            write_lane_report(run_dir, synthesis)
        else:
            synthesis_note = "synthesis skipped: no successful lanes"
            print(f"[council] {synthesis_note}", file=sys.stderr)

    result_path = Path(args.output).resolve() if args.output else run_dir / "result.md"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    built = write_result(run_dir, task, args.mode, lanes, synthesis, synthesis_note)
    if result_path != built:
        shutil.copyfile(built, result_path)

    elapsed = time.monotonic() - started
    failed = [l["model"] for l in lanes if not l["ok"]]
    ok = len(lanes) - len(failed) > 0

    if persist and ok:
        save_config(config_path, models)
    elif persist:
        print("[council] lineup not saved: every lane failed; fix the model list "
              "and re-run", file=sys.stderr)

    if not failed:
        status = "completed"
    elif ok:
        status = "partial"
    else:
        status = "failed"
    print(f"status={status}")
    print(f"output_path={result_path}")
    print(f"run_dir={run_dir}")
    print(f"models={','.join(models)}")
    if failed:
        print(f"failed={','.join(failed)}")
    print(f"elapsed={elapsed:.0f}s")
    return EXIT_OK if ok else EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
