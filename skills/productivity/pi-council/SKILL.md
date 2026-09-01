---
name: pi-council
description: >-
  Dispatch one task to several different LLMs in parallel via the pi CLI with read-only tools, and collect their independent opinions into one Markdown report. Built for brainstorming, design or proposal discussion, plan review, and code review. Explicit user invocation only.
disable-model-invocation: true
---

# Pi Council

One task in, N independent model opinions out. Each council lane is a separate `pi` process pinned to a different model, running in parallel with a read-only tool allowlist. The calling agent reads the combined report and does the final synthesis itself (unless `--synthesize` is requested).

## Requirements

- `pi` CLI on `PATH` (`npm install -g @earendil-works/pi-coding-agent`, see https://pi.dev), with authenticated providers
- Python 3.8+ (stdlib only); the council script itself is cross-platform (macOS/Linux/Windows)

## Workflow

1. **Polish the task first — that is your job, not the script's.** Council lanes are one-shot: they cannot ask clarifying questions or see your conversation. Turn the user's raw request into a self-contained brief with background, relevant materials or paths, and the specific questions each lane should answer. `council.py` passes the task text verbatim.

2. Run the council from the workspace under discussion. Use the installed skill's absolute script path (the relative form below assumes the skill directory is your cwd):

   ```bash
   python3 <skill-dir>/scripts/council.py "<task>" -m code-review -f src/api.ts -w /path/to/repo
   ```

3. **Cold start** — exit code 3 with `status=config_required` means no model lineup is saved. Ask the user which models should sit on the council, then re-run with the lineup; it is saved automatically on first use (`--save` makes that explicit and also works when replacing an existing lineup):

   ```bash
   python3 <skill-dir>/scripts/council.py "<task>" --models deepseek/deepseek-v4-pro,openai/gpt-5 --save
   ```

   Later runs use the saved lineup silently. `--models a,b,c` without `--save` overrides for one run only. A lineup is persisted only after a run where at least one lane succeeded — a typo'd lineup never becomes the saved default.

4. **Recommending a lineup** — at cold start, and whenever the user asks what models are available, run `pi --list-models` and propose 3–4 IDs from **different vendors**; same-family models converge and defeat the council's purpose. Pass IDs exactly as listed, in `provider/model` form. Shapes that work well (illustrative, always confirm against the user's actual list):

   - quality-leaning: one reasoning-strong model per vendor, e.g. `deepseek/deepseek-v4-pro,litellm/m3/glm-5.3,litellm/m3/kimi-k3,openai-codex/gpt-5.6-sol`
   - budget-leaning: flash/mini tiers, e.g. `deepseek/deepseek-v4-flash,litellm/m3/glm-5.3-flash`

5. Read `result.md` (path on stdout as `output_path=`). Report every lane's opinion to the user, explicitly separating consensus from genuine disagreement, and name any failed lanes from the status table. Do not silently drop a disagreement.

## Command surface

```text
council.py <task> [-t <task>]            # stdin works when no task arg is given
  -m discuss|brainstorm|review|code-review   # scenario preamble, default: discuss
  --models a,b,c [--save]                # override lineup / persist lineup
  -f, --file <path> ...                  # up to 4 focus files, embedded into the prompt;
                                         # relative paths resolve against --workspace
  -w, --workspace <path>                 # working directory for every lane
  --synthesize <model>                   # optional chairman pass over all opinions
  --thinking <level>                     # off|minimal|low|medium|high|xhigh|max,
                                         # default: high (applies to every lane)
  --timeout <seconds>                    # per-lane timeout, default 600; raise it for
                                         # slow thinking-heavy models (e.g. 1500)
  --events / --no-events                 # keep raw per-lane NDJSON streams (default: off;
                                         # failed lanes always keep theirs)
  -o, --output <path>                    # report path, default <run_dir>/result.md
```

## What each lane actually runs

```bash
pi -p --mode json --tools read,grep,find,ls --no-session --no-approve \
   --model <provider/model> --thinking high [@focus-file ...]   # prompt fed via stdin
```

The prompt is a scenario preamble plus the task, delivered on stdin (never argv). The script parses pi's NDJSON event stream and keeps the final text-bearing assistant message; token usage and cost are accumulated across all of the lane's turns.

## Read-only guarantees

- `--tools read,grep,find,ls` is a tool-surface allowlist: `write`, `edit`, `bash`, `powershell`, and any extension-registered tools are unavailable to the lane. It restricts what a lane can *do*, not what it can *read* — a lane can read any file the user account can read.
- `--no-session` keeps runs ephemeral; `--no-approve` ignores project-local pi configuration.
- The optional chairman lane (`--synthesize`) runs with `--no-tools`, since it only reads the embedded opinions.
- The preamble tells each model it is a read-only council member. Verified end-to-end: a lane asked to create a file refuses and nothing is written.
- `--no-extensions` is deliberately **not** passed: user-level pi extensions may register custom providers (e.g. LiteLLM gateways), and disabling them makes those models vanish. The tools allowlist already blocks any tools such extensions add.
- **Data egress**: the task, focus files, and anything lanes choose to read are sent to every provider in the lineup. Do not point the council at secrets or confidential material without the user's explicit consent.

## Output contract

stdout ends with machine-readable lines: `status=completed|partial|failed|config_required`, `output_path=`, `run_dir=`, `models=`, optional `failed=`, `elapsed=`. `partial` means at least one lane failed while others succeeded. Exit codes: 0 = at least one lane succeeded (including partial), 1 = all lanes failed or bad input, 3 = lineup not configured (2 is reserved for argparse usage errors).

The run directory holds `<model-slug>.md` per lane plus the combined `result.md` (status table + full opinions + optional synthesis). Raw `<model-slug>.events.jsonl` streams are kept only for failed lanes, or for all lanes with `--events`. If every lane fails, synthesis is skipped and `result.md` says so explicitly.

Run data accumulates: after each run the script reports on stderr how many runs and how many MB are stored under `<state_home>/runs/` (e.g. `[council] state: 12 runs, 45.0 MB accumulated at ... (delete it anytime)`). Surface this to the user when it grows large; purging old run directories is always safe.

## Environment variables

- `PI_COUNCIL_STATE_HOME` — overrides the state directory (config + run artifacts). Default: `$XDG_STATE_HOME/pi-council` or `~/.local/state/pi-council` on POSIX, `%LOCALAPPDATA%\pi-council` on Windows. Set this to a throwaway directory to simulate a clean first run or isolate test runs.
- `PI_COUNCIL_PI_BIN` — overrides the pi executable resolution (default: `pi` from `PATH`).

## Failure handling

- A lane that fails (unknown model, timeout, empty reply) does not sink the run; it appears as `failed (...)` in the status table and in the `failed=` stdout line. Failed lanes always keep their `events.jsonl`, and an empty-reply error points at it for diagnosis.
- A timed-out lane is killed together with its whole process tree; its partial output is still salvaged into `events.jsonl`.
- If a lane reports `Model "..." not found`, the saved lineup is stale: ask the user for a replacement and re-run with `--models ... --save`.
- If every custom-provider lane fails at once, suspect a provider/auth outage rather than the task; check `pi auth check --provider <name>`. Note that extension-registered providers (e.g. LiteLLM gateways) can report `not_ready` there yet still work — an actual lane result beats the auth check.
- Cost scales linearly with lanes: N models = N× tokens. Three to four lanes is the practical sweet spot. Reported cost is accumulated across every turn of a lane, including tool-call turns. Thinking level (`--thinking`) is the main cost/latency lever.

## Tests

```bash
python3 -m unittest discover -s tests     # from the skill directory
```
