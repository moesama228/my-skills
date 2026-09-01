---
name: pi-council
description: >-
  Dispatch one task to several different LLMs in parallel via the pi CLI with read-only tools, and collect their independent opinions into one Markdown report. Built for brainstorming, design or proposal discussion, plan review, and code review.
disable-model-invocation: true
---

# Pi Council

One task in, N independent model opinions out. Each council lane is a separate `pi` process pinned to a different model, running in parallel with a read-only tool allowlist. The calling agent reads the combined report and does the final synthesis itself (unless `--synthesize` is requested).

## Requirements

- `pi` CLI on `PATH` (`npm install -g @earendil-works/pi-coding-agent`, see https://pi.dev), with authenticated providers
- Python 3.8+ (stdlib only); the council script itself is cross-platform (macOS/Linux/Windows)

## Workflow

1. **Shape the task — keep the user's words, add only what's missing.** Council lanes are one-shot: they cannot ask clarifying questions and cannot see this conversation. Preserve the user's wording and priorities; add only the context a lane cannot supply itself — background, relevant materials or paths, and the specific questions to answer. Done when the text stands alone: a lane can act on it without asking anything back. `council.py` passes the task text verbatim.

2. **Settle the lineup.** Read the saved lineup from `<state_home>/config.json` (default `~/.local/state/pi-council`). If none exists, ask the user which models should sit on the council: run `pi --list-models`, then propose 3–4 IDs from **different vendors** — same-family models converge and defeat the council's purpose, and 3–4 lanes is the practical sweet spot since cost scales linearly (N models = N× tokens). Pass IDs exactly as listed, in `provider/model` form. Shapes that work well (illustrative, always confirm against the user's actual list):

   - quality-leaning: one reasoning-strong model per vendor, e.g. `deepseek/deepseek-v4-pro,litellm/m3/glm-5.3,litellm/m3/kimi-k3,openai-codex/gpt-5.6-sol`
   - budget-leaning: flash/mini tiers, e.g. `deepseek/deepseek-v4-flash,litellm/m3/glm-5.3-flash`

3. **Confirm before dispatch.** Present the shaped task text and the lineup, and adjust either on feedback. Approval means a user message answering that presentation — the invoking message is raw input, never approval, even when it already names task and models. Dispatch only after approval (sole exception: the invocation explicitly waives confirmation, e.g. "直接跑", "skip confirm"); one run spends N× tokens on the user's behalf.

4. Run the council from the workspace under discussion, using the installed skill's absolute script path. `--save` has exactly one job: replacing the saved lineup when the user asks to change the standing default — first-ever setup saves automatically, and a lineup named for one run goes in as `--models` alone. Persistence happens only after a run where at least one lane succeeded, so a typo'd lineup never becomes the saved default:

   ```bash
   python3 <skill-dir>/scripts/council.py "<task>" -m code-review -f src/api.ts -w /path/to/repo
   ```

   (If a run still exits 3 with `status=config_required`, the lineup was never settled — return to step 2.)

5. Read `result.md` (path on stdout as `output_path=`). Report every lane's opinion to the user, explicitly separating consensus from genuine disagreement, and name any failed lanes from the status table.

## Command surface

```text
council.py <task> [-t <task>]            # stdin works when no task arg is given
  -m discuss|brainstorm|review|code-review   # scenario preamble, default: discuss
  --models a,b,c [--save]                # one-off override; --save replaces the saved default
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
- The preamble tells each model it is a read-only council member.
- `--no-extensions` is deliberately **not** passed: user-level pi extensions may register custom providers (e.g. LiteLLM gateways), and disabling them makes those models vanish. The tools allowlist already blocks any tools such extensions add.
- **Data egress**: the task, focus files, and anything lanes choose to read are sent to every provider in the lineup. Get the user's consent before pointing the council at confidential material.

## Output contract

stdout ends with machine-readable lines: `status=completed|partial|failed|config_required`, `output_path=`, `run_dir=`, `models=`, optional `failed=`, `elapsed=`. `partial` means at least one lane failed while others succeeded. Exit codes: 0 = at least one lane succeeded (including partial), 1 = all lanes failed or bad input, 3 = lineup not configured (2 is reserved for argparse usage errors).

The run directory holds `<model-slug>.md` per lane plus the combined `result.md` (status table + full opinions + optional synthesis). The final report's status table records the requested thinking level for every council lane and optional synthesis model as an audit field; it does not include model thinking content. Raw `<model-slug>.events.jsonl` streams are kept only for failed lanes, or for all lanes with `--events`. If every lane fails, synthesis is skipped and `result.md` says so explicitly. Reported token usage and cost are accumulated across every turn of a lane, including tool-call turns; `--thinking` is the main cost and latency lever.

Run data accumulates: after each run the script reports on stderr how many runs and how many MB are stored under `<state_home>/runs/` (e.g. `[council] state: 12 runs, 45.0 MB accumulated at ... (delete it anytime)`). Surface this to the user when it grows large; purging old run directories is always safe.

## Environment variables

Both are escape hatches for developing or testing the skill itself — a normal council run needs neither, and neither should ever be set per-project.

- `PI_COUNCIL_STATE_HOME` — overrides the state directory (config + run artifacts). Default: `$XDG_STATE_HOME/pi-council` or `~/.local/state/pi-council` on POSIX, `%LOCALAPPDATA%\pi-council` on Windows. The state is intentionally **user-level**: the saved lineup works in every workspace, so a new workspace is not a cold start, and the script creates and manages the directory itself. Legitimate use: an **isolated test run** — point it at a throwaway directory (e.g. `PI_COUNCIL_STATE_HOME=/tmp/pi-council-test`) to simulate a clean first run; the skill's own unit tests work this way.
- `PI_COUNCIL_PI_BIN` — overrides the pi executable resolution (default: `pi` from `PATH`).

## Failure handling

- A lane that fails (unknown model, timeout, empty reply) does not sink the run; it appears as `failed (...)` in the status table and in the `failed=` stdout line. Failed lanes always keep their `events.jsonl`, and an empty-reply error points at it for diagnosis.
- A timed-out lane is killed together with its whole process tree; its partial output is still salvaged into `events.jsonl`.
- If a lane reports `Model "..." not found`, the saved lineup is stale: ask the user for a replacement and re-run with `--models ... --save`.
- If every custom-provider lane fails at once, suspect a provider/auth outage rather than the task; check `pi auth check --provider <name>`. Note that extension-registered providers (e.g. LiteLLM gateways) can report `not_ready` there yet still work — an actual lane result beats the auth check.

## Tests

```bash
python3 -m unittest discover -s tests     # from the skill directory
```
