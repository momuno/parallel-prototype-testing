# Parallel Prototype Testing

A toolkit for running multiple parallel Claude instances to explore different implementation approaches for the same task. Each instance receives unique instructions and works in isolated git worktrees, allowing for rapid prototyping and comparison of different solutions.

## Overview

This repository contains tools to:
- Spawn multiple Claude instances working on the same task with different approaches
- Automatically generate unique implementation strategies using Claude
- Manage git worktrees and branches for isolated development
- Clean up worktrees and branches when done

## Important Setup Notes

**These scripts should be run on a DIFFERENT repository than the one containing the scripts.** The recommended workflow is:

1. Keep these scripts in this `momuno_parallel-prototype-testing` repository
2. Have your actual project repository as a sibling directory
3. Start a Claude session in the parent directory (one level above both repos)
4. Run the scripts targeting your project repository

This setup allows you to:
- Have a supervisor Claude session that can observe all worktrees
- Keep the orchestration tools separate from your actual projects
- Monitor and coordinate the parallel instances from the parent session

## Tools

### 1. `claude_orchestrator_autostart.py` - Parallel Instance Launcher

Launches multiple Claude instances in separate terminals, each with a unique approach to solving the same task.

#### Usage

```bash
# Launch 3 parallel instances on your PROJECT repo (not this tools repo)
python3 momuno_parallel-prototype-testing/claude_orchestrator_autostart.py --repo YOUR_PROJECT_REPO --parallel 3 --task 'implement a feature'

# Example with a real project
python3 momuno_parallel-prototype-testing/claude_orchestrator_autostart.py --repo my-web-app --parallel 3 --task 'explore a prototype for an onboarding guide'

# Launch 5 instances with prompt for task
python3 momuno_parallel-prototype-testing/claude_orchestrator_autostart.py --repo my-web-app -p 5
```

#### Options
- `--repo, -r` (required): Repository name to work in
- `--parallel, -p`: Number of parallel instances to create
- `--task, -t`: Task description for all variants

#### Features
- **Auto-generated approaches**: Uses Claude to generate N different implementation strategies
- **Isolated worktrees**: Each variant works in its own git worktree and branch
- **Color-coded tabs**: Each terminal tab has a unique color for easy identification
- **Auto-start**: Claude begins working immediately with full task context
- **Session tracking**: Creates session files in `claude_sessions/` for history

#### What it does:
1. Asks Claude to generate N unique approaches to the task
2. Creates N git worktrees (one per approach)
3. Generates a `TASK.md` in each worktree with specific instructions
4. Spawns N terminal windows with Claude auto-started
5. Each Claude instance receives the full task and begins implementation

### 2. `claude_cleanup.py` - Worktree and Branch Cleanup

Manages cleanup of worktrees and branches created by the orchestrator.

#### Usage

```bash
# See what would be cleaned (dry run)
python3 momuno_parallel-prototype-testing/claude_cleanup.py --repo YOUR_PROJECT_REPO --dry-run

# Interactive cleanup - choose what to delete
python3 momuno_parallel-prototype-testing/claude_cleanup.py --repo my-web-app -i

# Delete all Claude worktrees and branches
python3 momuno_parallel-prototype-testing/claude_cleanup.py --repo my-web-app --all

# Delete worktrees from a specific session (pattern matching)
python3 momuno_parallel-prototype-testing/claude_cleanup.py --repo my-web-app --pattern "20250929_1127"
```

#### Options
- `--repo, -r` (required): Repository name to clean
- `--all`: Remove ALL Claude worktrees and branches
- `--pattern, -p`: Remove worktrees matching pattern (e.g., timestamp)
- `--interactive, -i`: Choose what to delete interactively
- `--dry-run`: Preview what would be deleted without deleting

#### Features
- **Safe cleanup**: Properly removes git worktrees and branches
- **Orphan detection**: Finds and removes branches with no worktree
- **Pattern matching**: Clean up specific sessions by timestamp
- **Dry run mode**: Preview changes before execution

## Recommended Workflow Example

1. **Setup your directory structure:**
   ```
   workspace/
   ├── momuno_parallel-prototype-testing/  # This tools repo
   └── my-web-app/                        # Your actual project repo
   ```

2. **Start a supervisor Claude session in the workspace directory:**
   ```bash
   cd workspace
   claude
   ```

3. **From the supervisor session, launch parallel instances:**
   ```bash
   python3 momuno_parallel-prototype-testing/claude_orchestrator_autostart.py --repo my-web-app -p 3 --task "implement a todo app with React"
   ```

4. **Monitor the parallel instances:**
   - Each terminal shows a different variant (V1, V2, V3)
   - Each uses a different approach (Functional, OOP, Event-driven, etc.)
   - The supervisor Claude can observe and analyze all worktrees
   - You can ask the supervisor Claude to compare implementations or gather insights

5. **Review implementations:**
   - Check each worktree directory for the implementations
   - Use the supervisor Claude to analyze differences
   - Compare different approaches

6. **Clean up when done:**
   ```bash
   # Interactive cleanup to keep some variants
   python3 momuno_parallel-prototype-testing/claude_cleanup.py --repo my-web-app -i
   
   # Or remove all
   python3 momuno_parallel-prototype-testing/claude_cleanup.py --repo my-web-app --all
   ```

## Requirements

- Python 3.6+
- Git
- Claude CLI (`claude` command available)
- Click library (`pip install click`)
- Terminal that supports tabs (Windows Terminal, iTerm2, etc.)

## Directory Structure

After running the orchestrator on `my-web-app`:
```
workspace/                                       # Parent directory where you run supervisor Claude
├── momuno_parallel-prototype-testing/          # Tools repository
│   ├── claude_orchestrator_autostart.py
│   ├── claude_cleanup.py
│   └── README.md
├── my-web-app/                                 # Your project repository
│   └── (your project files)
├── my-web-app-{timestamp}-v1/                  # Worktree 1
│   └── TASK.md
├── my-web-app-{timestamp}-v2/                  # Worktree 2
│   └── TASK.md
├── my-web-app-{timestamp}-v3/                  # Worktree 3
│   └── TASK.md
└── claude_sessions/                            # Session history
    └── claude_session_{timestamp}.json
```

## Tips

- Each variant gets a unique colored tab for easy identification
- Session files track what was run and when
- Use pattern matching in cleanup to remove specific sessions
- The dry-run option lets you preview cleanup operations safely
- Worktrees are completely isolated - variants won't interfere with each other

## Future Improvements

### Auto-Setup Integration
**Goal**: Have the supervisor Claude session automatically run the orchestrator script when requested, eliminating manual execution.

This would allow you to simply tell Claude:
- "Start 3 parallel prototypes for implementing feature X"
- Claude would then automatically run the orchestrator script
- All terminals would spawn without manual intervention

This integration would make the workflow even more seamless, allowing the supervisor Claude to act as a true orchestration layer that can launch and manage parallel instances on demand.