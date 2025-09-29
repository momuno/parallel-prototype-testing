#!/usr/bin/env python3
"""
Claude Orchestrator with Auto-Start - Uses --command flag to execute on startup
"""
import subprocess
import platform
import os
import sys
from pathlib import Path
from datetime import datetime
import click
import json
import time
import tempfile

class ClaudeOrchestrator:
    def __init__(self, repo_name):
        self.parent_dir = Path.cwd()
        self.main_repo = self.parent_dir / repo_name
        self.repo_name = repo_name
        
        # Detect platform
        self.platform = platform.system()
        print(f"🖥️  Platform detected: {self.platform}")
        
        # Validate setup
        if not self.main_repo.exists():
            raise ValueError(f"Repository {repo_name} not found in {self.parent_dir}")
        if not (self.main_repo / ".git").exists():
            raise ValueError(f"{repo_name} is not a git repository")
        
        print(f"✅ Initialized orchestrator")
        print(f"📂 Parent directory: {self.parent_dir}")
        print(f"📦 Main repository: {self.main_repo}")
    
    def generate_variations_with_claude(self, base_task: str, n: int):
        """Use Claude to generate N different approaches for the task"""
        print(f"\n🤖 Asking Claude to generate {n} unique approaches...")
        
        prompt = f"""Generate {n} distinctly different approaches to implement: {base_task}

For each approach, provide:
1. A short title (e.g., "Functional Approach", "Event-Driven Design")
2. A detailed description of the approach
3. Key implementation details
4. What makes this approach unique

Format each approach as:
APPROACH N:
Title: [title]
Description: [description]
Key Details: [details]
Unique Aspects: [what makes it different]
---"""
        
        try:
            # Try claude-code first, fall back to claude if not found
            claude_cmd = "claude-code" if subprocess.run(["which", "claude-code"], capture_output=True).returncode == 0 else "claude"
            result = subprocess.run(
                [claude_cmd, "--print", prompt],
                capture_output=True,
                text=True,
                timeout=60  # Increased timeout
            )
            
            # Claude may output to stderr, so check both
            output = result.stdout if result.stdout else result.stderr
            
            if output:
                # Debug: show first 100 chars of output
                # print(f"Debug: Got output: {output[:100]}...")
                variations = self.parse_variations(output, n)
                if len(variations) < n:
                    print(f"⚠️  Only got {len(variations)} variations, using fallback for the rest")
                    variations.extend(self.get_fallback_variations(n - len(variations)))
                return variations
            else:
                print(f"⚠️  Claude didn't respond as expected (return code: {result.returncode})")
                if result.stderr:
                    print(f"    Error: {result.stderr[:200]}")
                return self.get_fallback_variations(n)
                
        except subprocess.TimeoutExpired:
            print("⚠️  Claude timed out after 60 seconds, using fallback variations")
            return self.get_fallback_variations(n)
        except FileNotFoundError:
            print("⚠️  Claude command not found, using fallback variations")
            return self.get_fallback_variations(n)
        except Exception as e:
            print(f"⚠️  Unexpected error calling Claude: {e}")
            return self.get_fallback_variations(n)
    
    def parse_variations(self, response: str, n: int):
        """Parse Claude's response into structured variations"""
        variations = []
        sections = response.split("APPROACH")
        
        for section in sections[1:]:
            if len(variations) >= n:
                break
                
            lines = section.strip().split('\n')
            variation = {
                "title": "Approach " + str(len(variations) + 1),
                "description": "",
                "details": "",
                "unique": ""
            }
            
            for line in lines:
                line = line.strip()
                if line.startswith("Title:"):
                    variation["title"] = line.replace("Title:", "").strip()
                elif line.startswith("Description:"):
                    variation["description"] = line.replace("Description:", "").strip()
                elif line.startswith("Key Details:"):
                    variation["details"] = line.replace("Key Details:", "").strip()
                elif line.startswith("Unique Aspects:"):
                    variation["unique"] = line.replace("Unique Aspects:", "").strip()
            
            if not variation["description"]:
                variation["description"] = section.strip()
            
            variations.append(variation)
        
        return variations
    
    def get_fallback_variations(self, n: int):
        """Fallback variations if Claude isn't available"""
        base_approaches = [
            {
                "title": "Functional Programming Approach",
                "description": "Implement using pure functions, immutability, and function composition",
                "details": "No classes, no mutable state, use higher-order functions",
                "unique": "Emphasizes composability and predictability"
            },
            {
                "title": "Object-Oriented Design",
                "description": "Use classes, inheritance, and encapsulation with SOLID principles",
                "details": "Clear class hierarchies, interfaces, and dependency injection",
                "unique": "Focuses on extensibility and maintainability"
            },
            {
                "title": "Event-Driven Architecture",
                "description": "Build with event emitters, listeners, and asynchronous patterns",
                "details": "Loose coupling through events, reactive to state changes",
                "unique": "Highly decoupled and scalable"
            }
        ]
        
        variations = []
        for i in range(n):
            variations.append(base_approaches[i % len(base_approaches)])
        return variations
    
    def create_worktree(self, task_id: str, variant: int) -> Path:
        """Create a single worktree"""
        branch_name = f"claude/{task_id}/variant-{variant}"
        worktree_name = f"{self.repo_name}-{task_id}-v{variant}"
        worktree_path = self.parent_dir / worktree_name
        
        print(f"  📁 Creating worktree: {worktree_name}")
        
        if worktree_path.exists():
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree_path)],
                cwd=self.main_repo,
                capture_output=True
            )
        
        current_branch = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=self.main_repo,
            capture_output=True,
            text=True
        ).stdout.strip() or "master"
        
        result = subprocess.run(
            ["git", "worktree", "add", "-b", branch_name, f"../{worktree_name}", current_branch],
            cwd=self.main_repo,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return worktree_path
        else:
            raise RuntimeError(f"Failed to create worktree: {result.stderr}")
    
    def create_task_file(self, worktree_path: Path, variant: int, base_task: str, variation: dict):
        """Create TASK.md with detailed instructions"""
        
        task_content = f"""# Task for Variant {variant}: {variation['title']}

## Main Objective
{base_task}

## Your Specific Approach: {variation['title']}

### Description
{variation['description']}

### Key Implementation Details
{variation['details']}

### What Makes This Unique
{variation['unique']}

## Instructions
1. Implement the solution using the approach described above
2. Make sure your implementation is distinctly different from other variants
3. Follow the key implementation details closely
4. Create appropriate files and folder structure
5. Include tests if applicable
6. Document your design decisions

## Getting Started
Please begin by implementing "{base_task}" using the {variation['title']} approach described above.

Remember: Your implementation should clearly demonstrate the unique aspects of this approach.
"""
        
        task_file = worktree_path / "TASK.md"
        with open(task_file, 'w') as f:
            f.write(task_content)
        
        return task_file
    
    def create_claude_settings(self, worktree_path: Path, task_summary: str, approach: str):
        """Create .claude/settings.json with custom status line"""
        claude_dir = worktree_path / ".claude"
        claude_dir.mkdir(exist_ok=True)
        
        settings = {
            "statusLine": f"{task_summary}: {approach}"
        }
        
        settings_file = claude_dir / "settings.json"
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        
        return settings_file
    
    def create_startup_query(self, worktree_path: Path, variant: int, variation: dict, base_task: str):
        """Create the startup query by reading TASK.md content"""
        # Read the TASK.md file content
        task_file = worktree_path / "TASK.md"
        with open(task_file, 'r') as f:
            task_content = f.read()
        
        # Create a comprehensive query with the full task content
        query = (
            f"Here is your task:\n\n"
            f"{task_content}\n\n"
            f"---\n\n"
            f"You are Variant {variant}. Please implement this task using the {variation['title']} approach described above. "
            f"Start by creating the necessary project structure and files, then begin implementation according to your specific approach."
        )
        
        return query
    
    def create_claude_session_script(self, worktree_path: Path, variant: int, variation: dict, base_task: str, task_id: str, startup_query: str) -> str:
        """Create script to launch Claude with initial query"""
        
        # Generate a unique session ID for this variant
        session_id = f"{task_id}-variant-{variant}"
        
        # Escape the query for bash - replace single quotes and backslashes
        escaped_query = startup_query.replace("'", "'\\''").replace("\\", "\\\\")
        
        script_content = f'''#!/bin/bash
echo "🤖 Claude Auto-Start - Variant {variant}"
echo "📂 Working in: {worktree_path}"
echo "🎯 Approach: {variation['title']}"
echo "{'=' * 60}"

cd "{worktree_path}"

if ! command -v claude &> /dev/null; then
    echo "❌ claude CLI not found!"
    echo "Please ensure Claude Code is installed and in your PATH"
    read -p "Press Enter to exit..."
    exit 1
fi

echo ""
echo "🚀 AUTO-STARTING with full task content"
echo "📝 Session ID: {session_id}"
echo "⚡ Using --permission-mode default to skip permission prompt"
echo "{'─' * 40}"
echo ""

# Start claude with the initial query and permission mode
# The query contains the full TASK.md content
claude --permission-mode default '{escaped_query}'

echo ""
echo "Session ended. Press Enter to close..."
read
'''
        
        # Create script in temp directory with auto-cleanup
        temp_dir = Path(tempfile.gettempdir())
        script_path = temp_dir / f"claude_auto_v{variant}_{datetime.now().strftime('%H%M%S')}.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        os.chmod(script_path, 0o755)
        return str(script_path)
    
    def spawn_terminal(self, worktree_name: str, command: str, terminal_title: str = None, variant_num: int = None):
        """Spawn a new terminal window"""
        # Use custom title if provided, otherwise use worktree name
        title = terminal_title if terminal_title else worktree_name
        
        # Define colors for different variants (hex colors for Windows Terminal)
        variant_colors = [
            "#0078D4",  # Blue for variant 1
            "#00BCF2",  # Cyan for variant 2  
            "#00B7C3",  # Teal for variant 3
            "#FF8C00",  # Orange for variant 4
            "#E81123",  # Red for variant 5
        ]
        tab_color = variant_colors[(variant_num - 1) % len(variant_colors)] if variant_num else None
        try:
            if self.platform == "Linux":
                terminals = [
                    ["gnome-terminal", "--title", title, "--", "bash", "-c", command],
                    ["konsole", "--title", title, "-e", "bash", "-c", command],
                    ["xfce4-terminal", "--title", title, "-e", f"bash -c '{command}'"],
                    ["xterm", "-title", title, "-e", "bash", "-c", command],
                ]
                
                for term_cmd in terminals:
                    try:
                        subprocess.Popen(
                            term_cmd,
                            stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            start_new_session=True
                        )
                        return True
                    except FileNotFoundError:
                        continue
                
                # Try Windows Terminal (WSL)
                try:
                    # Windows Terminal with specific settings
                    # --suppressApplicationTitle prevents the title from changing
                    # --tabColor can set a specific color for the tab
                    # Note: Tab width cannot be set via CLI, but longer titles will make tabs appear wider
                    wt_cmd = [
                        "wt.exe", 
                        "new-tab",
                        "--title", title,
                        "--suppressApplicationTitle"
                    ]
                    if tab_color:
                        wt_cmd.extend(["--tabColor", tab_color])
                    wt_cmd.extend(["wsl.exe", "-e", "bash", "-c", command])
                    subprocess.Popen(
                        wt_cmd,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    return True
                except:
                    pass
                    
            elif self.platform == "Darwin":
                apple_script = f'''
                tell application "Terminal"
                    activate
                    do script "{command}"
                    set custom title of front window to "{title}"
                end tell
                '''
                subprocess.run(["osascript", "-e", apple_script])
                return True
                    
            elif self.platform == "Windows":
                subprocess.Popen(
                    ["wt", "new-tab", "--title", title, "bash", "-c", command],
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return True
            
        except Exception as e:
            print(f"   ❌ Error spawning terminal: {e}")
            return False
    
    def get_short_task_summary(self, base_task: str):
        """Extract a short summary from the task description"""
        # Take the first few words or key concept
        words = base_task.split()
        if 'implement' in base_task.lower():
            # Remove "implement" and take the key concept
            task_lower = base_task.lower()
            if 'implement a' in task_lower:
                summary = base_task.split('implement a', 1)[-1].strip()
            elif 'implement an' in task_lower:
                summary = base_task.split('implement an', 1)[-1].strip()
            elif 'implement' in task_lower:
                summary = base_task.split('implement', 1)[-1].strip()
            else:
                summary = base_task
        else:
            summary = base_task
        
        # Capitalize first letter of each word and limit length
        summary_words = summary.split()[:3]  # Max 3 words
        return ' '.join(word.capitalize() for word in summary_words)
    
    def spawn_multiple_claude_terminals(self, n: int, base_task: str):
        """Create n worktrees with auto-starting Claude instances"""
        task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        print(f"\n🚀 Setting up {n} parallel Claude instances with AUTO-START")
        print(f"📋 Base Task: {base_task}")
        print(f"⚡ Using --command flag for automatic execution")
        
        # Generate variations
        variations = self.generate_variations_with_claude(base_task, n)
        
        print(f"\n✨ Generated {len(variations)} unique approaches:")
        for i, var in enumerate(variations, 1):
            print(f"   {i}. {var['title']}")
        
        print(f"\n🔨 Creating worktrees with auto-start scripts...")
        
        worktrees = []
        for i in range(1, n + 1):
            variation = variations[i - 1]
            
            # Create worktree
            worktree_path = self.create_worktree(task_id, i)
            worktree_name = f"{self.repo_name}-{task_id}-v{i}"
            
            # Create TASK.md
            self.create_task_file(worktree_path, i, base_task, variation)
            
            # Get task summary and approach for status line and terminal title
            task_summary = self.get_short_task_summary(base_task)
            # Make approach names very short for compact tabs
            approach_short = variation['title'].replace('Programming Approach', '').replace('Programming', '') \
                                               .replace('Architecture', '').replace('Pattern', '') \
                                               .replace('Approach', '').replace('Design', '') \
                                               .replace('-', '').strip()
            # Further abbreviate common words
            approach_short = approach_short.replace('Functional', 'Func') \
                                          .replace('Object-Oriented', 'OOP') \
                                          .replace('Object Oriented', 'OOP') \
                                          .replace('Event-Driven', 'Event') \
                                          .replace('Event Driven', 'Event') \
                                          .replace('Interactive', 'Inter') \
                                          .replace('Contextual', 'Context') \
                                          .replace('Step-by-Step', 'Steps') \
                                          .replace('Wizard', 'Wiz')
            
            # Create Claude settings with custom status line
            self.create_claude_settings(worktree_path, task_summary, approach_short)
            
            # Create the startup query with full task content
            startup_query = self.create_startup_query(worktree_path, i, variation, base_task)
            
            # Create session script with the query
            script_path = self.create_claude_session_script(
                worktree_path, 
                i,
                variation,
                base_task,
                task_id,
                startup_query
            )
            
            # Create compact terminal title
            terminal_title = f"V{i}:{approach_short[:15]}"
            
            # Spawn terminal with custom title and color
            print(f"  🖥️  Spawning terminal {i}: {terminal_title}")
            command = f"bash {script_path}"
            self.spawn_terminal(worktree_name, command, terminal_title, i)
            
            time.sleep(1)
            
            worktrees.append({
                "variant": i,
                "name": worktree_name,
                "path": str(worktree_path),
                "approach": variation,
                "session_id": f"{task_id}-variant-{i}"
            })
        
        # Save session info in dedicated folder
        sessions_dir = self.parent_dir / "claude_sessions"
        sessions_dir.mkdir(exist_ok=True)
        session_file = sessions_dir / f"claude_session_{task_id}.json"
        with open(session_file, 'w') as f:
            json.dump({
                "task_id": task_id,
                "created": datetime.now().isoformat(),
                "base_task": base_task,
                "variations": variations,
                "worktrees": worktrees
            }, f, indent=2)
        
        print(f"\n✅ All {n} terminals spawned with AUTO-START!")
        print(f"📝 Session info saved to: {session_file}")
        print(f"\n🎯 AUTO-START ACTIVE:")
        print(f"   • Full TASK.md content passed as initial query")
        print(f"   • Using --permission-mode default to skip permission prompt")
        print(f"   • Each variant receives complete implementation instructions")
        print(f"   • Work should begin immediately")
        print(f"   • Each session has a unique ID for tracking\n")

@click.command()
@click.option('--repo', '-r', required=True, help='Repository name (required)')
@click.option('--parallel', '-p', type=int, help='Create N parallel Claude instances')
@click.option('--task', '-t', help='Task description for Claude instances')
def main(repo, parallel, task):
    """Claude Orchestrator with Auto-Start - passes full task as initial query"""
    try:
        orch = ClaudeOrchestrator(repo_name=repo)
        
        if parallel:
            if not task:
                task = click.prompt("Enter the task for all variants")
            orch.spawn_multiple_claude_terminals(parallel, task)
        else:
            print("\n📋 Usage:")
            print("  python claude_orchestrator_autostart.py --repo momuno_parallel-prototype-testing --parallel 3 --task 'implement a rate limiter'")
            print("\nRequired arguments:")
            print("  --repo/-r    : The git repository name")
            print("  --parallel/-p: Number of parallel Claude instances")
            print("  --task/-t    : Task description for all variants")
            print("\nThis version uses Claude's query syntax:")
            print("  • Passes full TASK.md content as initial query")
            print("  • Uses --permission-mode default to skip permission prompt")
            print("  • Claude receives complete task and begins implementation")
            print("  • Each variant has a unique session ID")
            print("\n🚀 TRUE AUTO-START - Claude begins work automatically!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

if __name__ == "__main__":
    main()