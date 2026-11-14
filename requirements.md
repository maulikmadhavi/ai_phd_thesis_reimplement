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
- Agentic handoff: 
    - prepare handoff_request.md fromm claude code to codex agent
    - prepare handoff_response.md from codex agent to claude code
    - The handoff protocol role:
        - Claude code: 
            1. Orchestrator: Responsible for initial task understanding and making execution plan. Check for handoff_response.md from other agents and adjust the execution plan accordingly. [Opus - high] 
            2. Executor: Responsible for implementing the task as per the execution plan. [Sonnet - high]
            3. Reviewer: Check the implemented code for correctness and adherence to the execution plan. commit the results and provide handoff_request.md [Opus - medium] 
        - Codex agent:
            1. Just write single handoff_response.md based on the received handoff_request.md. Codex must not create or modify any other file.
            Commit the handoff_response.md to the repository. [codex - GPT 6 - sol - medium]

    - handoff exectution: Claud code Orchestrator [commit (plan)] -> Claude Code Executor [commit (exec) ] -> Claude Code Reviewer [commit (handoff)] -> Codex [commit (handoff_resp)] -> Claud code Orchestrator [commit (plan)]  .... 
    - Every step in the cycle ends with its own git commit.
    - The user starts every session manually, including the single Codex agent. Claude Code never launches Codex: after the Reviewer's handoff commit it stops and waits for the user.
    - All session should have appropriate title/session_name for better tracking and management.