import subprocess
import sys

def call_agent(prompt):
    """Call the agent with the given prompt."""
    print("\n" + "="*80)
    print("AGENT PROMPT:")
    print("="*80)
    print(prompt)
    print("="*80 + "\n")
    
    result = subprocess.run(["opencode", "run", prompt])
    
    if result.returncode != 0:
        print(f"Error calling agent: {result.stderr}", file=sys.stderr)
        return False
    
    return True
