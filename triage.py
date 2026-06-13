import os
import sys
import json
import time
import argparse
import subprocess
from pathlib import Path
from anthropic import Anthropic

# ANSI Color Codes for beautiful CLI printing
COLOR_RESET = "\033[0m"
COLOR_THOUGHT = "\033[36m"  # Cyan
COLOR_TOOL_CALL = "\033[33m"  # Yellow
COLOR_TOOL_RESULT = "\033[34m"  # Blue
COLOR_SUCCESS = "\033[32m"  # Green
COLOR_ERROR = "\033[31m"  # Red
COLOR_INFO = "\033[35m"  # Magenta

def print_colored(text: str, color_code: str):
    print(f"{color_code}{text}{COLOR_RESET}")

# --- Agent Tools implementation ---

def read_file(path: str) -> str:
    """Reads the content of a file in the codebase."""
    p = Path(path).resolve()
    base = Path(".").resolve()
    # Prevent directory traversal
    if not str(p).startswith(str(base)):
        return "Error: Access denied (path outside repository)"
    if not p.exists():
        return f"Error: File '{path}' not found"
    if p.is_dir():
        return f"Error: '{path}' is a directory, not a file"
    try:
        return p.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {str(e)}"

def search_codebase(query: str) -> str:
    """Searches codebase python files for a given string query (simple grep)."""
    results = []
    base = Path("buggy_app")
    if not base.exists():
        return "Error: buggy_app directory not found"
    for p in base.rglob("*.py"):
        if p.is_file():
            try:
                content = p.read_text(encoding="utf-8")
                for i, line in enumerate(content.splitlines(), 1):
                    if query.lower() in line.lower():
                        results.append(f"{p.as_posix()}:{i}: {line.strip()}")
            except Exception as e:
                pass
    if not results:
        return f"No matches found for '{query}'"
    return "\n".join(results[:50])

def get_recent_commits(file_path: str = None) -> str:
    """Gets the recent git commit history for the codebase or a specific file."""
    cmd = ["git", "log", "-n", "5", "--oneline"]
    if file_path:
        cmd.extend(["--", file_path])
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return res.stdout if res.stdout else "No commit history found."
    except Exception:
        # Fallback simulated commit history
        simulated_commits = [
            "a9b7b13 Initial commit with buggy codebase",
            "8f3d1e2 Setup API routes and database models",
            "2c9a1b0 Implement users router and error handling"
        ]
        if file_path:
            return f"Simulated history for {file_path}:\n" + "\n".join(simulated_commits)
        return "Simulated repository history:\n" + "\n".join(simulated_commits)

def propose_fix(file_path: str, diff: str, error_id: str = None) -> str:
    """Proposes a code fix for a simple bug by saving a patch/diff file."""
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(exist_ok=True)
    suffix = f"_{error_id}" if error_id else ""
    safe_name = Path(file_path).name.replace(".", "_")
    patch_path = outputs_dir / f"fix_{safe_name}{suffix}.patch"
    try:
        patch_path.write_text(diff, encoding="utf-8")
        return f"Success: Code fix (diff) saved to {patch_path.as_posix()}"
    except Exception as e:
        return f"Error saving proposed fix: {str(e)}"

def write_report(content: str, error_id: str = None) -> str:
    """Writes a structured triage report for a logic bug."""
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(exist_ok=True)
    suffix = f"_{error_id}" if error_id else ""
    report_path = outputs_dir / f"report{suffix}.md"
    try:
        report_path.write_text(content, encoding="utf-8")
        return f"Success: Structured triage report saved to {report_path.as_posix()}"
    except Exception as e:
        return f"Error saving report: {str(e)}"

# Maps tool names to their python functions
TOOLS_MAP = {
    "read_file": read_file,
    "search_codebase": search_codebase,
    "get_recent_commits": get_recent_commits,
    "propose_fix": propose_fix,
    "write_report": write_report
}

# Anthropic Tool Schemas
CLAUDE_TOOLS = [
    {
        "name": "read_file",
        "description": "Reads the content of a file in the codebase. Use this to read the source code of files mentioned in stack traces.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "The path to the file relative to the project root (e.g. 'buggy_app/services/users.py')."
                }
            },
            "required": ["path"]
        }
    },
    {
        "name": "search_codebase",
        "description": "Searches python files inside buggy_app/ for a query string. Use this to find variables, functions, or imports.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search term to look for in the codebase."
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "get_recent_commits",
        "description": "Gets the recent git commit history. Provide a file_path to check modifications for a specific file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Optional file path relative to the project root."
                }
            }
        }
    },
    {
        "name": "propose_fix",
        "description": "Proposes a code fix for a simple bug (e.g. typo, missing null check) by writing a patch/diff. Do NOT use this tool for logic bugs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path of the file to be fixed."
                },
                "diff": {
                    "type": "string",
                    "description": "The git diff/patch containing the proposed changes. Include line contexts so it can be reviewed and applied."
                },
                "error_id": {
                    "type": "string",
                    "description": "Optional identifier or event_id to name the patch file."
                }
            },
            "required": ["file_path", "diff"]
        }
    },
    {
        "name": "write_report",
        "description": "Writes a structured triage report for a logic bug or complex error. Do NOT use this tool for simple bugs.",
        "input_schema": {
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "The markdown content of the triage report."
                },
                "error_id": {
                    "type": "string",
                    "description": "Optional identifier or event_id to name the report file."
                }
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
   - SIMPLE BUGS: If the bug is a simple typo (e.g. NameError) or a missing null check (e.g. AttributeError), you should propose a code fix in standard git diff/patch format. Use the 'propose_fix' tool.
   - LOGIC BUGS: If the bug is a logic error (e.g. wrong comparison operator, loop condition, incorrect logic that changes behavior rather than throwing a simple typo/null exception), you MUST NOT propose an auto-fix. Instead, you MUST write a structured triage report. Use the 'write_report' tool.
3. Structure for Triage Reports:
   - Summary: Brief description of the incident.
   - Root Cause Hypothesis: Your analysis of why this behavior is happening and how the logic is flawed.
   - Affected Files and Functions: List the code references.
   - Suggested Fix / Next Steps: Clear explanation of what needs to be changed.
   - Confidence Level: High, Medium, or Low, with a brief explanation.
4. Show your step-by-step reasoning. Think aloud before calling any tools.
"""

def simulate_demo_mode(error_log: dict, error_id: str):
    """Simulates the agent's thoughts and tool calls for demonstration purposes."""
    print_colored("[!] ANTHROPIC_API_KEY not found in environment.", COLOR_ERROR)
    print_colored("[!] RUNNING IN DEMO MODE (SIMULATED COGNITIVE LOOP)", COLOR_INFO)
    print("")
    time.sleep(1)

    error_type = error_log.get("error_type", "")

    if error_type == "NameError":
        # Step 1: Read services/users.py
        print_colored("--- Step 1 ---", COLOR_INFO)
        thought = (
            "I need to triage the NameError 'name 'updted_user' is not defined'. The stack trace shows it occurred "
            "in 'buggy_app/services/users.py' at line 50 inside the 'update_user' function. "
            "Let me use the read_file tool to inspect 'buggy_app/services/users.py' and look at the update_user function."
        )
        print_colored(thought, COLOR_THOUGHT)
        time.sleep(1.5)
        print_colored(f"[Tool Call] read_file({{\"path\": \"buggy_app/services/users.py\"}})", COLOR_TOOL_CALL)
        time.sleep(1)
        res = read_file("buggy_app/services/users.py")
        print_colored(f"[Tool Result] (Read {len(res)} characters)", COLOR_TOOL_RESULT)
        print("")

        # Step 2: Get recent commits
        print_colored("--- Step 2 ---", COLOR_INFO)
        thought = (
            "Looking at the source code of buggy_app/services/users.py:\n"
            "On line 49 we have: `upd_user = user`.\n"
            "On line 50 we have: `return updted_user`.\n"
            "This is a clear typo where 'updted_user' is returned instead of 'upd_user'.\n"
            "Let me inspect recent commits for this file to see if this was introduced recently."
        )
        print_colored(thought, COLOR_THOUGHT)
        time.sleep(1.5)
        print_colored(f"[Tool Call] get_recent_commits({{\"file_path\": \"buggy_app/services/users.py\"}})", COLOR_TOOL_CALL)
        time.sleep(1)
        res_commits = get_recent_commits("buggy_app/services/users.py")
        print_colored(f"[Tool Result] {res_commits.strip()}", COLOR_TOOL_RESULT)
        print("")

        # Step 3: Propose Fix
        print_colored("--- Step 3 ---", COLOR_INFO)
        thought = (
            "This is a simple typo bug (NameError). According to my instructions, I should auto-fix simple bugs "
            "by proposing a code fix in git diff format. Let me create a patch for this file."
        )
        print_colored(thought, COLOR_THOUGHT)
        time.sleep(1.5)
        diff_content = (
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
        print_colored(f"[Tool Call] propose_fix({{\"file_path\": \"buggy_app/services/users.py\", \"diff\": \"...\", \"error_id\": \"{error_id}\"}})", COLOR_TOOL_CALL)
        time.sleep(1)
        res_fix = propose_fix("buggy_app/services/users.py", diff_content, error_id)
        print_colored(f"[Tool Result] {res_fix}", COLOR_TOOL_RESULT)
        print("")

        print_colored("[*] Agent finished reasoning.", COLOR_INFO)

    elif error_type == "AttributeError":
        # Step 1: Read routers/users.py
        print_colored("--- Step 1 ---", COLOR_INFO)
        thought = (
            "I need to investigate the AttributeError: 'NoneType' object has no attribute 'bio'. "
            "The stack trace points to 'buggy_app/routers/users.py' line 28 in the 'get_user_bio' function. "
            "Let me read the file 'buggy_app/routers/users.py' to examine the code."
        )
        print_colored(thought, COLOR_THOUGHT)
        time.sleep(1.5)
        print_colored(f"[Tool Call] read_file({{\"path\": \"buggy_app/routers/users.py\"}})", COLOR_TOOL_CALL)
        time.sleep(1)
        res = read_file("buggy_app/routers/users.py")
        print_colored(f"[Tool Result] (Read {len(res)} characters)", COLOR_TOOL_RESULT)
        print("")

        # Step 2: Read models.py
        print_colored("--- Step 2 ---", COLOR_INFO)
        thought = (
            "Looking at buggy_app/routers/users.py:\n"
            "On line 28: `return {\"username\": user.username, \"bio\": user.profile.bio}`\n"
            "This line accesses user.profile.bio. If user.profile is None, this will throw an AttributeError.\n"
            "Let me check 'buggy_app/models.py' to confirm if the profile attribute is indeed optional."
        )
        print_colored(thought, COLOR_THOUGHT)
        time.sleep(1.5)
        print_colored(f"[Tool Call] read_file({{\"path\": \"buggy_app/models.py\"}})", COLOR_TOOL_CALL)
        time.sleep(1)
        res_models = read_file("buggy_app/models.py")
        print_colored(f"[Tool Result] (Read {len(res_models)} characters)", COLOR_TOOL_RESULT)
        print("")

        # Step 3: Propose Fix
        print_colored("--- Step 3 ---", COLOR_INFO)
        thought = (
            "I see that in models.py, User defines `profile: Profile | None = None`. "
            "Therefore, profile can be null (None). Accessing user.profile.bio without checking "
            "causes this AttributeError. Since this is a simple null check bug, I should propose a patch/diff "
            "to check if profile is None."
        )
        print_colored(thought, COLOR_THOUGHT)
        time.sleep(1.5)
        diff_content = (
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
        print_colored(f"[Tool Call] propose_fix({{\"file_path\": \"buggy_app/routers/users.py\", \"diff\": \"...\", \"error_id\": \"{error_id}\"}})", COLOR_TOOL_CALL)
        time.sleep(1)
        res_fix = propose_fix("buggy_app/routers/users.py", diff_content, error_id)
        print_colored(f"[Tool Result] {res_fix}", COLOR_TOOL_RESULT)
        print("")

        print_colored("[*] Agent finished reasoning.", COLOR_INFO)

    elif error_type == "LogicBugAlert":
        # Step 1: Read services/users.py
        print_colored("--- Step 1 ---", COLOR_INFO)
        thought = (
            "I need to triage a non-crashing logic bug alert. The reported symptom is that the registration endpoint "
            "fails validation for all new emails. The stack trace/context points to the function 'is_email_taken' in "
            "'buggy_app/services/users.py' around line 16. Let me read this file first."
        )
        print_colored(thought, COLOR_THOUGHT)
        time.sleep(1.5)
        print_colored(f"[Tool Call] read_file({{\"path\": \"buggy_app/services/users.py\"}})", COLOR_TOOL_CALL)
        time.sleep(1)
        res = read_file("buggy_app/services/users.py")
        print_colored(f"[Tool Result] (Read {len(res)} characters)", COLOR_TOOL_RESULT)
        print("")

        # Step 2: Analyze & Write Report
        print_colored("--- Step 2 ---", COLOR_INFO)
        thought = (
            "Analyzing 'is_email_taken' in buggy_app/services/users.py:\n"
            "```python\n"
            "def is_email_taken(email: str) -> bool:\n"
            "    for user in USERS_DB.values():\n"
            "        if user.email != email:  # Should be ==\n"
            "            return True\n"
            "    return False\n"
            "```\n"
            "The comparison operator is indeed `!=` instead of `==`. This checks if ANY user's email in the DB is not "
            "equal to the input email, and immediately returns True. Since there are always other users in the DB, "
            "this will evaluate to True for any registration, incorrectly claiming the email is taken.\n"
            "This is a logic bug that alters functional behavior but doesn't crash the server. According to my rules, "
            "I MUST NOT auto-fix logic bugs. Instead, I must write a structured triage report."
        )
        print_colored(thought, COLOR_THOUGHT)
        time.sleep(1.5)
        report_content = (
            f"# DevOps Incident Triage Report: LogicBugAlert ({error_id})\n\n"
            "## Summary\n"
            "The registration endpoint (`POST /users`) is failing for all new email registrations, returning "
            "a `400 Bad Request` with the message 'Email is already registered'. This prevents new users from signing up.\n\n"
            "## Root Cause Hypothesis\n"
            "In `buggy_app/services/users.py`, the function `is_email_taken` contains a critical logic error. "
            "It uses the inequality operator (`!=`) instead of the equality operator (`==`) when checking if an email is taken:\n"
            "```python\n"
            "def is_email_taken(email: str) -> bool:\n"
            "    for user in USERS_DB.values():\n"
            "        if user.email != email:  # Logic Error!\n"
            "            return True\n"
            "    return False\n"
            "```\n"
            "As long as there is at least one seeded user whose email does not match the new user's email, "
            "the condition evaluates to `True` immediately on the first iteration and returns `True`, "
            "preventing any registrations.\n\n"
            "## Affected Files and Functions\n"
            "- **File**: `buggy_app/services/users.py`\n"
            "- **Function**: `is_email_taken(email: str)`\n"
            "- **Impacted Endpoint**: `POST /users` (defined in `buggy_app/routers/users.py`)\n\n"
            "## Suggested Fix / Next Steps\n"
            "1. Change the comparison operator on line 16 from `!=` to `==`:\n"
            "```python\n"
            "def is_email_taken(email: str) -> bool:\n"
            "    for user in USERS_DB.values():\n"
            "        if user.email == email:\n"
            "            return True\n"
            "    return False\n"
            "```\n"
            "2. Add automated unit tests to verify that new emails can register, while existing emails are blocked.\n\n"
            "## Confidence Level\n"
            "**High**. The issue is a clear comparison logic mistake that matches all reported symptoms perfectly."
        )
        print_colored(f"[Tool Call] write_report({{\"content\": \"...\", \"error_id\": \"{error_id}\"}})", COLOR_TOOL_CALL)
        time.sleep(1)
        res_report = write_report(report_content, error_id)
        print_colored(f"[Tool Result] {res_report}", COLOR_TOOL_RESULT)
        print("")

        print_colored("[*] Agent finished reasoning.", COLOR_INFO)

    else:
        print_colored("Unknown error type in log file. Cannot run demo simulation.", COLOR_ERROR)

    print("")
    print_colored("[*] Triage workflow complete.", COLOR_SUCCESS)


def run_triage_flow(error_log_path: str, model_name: str):
    # 1. Read error log
    path = Path(error_log_path)
    if not path.exists():
        print_colored(f"Error: Log file '{error_log_path}' not found.", COLOR_ERROR)
        sys.exit(1)
        
    try:
        error_log = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print_colored(f"Error parsing log file as JSON: {str(e)}", COLOR_ERROR)
        sys.exit(1)
        
    error_id = error_log.get("event_id", "unknown")
    print_colored(f"[*] Starting triage for event ID: {error_id}", COLOR_INFO)
    print_colored(f"[*] Error Type: {error_log.get('error_type')}", COLOR_INFO)
    print_colored(f"[*] Message: {error_log.get('message')}", COLOR_INFO)
    print("")

    # 2. Setup Anthropic client (fallback to Demo Mode if key is missing)
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        simulate_demo_mode(error_log, error_id)
        return
        
    client = Anthropic(api_key=api_key)
    
    # 3. Create message history
    messages = [
        {
            "role": "user",
            "content": f"Investigate the following error log. Use your tools to search the codebase, read relevant source files, analyze git commits, and then choose either 'propose_fix' (for simple bugs) or 'write_report' (for logic bugs).\n\nError Log JSON:\n{json.dumps(error_log, indent=2)}"
        }
    ]
    
    # 4. Orchestration Loop
    max_steps = 10
    step = 0
    
    while step < max_steps:
        step += 1
        print_colored(f"--- Step {step} ---", COLOR_INFO)
        
        try:
            response = client.messages.create(
                model=model_name,
                max_tokens=4000,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=CLAUDE_TOOLS
            )
        except Exception as e:
            print_colored(f"API Error: {str(e)}", COLOR_ERROR)
            sys.exit(1)
            
        # Add assistant response to history
        response_blocks = []
        for block in response.content:
            if block.type == 'text':
                response_blocks.append({
                    "type": "text",
                    "text": block.text
                })
                print_colored(block.text, COLOR_THOUGHT)
            elif block.type == 'tool_use':
                response_blocks.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input
                })
                print_colored(f"[Tool Call] {block.name}({json.dumps(block.input)})", COLOR_TOOL_CALL)
                
        messages.append({
            "role": "assistant",
            "content": response_blocks
        })
        
        # Check if there are tool calls to execute
        tool_calls = [b for b in response.content if b.type == 'tool_use']
        if not tool_calls:
            print_colored("[*] Agent finished reasoning.", COLOR_INFO)
            break
            
        tool_responses = []
        for tool_call in tool_calls:
            name = tool_call.name
            args = tool_call.input
            call_id = tool_call.id
            
            # Inject error_id automatically if not provided
            if name in ["propose_fix", "write_report"] and "error_id" not in args:
                args["error_id"] = error_id
                
            func = TOOLS_MAP.get(name)
            if not func:
                result = f"Error: Tool '{name}' is not supported."
            else:
                try:
                    result = func(**args)
                except Exception as e:
                    result = f"Error executing tool: {str(e)}"
            
            print_colored(f"[Tool Result] {result}", COLOR_TOOL_RESULT)
            tool_responses.append({
                "type": "tool_result",
                "tool_use_id": call_id,
                "content": result
            })
            
        messages.append({
            "role": "user",
            "content": tool_responses
        })
        print("")
        
    print("")
    print_colored("[*] Triage workflow complete.", COLOR_SUCCESS)

def main():
    parser = argparse.ArgumentParser(description="DevOps Incident Triage Agent CLI")
    parser.add_argument(
        "--error", 
        required=True, 
        help="Path to Sentry/error JSON file"
    )
    parser.add_argument(
        "--model", 
        default="claude-3-5-sonnet-latest", 
        help="Claude model to use (default: claude-3-5-sonnet-latest)"
    )
    args = parser.parse_args()
    
    run_triage_flow(args.error, args.model)

if __name__ == "__main__":
    main()
