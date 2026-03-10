# Agentic Wiki Builder

A tool that uses AI agents to build and maintain a wiki from raw data sources.

I won't try to do a glossy LLM pitch. I wrote this because I was frustrated with existing knowledge management and RAG tools. We all know pure vector embed RAG isn't sufficient, so now everyone is excited about Knowledge Graphs. But having used a lot of the established knowledge graph tools on the market, I think the triples structure is contrived. Sure it is cute when Alice works for Company A and Bob works for Company B, but when it comes to nuanced, conditional, temporal relationships the whole approach falls apart a bit in my opinion. Isn't the whole interest in LLMs for being able to handle nuanced, conditional context? So anyway I felt like it would be nice to instead have some AI agents build and maintain a personal wiki based on the data provided. Web crawlers and junk are already optimized for prowling through Wiki articles so I figured it wasn't a bad idea to just use that as a knowledge base.

The main thing I couldn't decide on is how to handle citations back to the original data source. The obvious answer is doing anchor-style cites but those felt too brittle. So instead, the idea is that each time new data comes in, we create a session for processing it. Each session gets its own git branch, and an agent updates the wiki on that branch. Once done, we merge back to main. This way through `git blame` we can track what raw data motivated which wiki updates. I feel like this makes sense compared to relying only on citations.

## Workflow

### Setup
This is just a thin Python wrapper on [OpenCode](https://github.com/anomalyco/opencode). Make sure it is working on your terminal with whatever model you want.

### Running a Session

```bash
cd /path/to/your/working/dir && uv run /path/to/this/repo/main.py
```

For each session:
1. **Creates session workspace** with UUID: `sessions/{uuid}/`
   - `raw/` - Your source data gets copied here
   - `processed/` - Agent's working files
   - `docs/` - Agent documents what it did and why
   
2. **Creates git branch** `session-{uuid}` off main

3. **Agent updates wiki** 
   - Reads from `sessions/{uuid}/raw/`
   - Updates markdown files in shared `/wiki` directory
   - Can write reusable Python scripts to `/helpers`
   - Documents changes in `sessions/{uuid}/docs/`

4. **Commits and merges**
   - Commits changes on session branch
   - Merges back to main with session ID in merge commit
   - Deletes session branch

5. **Track provenance**
   - `git blame wiki/some_file.md` shows which session changed it
   - `git log --grep="session-{uuid}"` finds all changes from a session
   - Session workspace preserved in `sessions/{uuid}/` for reference

### Concurrent Sessions

Multiple agents can run in parallel. Each gets its own branch. If they touch different wiki pages, git auto-merges. If they conflict, you'll get clear instructions to resolve manually.

## Directory Structure

- `/wiki` - Shared wiki (version controlled, all agents contribute here)
- `/helpers` - Shared Python scripts (agents can write and reuse)
- `/sessions/{uuid}/` - Per-session workspaces
  - `raw/` - Source data for this session
  - `processed/` - Agent's working files
  - `docs/` - What the agent changed and why

## Agent Instructions

The agent is told to:
- Only add info from the raw data provided in its session
- Use markdown links: `[Some Name](./another_file.md)`
- Keep everything flat in `/wiki` (no subfolders)
- Not reference session IDs in wiki content
- Not cite sources (git handles provenance)
- Write reusable scripts in `/helpers` using `uv`
- Document changes in `sessions/{uuid}/docs/`

## Requirements

- Python 3.7+
- Git
- [OpenCode](https://github.com/anomalyco/opencode)
