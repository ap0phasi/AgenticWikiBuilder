# New plan:
#
# Create a session for each bit of raw data, which includes a raw, processed, and docs 
import uuid
import os
from pathlib import Path
import subprocess
import shutil

def initial_doer_prompt(session_name, focus_prompt):
    prompt = f"""
    You are an agent responsible for extracting information from some provided `raw` data and updating a wiki based on this information.

    Please find the raw data in `sessions/{session_name}/raw`. You are encouraged to create working files in `sessions/{session_name}/processed`. Once you complete your wiki updates, create some notes about what you did in `sessions/{session_name}/docs`.

    You are encouraged to write Pythons scripts to help with your extraction of information and wiki population in `helpers`. Use `uv` for all Python package management and script execution. Before writing a script, scan this directory to see if another agent has already written a script that can be modified.

    Rules for updating the wiki:
    - Your goal is to help maintain an accurate, up-to-date wiki. Only populate the wiki based on information you read in `sessions/{session_name}/raw`.
    - Use links in the [Some Name](./another_file.md) format.
    - Do not create subfolders, everthing must be a markdown in `/wiki`.
    - Keep markdown file names readable and compact enough to be intuitive to navigate.
    - Do not reference the session_name id in your wiki. Your job is to write a clean article
    - Do not cite your sources, another tool will be responsible for that 

    Additionally, you have been requested to focus on the following when updating your wiki:
    `{focus_prompt}`
    """

    return prompt

def call_agent(prompt):
    print(prompt)
    cmd = ["opencode", "run" , prompt]
    subprocess.run(cmd)

if __name__ == "__main__":
    os.makedirs("wiki", exist_ok = True)
    os.makedirs("helpers", exist_ok = True)
    os.makedirs("sessions", exist_ok = True)

    session_name = str(uuid.uuid4())

    print(session_name)
    os.makedirs(name = Path("sessions", session_name), exist_ok = False)
    os.makedirs(name = Path("sessions", session_name, "raw"), exist_ok = False)
    os.makedirs(name = Path("sessions", session_name, "processed"), exist_ok = False)
    os.makedirs(name = Path("sessions", session_name, "docs"), exist_ok = False)
    # with open(Path("sessions", session_name, "raw","test.md"), 'w') as f:
    #     f.write("# Test")
    shutil.copyfile("/mnt/c/Users/johnm/Downloads/technical-specification-civil.pdf", Path("sessions",session_name,"raw", "technical-specification-civil.pdf"))
    

    call_agent(initial_doer_prompt(session_name, "Information about electrofusion joint testing"))


    
