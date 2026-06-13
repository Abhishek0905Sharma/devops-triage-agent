# DevOps Incident Triage Agent - Demo Video Script

This script provides step-by-step instructions for recording a demo video of the **DevOps Incident Triage Agent** in action.

---

## Part 1: Introduction (Approx. 45 seconds)
**Visual**: Show your IDE with the project root folder `devops_triage_agent` open. Highlight the file structure.

**Narration**:
> "Hello everyone! Today, I am excited to show you a demo of the **DevOps Incident Triage Agent**.
> 
> When production systems throw errors, engineers can spend hours searching codebases and looking at git logs to locate the issue. This AI agent acts as a Senior DevOps Engineer. It reads a Sentry error log, gathers context using developer tools, and makes a smart decision:
> 
> If the bug is simple—like a typo or a missing null check—it auto-fixes it by proposing a git patch. If it's a complex logic bug, it respects its limits and writes a structured triage report instead of changing code. Let's see it in action!"

---

## Part 2: Codebase & Error Logs Tour (Approx. 60 seconds)
**Visual**: 
1. Open and highlight `buggy_app/services/users.py` line 50.
2. Open and highlight `buggy_app/routers/users.py` line 28.
3. Open `errors/error_1.json` to show the simulated Sentry log.

**Narration**:
> "Let's quickly look at our sample codebase. We have a Users API built with FastAPI.
> 
> Under `buggy_app/services/users.py`, we have an intentional typo: returning `updted_user` instead of `upd_user`, which raises a `NameError`.
> 
> Under `buggy_app/routers/users.py`, we have an endpoint accessing `user.profile.bio` without checking if `user.profile` is null, which raises an `AttributeError`.
> 
> We have simulated Sentry logs under our `errors/` directory. Each log includes the error type, message, file path, line number, and stack trace. Let's run our triage agent."

---

## Part 3: Running Triage on Bug 1 - Typo (Approx. 60 seconds)
**Visual**: Open terminal and run the command:
```bash
python triage.py --error errors/error_1.json
```
Let the console print the steps. Open the generated file [`outputs/fix_users_py_8c0a8cf5c6354b9d99723be6ea684d0b.patch`](file:///C:/Users/home/.gemini/antigravity/scratch/devops_triage_agent/outputs/fix_users_py_8c0a8cf5c6354b9d99723be6ea684d0b.patch) in your editor.

**Narration**:
> "First, we run the agent on our `NameError` typo using the command: `python triage.py --error errors/error_1.json`.
> 
> In the console, you can see the agent's step-by-step cognitive reasoning. 
> 
> * Step 1: The agent reads the stack trace, identifies the line of code, and calls the `read_file` tool to inspect `services/users.py`.
> * Step 2: It reviews the code, spots the typo, and checks git logs using `get_recent_commits`.
> * Step 3: It decides this is a simple typo and calls `propose_fix` to save a patch.
> 
> Let's look at the generated patch in the `outputs/` folder. It is a clean, standard git patch that fixes the typo!"

---

## Part 4: Running Triage on Bug 2 - Missing Null Check (Approx. 45 seconds)
**Visual**: In terminal, run:
```bash
python triage.py --error errors/error_2.json
```
Let it run. Open the generated file [`outputs/fix_users_py_f516a22f7b884d0590a3ea1496a7efcc.patch`](file:///C:/Users/home/.gemini/antigravity/scratch/devops_triage_agent/outputs/fix_users_py_f516a22f7b884d0590a3ea1496a7efcc.patch) in your editor.

**Narration**:
> "Now let's run the agent on the `AttributeError` log: `python triage.py --error errors/error_2.json`.
> 
> The agent starts step-by-step reasoning. It reads the router file, then inspects `models.py` to confirm that `profile` is indeed optional.
> 
> Recognizing this is a simple null check omission, it writes a patch file. Opening the output, we see it successfully added a conditional ternary check to safeguard the bio attribute access."

---

## Part 5: Running Triage on Bug 3 - Logic Bug (Approx. 60 seconds)
**Visual**: In terminal, run:
```bash
python triage.py --error errors/error_3.json
```
Let it print the logs. Open the generated markdown report [`outputs/report_bc89fa6e890c4fb98ad16e88fa765fe1.md`](file:///C:/Users/home/.gemini/antigravity/scratch/devops_triage_agent/outputs/report_bc89fa6e890c4fb98ad16e88fa765fe1.md) in your editor. Show the formatted markdown.

**Narration**:
> "Finally, let's run the agent on Bug 3, which is a logic anomaly where the duplicate email check loop compares using `!=` instead of `==`.
> 
> Watch how the agent behaves here:
> 
> It reads `services/users.py` and locates the bug. But instead of generating a code patch, the agent recognizes that logic bugs affect application business rules and should not be auto-fixed without supervision. 
> 
> It calls the `write_report` tool instead of `propose_fix`.
> 
> Opening the report, we see a structured document with the summary, root cause hypothesis, list of affected functions, proposed solution, and confidence level. This is exactly what a senior engineer needs to quickly resolve the issue manually!"

---

## Part 6: Conclusion (Approx. 30 seconds)
**Visual**: Bring up the project's README.md file in the editor.

**Narration**:
> "To summarize, our DevOps Incident Triage Agent successfully automates standard debugging steps, fixes simple bugs safely, and provides detailed documentation for logic bugs. It offers speed where safe, and safety where needed.
> 
> Thanks for watching!"
