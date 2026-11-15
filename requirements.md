# Thesis location:
D:\Storage\career_phd_daiict_work\Thesis
- pdf file: Maulik201121003.pdf
- source file: Maulik201121003.tex

# Data location
- Some data D:\Storage\research_data\speech_qbe-std
- TIMIT data: https://huggingface.co/datasets/Siyong/speech_timit

# Old referene work:
matching algorithm: https://github.com/maulikmadhavi/research_qbestd/tree/main/matlab
signal processing and audio features extraction: https://github.com/maulikmadhavi/research_myMATLAB_codes/tree/master/Analysis/Feature_Extraction

# Task requirements
1. Read thesis document thoroughly.
2. Identify the components used [algorithm, data, metrics, experiments]
3. Reproduce the experiments described in the thesis. Implementation was done in the MATLAB earlier. Aim to arrive at similar results as reported in the thesis.
4. There is no priority as such, but we need to have something like this (1) make audio processing base (2) audio feature extraction (3) machine learning (4) machine learning based - posteriogram  (5) matchin algorithms => DTW, subDTW, fastDTW, (6) Indexing. 

# Target repo:
- git@github.com:maulikmadhavi/ai_phd_thesis_reimplement.git

# Development Instruction
## Environment Setup
Use python as a language for implementation.
- Use pixi to setup the virtual environment for Python development.
- Try to be more conservative with package installations and dependencies.

## Base Plan
- As indicatead in [Task requirements](#task-requirements) section.

## Coding style
- Each function and class should reflect their usage and have clear, descriptive names.
- Proper test cases for each function and classes.
- Follow PEP 8 guidelines for code formatting and style.
- Each coude MUST not exceed more than 400 lines. Aim to keep functions and classes concise and modular. 
- Use meaningful variable names and avoid single-letter names except for loop counters.
- No need to exactly follow the naming and structure from the original MATLAB code, you can adapt as per your requirement. First use document thesis and implement, then refer back to the original code and verify. 
- Code should be easy to read. 

##  Folder Structure

- src 
- docs 
    - current reference    
- tests 
- demo [for each stage show can UI using gradio based simple pythonic interface with all possible blocks, input and output and some usage description. ]
README.md [Shorter and concise overview of the project]


## CICD setup 
- Plan very small atomic task implement and commit locally.
- Commit message should be very short one line not exceeding 10 words, no claude code signs. 
- you can create multiple branches if needed for different features or experiments. But make sure maintain the main branch stable and up-to-date.
- Use target repository for all code push. [No need to pull from target repository]
- Push immediately after every git commit, on whichever branch or tag it was made. No need to ask before pushing.
- Agentic handoff (from cycle 6 on, all four roles are Claude Code sessions; Codex is retired):
    - `handoff_request.md`: Reviewer -> Handoff_feedback. `handoff_response.md`: Handoff_feedback -> Orchestrator.
    - Roles (one local Claude Code session each; the session name is its address):
        1. Orchestrator [Opus - high]: understands the task and owns `docs/plan.md`. On a handoff_resp commit, reads `handoff_response.md`, updates the plan, commits `plan: ...`.
        2. Executor [Sonnet - high]: implements the plan task by task, one `exec: ...` commit per task. Stops and reports at every STOP gate in the plan.
        3. Reviewer [Opus - medium]: checks the exec commits for correctness and plan adherence, re-runs the tests, writes `handoff_request.md`, commits `handoff: ...`.
        4. Handoff_feedback [Fable]: independent reviewer that replaces Codex. Writes only `handoff_response.md` from `handoff_request.md`, the repo and the thesis sources, and commits `handoff_resp: ...`. It must not create or modify any other file, and must not take plan decisions in place of the Orchestrator.
    - Cycle: Orchestrator [plan] -> Executor [exec ...] -> Reviewer [handoff] -> Handoff_feedback [handoff_resp] -> Orchestrator [plan] ...
    - Every step ends with its own git commit and an immediate push. Git is the source of truth; messages only point to commits.
    - Notification: after its final commit and push, each role sends the next role a SendMessage with the commit hash and a one-line summary, then stops. No manual relay by the user.
        - Orchestrator -> Executor, Executor -> Reviewer, Reviewer -> Handoff_feedback, Handoff_feedback -> Orchestrator.
        - Fallback: the Orchestrator keeps a background git watcher for `handoff_resp` commits newer than its last plan commit, in case a message is lost.
    - The user still starts every session manually and can stop the loop at any time. The loop pauses for the user (the role reports instead of handing on) when:
        - a STOP gate in the plan fires, tests fail, or a regression check fails;
        - Handoff_feedback marks an item **user decision** (data access, licence, scope, compute cost);
        - a session needs a permission it does not have. A role never asks another session to do something its own permissions blocked.
    - All sessions should have an appropriate title/session_name for better tracking and management.
