from src.commit_processor import process_commit
from src.wiki_agent import run_agents

if __name__ == "__main__":
    process_commit()

    run_agents()
