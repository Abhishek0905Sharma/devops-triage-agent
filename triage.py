import os
import sys
import json
import time
import argparse
import subprocess
from typing import Generator
from pathlib import Path
from anthropic import Anthropic

# ─── ANSI colours (CLI only) ─────────────────────────────────────────────────
COLOR_RESET   = "\033[0m"
COLOR_THOUGHT = "\033[36m"
COLOR_TOOL_CALL   = "\033[33m"
COLOR_TOOL_RESULT = "\033[34m"
COLOR_SUCCESS = "\033[32m"
COLOR_ERROR   = "\033[31m"
COLOR_INFO    = "\033[35m"

def _print(text: str, color: str = ""):
    print(f"{color}{text}{COLOR_RESET}")

# ─── Tool implementations ─────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.resolve()

def read_file(path: str) -> str:
    p = (BASE_DIR / path).resolve()
    if not str(p).startswith(str(BASE_DIR)):
        return "Error: Access denied (path outside repository)"
    if not p.exists():
        return f"Error: File '{path}' not found"
    if p.is_dir():
        return f"Error: '{path}' is a directory, not a file"
    try:
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {e}"

def search_codebase(query: str) -> str:
    results = []
    base = BASE_DIR / "buggy_app"
    if not base.exists():
        return "Error: buggy_app directory not found"
    for p in base.rglob("*.py"):
        if p.is_file():
            try:
                for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
                    if query.lower() in line.lower():
                        results.append(f"{p.relative_to(BASE_DIR).as_posix()}:{i}: {line.strip()}")
            except Exception:
                pass
    return "\n".join(results[:50]) if results else f"No matches found for '{query}'"

def get_recent_commits(file_path: str = None) -> str:
    cmd = ["git", "log", "-n", "5", "--oneline"]
    if file_path:
        cmd.extend(["--", file_path])
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=str(BASE_DIR))
        return res.stdout or "No commit history found."
    except Exception:
        commits = [
            "a9b7b13 Initial commit with buggy codebase",
            "8f3d1e2 Setup API routes and database models",
            "2c9a1b0 Implement users router and error handling"
        ]
        prefix = f"Simulated history for {file_path}:\n" if file_path else "Simulated repository history:\n"
        return prefix + "\n".join(commits)

def propose_fix(file_path: str, diff: str, error_id: str = None) -> str:
    outputs_dir = BASE_DIR / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    suffix = f"_{error_id}" if error_id else ""
    safe_name = Path(file_path).name.replace(".", "_")
    patch_path = outputs_dir / f"fix_{safe_name}{suffix}.patch"
    try:
        patch_path.write_text(diff, encoding="utf-8")
        return f"Success: Code fix (diff) saved to {patch_path.as_posix()}"
    except Exception as e:
        return f"Error saving proposed fix: {e}"

def write_report(content: str, error_id: str = None) -> str:
    outputs_dir = BASE_DIR / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    suffix = f"_{error_id}" if error_id else ""
    report_path = outputs_dir / f"report{suffix}.md"
    try:
        report_path.write_text(content, encoding="utf-8")
        return f"Success: Structured triage report saved to {report_path.as_posix()}"
    except Exception as e:
        return f"Error saving report: {e}"

TOOLS_MAP = {
    "read_file": read_file,
    "search_codebase": search_codebase,
    "get_recent_commits": get_recent_commits,
    "propose_fix": propose_fix,
    "write_report": write_report,
}

CLAUDE_TOOLS = [
    {
        "name": "read_file",
        "description": "Reads the content of a file in the codebase. Use this to read the source code of files mentioned in stack traces.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "File path relative to the project root."}},
            "required": ["path"]
        }
    },
    {
        "name": "search_codebase",
        "description": "Searches Python files inside buggy_app/ for a query string.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search term to look for."}},
            "required": ["query"]
        }
    },
    {
        "name": "get_recent_commits",
        "description": "Gets recent git commit history. Optionally filter by file_path.",
        "input_schema": {
            "type": "object",
            "properties": {"file_path": {"type": "string", "description": "Optional file path."}}
        }
    },
    {
        "name": "propose_fix",
        "description": "Saves a git diff/patch for a simple bug fix (typo, null check). Do NOT use for logic bugs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {"type": "string"},
                "diff": {"type": "string", "description": "Full unified diff content."},
                "error_id": {"type": "string"}
            },
            "required": ["file_path", "diff"]
        }
    },
    {
        "name": "write_report",
        "description": "Writes a structured markdown triage report for logic bugs. Do NOT use for simple bugs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Markdown report content."},
                "error_id": {"type": "string"}
            },
            "required": ["content"]
        }
    }
]

SYSTEM_PROMPT = """You are an expert DevOps Incident Triage Agent.
Your job is to investigate error logs/alerts, locate the relevant files and functions in the codebase, and triage the bug.

CRITICAL INSTRUCTIONS:
1. Gather context first. Use 'search_codebase', 'read_file', and 'get_recent_commits' to understand the code around the error. Do not make assumptions.
2. Determine the nature of the bug:
   - SIMPLE BUGS: If the bug is a simple typo (e.g. NameError) or a missing null check (e.g. AttributeError), propose a code fix in standard git diff/patch format using the 'propose_fix' tool.
   - LOGIC BUGS: If the bug is a logic error (wrong comparison operator, loop condition, incorrect logic), you MUST NOT propose an auto-fix. Write a structured triage report using the 'write_report' tool.
3. Triage Report structure:
   - Summary, Root Cause Hypothesis, Affected Files and Functions, Suggested Fix / Next Steps, Confidence Level.
4. Think aloud before calling any tools.
"""

# ─── Demo mode (no API key) ───────────────────────────────────────────────────
def _demo_steps(error_log: dict, error_id: str) -> Generator[dict, None, None]:
    """Yields SSE-compatible dicts for demo mode (no API key)."""
    error_type = error_log.get("error_type", "")
    yield {"type": "info", "text": "ANTHROPIC_API_KEY not set — running in DEMO MODE"}

    if error_type == "NameError":
        yield {"type": "thought", "text": "I need to triage the NameError. The stack trace points to 'buggy_app/services/users.py' line 50. Let me read that file."}
        yield {"type": "tool_call", "name": "read_file", "input": {"path": "buggy_app/services/users.py"}}
        res = read_file("buggy_app/services/users.py")
        yield {"type": "tool_result", "text": f"Read {len(res)} characters from services/users.py"}

        yield {"type": "thought", "text": "Found the issue: line 49 assigns `upd_user = user`, but line 50 returns `updted_user` — a clear typo. Checking git history."}
        yield {"type": "tool_call", "name": "get_recent_commits", "input": {"file_path": "buggy_app/services/users.py"}}
        commits = get_recent_commits("buggy_app/services/users.py")
        yield {"type": "tool_result", "text": commits.strip()}

        yield {"type": "thought", "text": "This is a simple NameError typo — safe to auto-fix. Generating patch."}
        diff = (
            "diff --git a/buggy_app/services/users.py b/buggy_app/services/users.py\n"
            "index 6f3a8b2..2c91df0 100644\n"
            "--- a/buggy_app/services/users.py\n"
            "+++ b/buggy_app/services/users.py\n"
            "@@ -47,4 +47,4 @@ def update_user(user_id: int, update_data: UserUpdate) -> User | None:\n"
            "         user.profile = update_data.profile\n"
            "         \n"
            "     upd_user = user\n"
            "-    return updted_user\n"
            "+    return upd_user\n"
        )
        yield {"type": "tool_call", "name": "propose_fix", "input": {"file_path": "buggy_app/services/users.py", "diff": "...", "error_id": error_id}}
        fix_result = propose_fix("buggy_app/services/users.py", diff, error_id)
        yield {"type": "tool_result", "text": fix_result}
        yield {"type": "final", "outcome": "fix", "content": diff}

    elif error_type == "AttributeError":
        yield {"type": "thought", "text": "Investigating AttributeError: 'NoneType' object has no attribute 'bio'. Stack trace points to routers/users.py line 28. Reading the file."}
        yield {"type": "tool_call", "name": "read_file", "input": {"path": "buggy_app/routers/users.py"}}
        res = read_file("buggy_app/routers/users.py")
        yield {"type": "tool_result", "text": f"Read {len(res)} characters from routers/users.py"}

        yield {"type": "thought", "text": "Line 28 accesses `user.profile.bio` directly. If `profile` is None this crashes. Checking models.py to confirm profile is Optional."}
        yield {"type": "tool_call", "name": "read_file", "input": {"path": "buggy_app/models.py"}}
        res2 = read_file("buggy_app/models.py")
        yield {"type": "tool_result", "text": f"Read {len(res2)} characters from models.py — profile: Profile | None = None confirmed."}

        yield {"type": "thought", "text": "Simple null-check omission. Profile is optional and can be None. Generating patch with ternary guard."}
        diff = (
            "diff --git a/buggy_app/routers/users.py b/buggy_app/routers/users.py\n"
            "index c2d1e2e..e9185fa 100644\n"
            "--- a/buggy_app/routers/users.py\n"
            "+++ b/buggy_app/routers/users.py\n"
            "@@ -25,4 +25,5 @@ def get_user_bio(user_id: int):\n"
            "     if not user:\n"
            "         raise HTTPException(status_code=404, detail=\"User not found\")\n"
            "     \n"
            "-    return {\"username\": user.username, \"bio\": user.profile.bio}\n"
            "+    bio_content = user.profile.bio if user.profile else None\n"
            "+    return {\"username\": user.username, \"bio\": bio_content}\n"
        )
        yield {"type": "tool_call", "name": "propose_fix", "input": {"file_path": "buggy_app/routers/users.py", "diff": "...", "error_id": error_id}}
        fix_result = propose_fix("buggy_app/routers/users.py", diff, error_id)
        yield {"type": "tool_result", "text": fix_result}
        yield {"type": "final", "outcome": "fix", "content": diff}

    elif error_type == "LogicBugAlert":
        yield {"type": "thought", "text": "Non-crashing logic anomaly: POST /users rejects all new emails. The hint points to `is_email_taken` in services/users.py. Reading the file."}
        yield {"type": "tool_call", "name": "read_file", "input": {"path": "buggy_app/services/users.py"}}
        res = read_file("buggy_app/services/users.py")
        yield {"type": "tool_result", "text": f"Read {len(res)} characters from services/users.py"}

        yield {"type": "thought", "text": (
            "Found it — line 16 uses `!=` instead of `==`:\n"
            "  if user.email != email:  # Should be ==\n"
            "This returns True as soon as ANY existing user's email differs from the input, "
            "so every new email is falsely flagged as taken.\n"
            "This is a logic bug affecting business behaviour — I must NOT auto-fix. Writing triage report."
        )}
        report = (
            f"# DevOps Incident Triage Report: LogicBugAlert ({error_id})\n\n"
            "## Summary\n"
            "The `POST /users` endpoint returns `400 Email is already registered` for every new registration attempt, "
            "preventing any new user from signing up.\n\n"
            "## Root Cause Hypothesis\n"
            "`is_email_taken` in `buggy_app/services/users.py` uses `!=` instead of `==`:\n"
            "```python\n"
            "def is_email_taken(email: str) -> bool:\n"
            "    for user in USERS_DB.values():\n"
            "        if user.email != email:  # Logic Error!\n"
            "            return True\n"
            "    return False\n"
            "```\n"
            "As long as any existing user has a different email, the function returns `True` on the first iteration, "
            "always marking the new email as taken.\n\n"
            "## Affected Files and Functions\n"
            "- **File**: `buggy_app/services/users.py`\n"
            "- **Function**: `is_email_taken(email: str)` — line 16\n"
            "- **Endpoint**: `POST /users` → `buggy_app/routers/users.py`\n\n"
            "## Suggested Fix / Next Steps\n"
            "1. Change `!=` to `==` on line 16.\n"
            "2. Add unit tests covering: new unique email (should succeed), duplicate email (should fail).\n\n"
            "## Confidence Level\n"
            "**High** — the operator inversion perfectly explains all reported symptoms."
        )
        yield {"type": "tool_call", "name": "write_report", "input": {"content": "...", "error_id": error_id}}
        rep_result = write_report(report, error_id)
        yield {"type": "tool_result", "text": rep_result}
        yield {"type": "final", "outcome": "report", "content": report}

    else:
        yield {"type": "error", "text": f"Unknown error_type '{error_type}' — cannot simulate."}

# ─── Real Claude API (streaming-compatible generator) ─────────────────────────
def _claude_steps(error_log: dict, error_id: str, model: str) -> Generator[dict, None, None]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    client = Anthropic(api_key=api_key)
    messages = [{
        "role": "user",
        "content": (
            "Investigate the following error log. Use your tools to search the codebase, "
            "read relevant source files, analyse git commits, then choose either "
            "'propose_fix' (simple bugs) or 'write_report' (logic bugs).\n\n"
            f"Error Log JSON:\n{json.dumps(error_log, indent=2)}"
        )
    }]

    for step in range(1, 11):
        yield {"type": "info", "text": f"--- Step {step} ---"}
        try:
            response = client.messages.create(
                model=model,
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=CLAUDE_TOOLS,
            )
        except Exception as e:
            yield {"type": "error", "text": f"API Error: {e}"}
            return

        response_blocks = []
        last_fix = None
        last_report = None

        for block in response.content:
            if block.type == "text":
                response_blocks.append({"type": "text", "text": block.text})
                yield {"type": "thought", "text": block.text}
            elif block.type == "tool_use":
                response_blocks.append({"type": "tool_use", "id": block.id, "name": block.name, "input": block.input})
                yield {"type": "tool_call", "name": block.name, "input": block.input}

        messages.append({"role": "assistant", "content": response_blocks})

        tool_calls = [b for b in response.content if b.type == "tool_use"]
        if not tool_calls:
            yield {"type": "info", "text": "Agent finished reasoning."}
            break

        tool_responses = []
        for tc in tool_calls:
            name, args, call_id = tc.name, dict(tc.input), tc.id
            if name in ("propose_fix", "write_report") and "error_id" not in args:
                args["error_id"] = error_id
            func = TOOLS_MAP.get(name)
            result = func(**args) if func else f"Error: unknown tool '{name}'"
            yield {"type": "tool_result", "text": result}

            # Capture final output for display
            if name == "propose_fix":
                last_fix = args.get("diff", "")
            elif name == "write_report":
                last_report = args.get("content", "")

            tool_responses.append({"type": "tool_result", "tool_use_id": call_id, "content": result})

        messages.append({"role": "user", "content": tool_responses})

        if last_fix:
            yield {"type": "final", "outcome": "fix", "content": last_fix}
        elif last_report:
            yield {"type": "final", "outcome": "report", "content": last_report}

# ─── Public API ───────────────────────────────────────────────────────────────
def run_triage(error_log: dict, model: str = "claude-3-5-sonnet-latest") -> Generator[dict, None, None]:
    """
    Generator that yields structured event dicts for each triage step.
    Works with the Claude API when ANTHROPIC_API_KEY is set, or falls
    back to Demo Mode for presentation / testing without a key.

    Event dict shapes:
        {"type": "info"|"error",   "text": str}
        {"type": "thought",         "text": str}
        {"type": "tool_call",       "name": str, "input": dict}
        {"type": "tool_result",     "text": str}
        {"type": "final",           "outcome": "fix"|"report", "content": str}
    """
    error_id = error_log.get("event_id", "unknown")
    api_key  = os.environ.get("ANTHROPIC_API_KEY")

    yield {"type": "info", "text": f"Starting triage — event_id: {error_id}"}
    yield {"type": "info", "text": f"Error type: {error_log.get('error_type')}"}
    yield {"type": "info", "text": f"Message: {error_log.get('message')}"}

    gen = _claude_steps(error_log, error_id, model) if api_key else _demo_steps(error_log, error_id)
    yield from gen

# ─── CLI entry point ──────────────────────────────────────────────────────────
def run_triage_flow(error_log_path: str, model_name: str):
    path = Path(error_log_path)
    if not path.exists():
        _print(f"Error: Log file '{error_log_path}' not found.", COLOR_ERROR)
        sys.exit(1)
    try:
        error_log = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        _print(f"Error parsing JSON: {e}", COLOR_ERROR)
        sys.exit(1)

    for event in run_triage(error_log, model_name):
        t = event.get("type")
        if t == "thought":
            _print(event["text"], COLOR_THOUGHT)
        elif t == "tool_call":
            _print(f"[Tool Call] {event['name']}({json.dumps(event['input'])})", COLOR_TOOL_CALL)
        elif t == "tool_result":
            _print(f"[Tool Result] {event['text']}", COLOR_TOOL_RESULT)
        elif t == "info":
            _print(f"[*] {event['text']}", COLOR_INFO)
        elif t == "error":
            _print(f"[!] {event['text']}", COLOR_ERROR)
        elif t == "final":
            outcome = event["outcome"]
            badge = "AUTO-FIX PROPOSED" if outcome == "fix" else "TRIAGE REPORT"
            _print(f"\n{'='*60}\n{badge}\n{'='*60}", COLOR_SUCCESS)
            _print(event["content"], COLOR_THOUGHT)

    _print("\n[*] Triage workflow complete.", COLOR_SUCCESS)

def main():
    parser = argparse.ArgumentParser(description="DevOps Incident Triage Agent CLI")
    parser.add_argument("--error", required=True, help="Path to Sentry/error JSON file")
    parser.add_argument("--model", default="claude-3-5-sonnet-latest", help="Claude model to use")
    args = parser.parse_args()
    run_triage_flow(args.error, args.model)

if __name__ == "__main__":
    main()
