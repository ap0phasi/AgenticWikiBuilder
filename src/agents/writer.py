def writer_prompt(session_name, focus_prompt=None):
    """Generate the initial prompt for the doer agent."""
    prompt = f"""
You are an agent responsible for extracting information from provided `raw` data and updating a wiki based on this information.

Please find the raw data in `sessions/{session_name}/raw`. You are encouraged to create working files in `sessions/{session_name}/processed`. Once you complete your wiki updates, create notes about what you did in `sessions/{session_name}/docs`.

You are encouraged to write Python scripts to help with your extraction of information and wiki population in `helpers`. Use `uv` for all Python package management and script execution. Before writing a script, scan this directory to see if another agent has already written a script that can be modified.

Rules for updating the wiki:
- Your goal is to help maintain an accurate, up-to-date wiki. Only populate the wiki based on information you read in `sessions/{session_name}/raw`.
- Use links in the [Some Name](./another_file.md) format.
- Err on the side of many small files: if too many topics are covered in one wiki file, break it out and link them.
- Do not create subfolders, everything must be a markdown in `/wiki`.
- Keep markdown file names readable and compact enough to be intuitive to navigate.
- Do not reference the session_name id in your wiki. Your job is to write a clean article.
- Do not cite your sources, another tool will be responsible for that.

When you're done:
1. Document your changes in `sessions/{session_name}/docs/changes.md` (what you changed and why)
2. Create a brief summary in `sessions/{session_name}/docs/summary.txt` (one line description)
"""
    
    if focus_prompt:
        prompt += f"""
Additionally, you have been requested to focus on the following when updating your wiki: `{focus_prompt}`
"""
    
    return prompt
