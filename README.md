# Agentic Wiki Builder

A Python-based tool that processes git commits to markdown files and uses AI agents to automatically generate and maintain a wiki.

I won't try to do a glossy LLM pitch. I fully vibed this with Sonnet because I was frustrated with existing knowledge management and RAG tools. We all know pure vector embed RAG isn't sufficient, so now everyone is excited about Knowledge Graphs. But having used a lot of the established knowledge graph tools on the market, I think the triples structure is contrived. Sure it is cute when Alice works for Company A and Bob works for Company B, but when it comes to nuanced, conditional, temporal relationships the whole approach falls apart a bit in my opinion. Isn't the whole interest in LLMs for being able to handle nuanced, conditional context? So anyway I felt like it would be nice to instead have some AI agents build and maintain a personal wiki based on the data provided. Web crawlers and junk are already optimized for prowling through Wiki articles so I figured it wasn't a bad idea to just use that as a knowledge base.

The main thing I couldn't decide on is how to handle citations back to the original data source. The obvious answer is doing anchor-style cites but those felt too brittle. So instead, the idea is that each time new data comes into `/raw`, we split the new data into broad hunks, and then for each hunk we task an agent with updating the wiki on a dedicated `git` branch tied to that hunk, and a reviewer with confirming the updates are valid. Once the reviewer is satisfied, the branch is merged into main. This way through `git blame` we can track what each piece of raw data motivated the updates to the wiki. I feel like this makes sense compared to relying only on citations.   

## Workflow

### Setup

This is just a thin Python wrapper on [OpenCode](https://github.com/anomalyco/opencode). Make sure it is working on your terminal with whatever model you want.

### Step 1: Create/Update Source Files

Add or modify markdown files in the `/raw` directory, then commit:

```bash
git add raw/
git commit -m "Updated documentation files"
```

### Step 2: Extract Changes

Run the commit processor to create info files:

```bash
python3 commit_processor.py
```

This creates JSON files in `/info` directory with the file content and metadata.

### Step 3: Generate Wiki Content

Run the wiki agent to process info files and update the wiki:

```bash
python3 wiki_agent.py
```

For each info file, the agent will:
1. Create a branch named `wiki-update-{id}`
2. Call OpenCode to generate/update wiki pages in `/wiki` directory
3. Commit the changes on the branch
4. **Review-Fix Loop (up to 5 iterations):**
   - Call OpenCode reviewer agent to review the changes
   - If ACCEPTED: merge to main, delete branch, move to `/processed`
   - If REJECTED: call OpenCode to fix the issues based on feedback, then review again
5. After max iterations or acceptance: always merge and delete the branch
6. Move info file to `/processed`

This ensures you're **NEVER** left with extra branches - only `main` exists after processing.

## Directory Structure

- `/raw` - Source markdown files
- `/info` - JSON files containing commit metadata and file content (pending processing)
- `/processed` - All processed info files (accepted or force-merged after max iterations)
- `/wiki` - Generated wiki markdown files

## JSON Format

Each JSON file in `/info` contains:
- `id` - Unique identifier
- `commit_id` - Git commit hash
- `filename` - Path to the changed file
- `start_line` - Starting line number
- `end_line` - Ending line number
- `content` - Full text content of the file

## Requirements

- Python 3.7+
- Git
