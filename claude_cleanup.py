#!/usr/bin/env python3
"""
Claude Orchestrator Cleanup Tool - Remove worktrees and branches
"""
import subprocess
import shutil
from pathlib import Path
import click
import re

def get_worktrees(repo_path):
    """Get list of all worktrees for the repository"""
    result = subprocess.run(
        ["git", "worktree", "list"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    
    worktrees = []
    for line in result.stdout.strip().split('\n'):
        if line:
            # Parse: /path/to/worktree  hash [branch]
            parts = line.split()
            if len(parts) >= 3:
                path = parts[0]
                branch = parts[2].strip('[]') if '[' in parts[2] else parts[2]
                worktrees.append({'path': path, 'branch': branch})
    
    return worktrees

def get_claude_branches(repo_path):
    """Get list of all claude/* branches"""
    result = subprocess.run(
        ["git", "branch", "-a"],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    
    branches = []
    for line in result.stdout.strip().split('\n'):
        line = line.strip()
        if 'claude/' in line:
            # Remove '* ' or '  ' prefix and 'remotes/origin/' prefix
            branch = line.lstrip('* ').replace('remotes/origin/', '')
            branches.append(branch)
    
    return list(set(branches))  # Remove duplicates

def cleanup_worktree(repo_path, worktree_path, branch_name):
    """Remove a worktree and its associated branch"""
    print(f"  🗑️  Removing worktree: {worktree_path}")
    
    # Remove worktree
    result = subprocess.run(
        ["git", "worktree", "remove", "--force", worktree_path],
        cwd=repo_path,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0 and Path(worktree_path).exists():
        # If git command failed but directory exists, try manual removal
        print(f"     ⚠️  Git worktree remove failed, trying manual removal")
        shutil.rmtree(worktree_path, ignore_errors=True)
        # Prune worktree list
        subprocess.run(["git", "worktree", "prune"], cwd=repo_path, capture_output=True)
    
    # Delete branch
    if branch_name and branch_name != 'master' and branch_name != 'main':
        print(f"  🌿 Deleting branch: {branch_name}")
        subprocess.run(
            ["git", "branch", "-D", branch_name],
            cwd=repo_path,
            capture_output=True
        )

@click.command()
@click.option('--repo', '-r', required=True, help='Repository name')
@click.option('--all', is_flag=True, help='Remove ALL claude worktrees and branches')
@click.option('--pattern', '-p', help='Remove worktrees matching pattern (e.g., "20250929_1127")')
@click.option('--interactive', '-i', is_flag=True, help='Interactive mode - choose what to delete')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted without actually deleting')
def main(repo, all, pattern, interactive, dry_run):
    """Clean up Claude orchestrator worktrees and branches"""
    
    parent_dir = Path.cwd()
    main_repo = parent_dir / repo
    
    if not main_repo.exists():
        print(f"❌ Repository {repo} not found")
        return 1
    
    print(f"🧹 Claude Cleanup Tool")
    print(f"📦 Repository: {main_repo}")
    
    if dry_run:
        print("⚠️  DRY RUN MODE - Nothing will be deleted")
    
    # Get all worktrees
    worktrees = get_worktrees(main_repo)
    
    # Filter for claude-related worktrees
    claude_worktrees = []
    for wt in worktrees:
        # Check if it's a claude worktree (path contains repo name and timestamp pattern)
        worktree_path = Path(wt['path'])
        if repo in worktree_path.name and 'claude/' in wt['branch']:
            # Parse the worktree name for timestamp
            match = re.search(r'(\d{8}_\d{6})', worktree_path.name)
            if match:
                wt['timestamp'] = match.group(1)
                claude_worktrees.append(wt)
    
    if not claude_worktrees:
        print("✅ No Claude worktrees found to clean up")
        return 0
    
    print(f"\n📋 Found {len(claude_worktrees)} Claude worktree(s):")
    for wt in claude_worktrees:
        print(f"   • {Path(wt['path']).name} [{wt['branch']}]")
    
    # Filter by pattern if provided
    if pattern:
        original_count = len(claude_worktrees)
        claude_worktrees = [wt for wt in claude_worktrees if pattern in wt['path']]
        print(f"\n🔍 Filtered to {len(claude_worktrees)} worktree(s) matching '{pattern}'")
    
    # Interactive mode
    if interactive and not all:
        to_delete = []
        print("\n🤔 Select worktrees to delete:")
        for i, wt in enumerate(claude_worktrees, 1):
            response = click.prompt(
                f"   Delete {Path(wt['path']).name}? [y/N]",
                type=str,
                default='n'
            )
            if response.lower() == 'y':
                to_delete.append(wt)
        claude_worktrees = to_delete
    
    # Confirm deletion
    if claude_worktrees and not all and not interactive:
        print("\n⚠️  Use --all to delete all, --pattern to filter, or --interactive to choose")
        return 0
    
    if not claude_worktrees:
        print("\n✅ Nothing to delete")
        return 0
    
    print(f"\n🚮 Will delete {len(claude_worktrees)} worktree(s) and their branches")
    
    if not dry_run and not click.confirm("Continue?", default=True):
        print("❌ Cancelled")
        return 0
    
    # Perform cleanup
    print("\n🧹 Cleaning up...")
    for wt in claude_worktrees:
        if dry_run:
            print(f"  [DRY RUN] Would remove: {wt['path']} and branch {wt['branch']}")
        else:
            cleanup_worktree(main_repo, wt['path'], wt['branch'])
    
    # Clean up orphaned branches
    if not dry_run:
        print("\n🌿 Checking for orphaned Claude branches...")
        all_branches = get_claude_branches(main_repo)
        active_branches = [wt['branch'] for wt in get_worktrees(main_repo)]
        orphaned = [b for b in all_branches if b not in active_branches and 'claude/' in b]
        
        if orphaned:
            print(f"   Found {len(orphaned)} orphaned branch(es)")
            for branch in orphaned:
                print(f"   🗑️  Deleting orphaned branch: {branch}")
                subprocess.run(
                    ["git", "branch", "-D", branch],
                    cwd=main_repo,
                    capture_output=True
                )
    
    # Prune worktree list
    if not dry_run:
        print("\n🧹 Pruning worktree list...")
        subprocess.run(["git", "worktree", "prune"], cwd=main_repo, capture_output=True)
    
    print("\n✅ Cleanup complete!")
    
    # Show remaining
    remaining = get_worktrees(main_repo)
    claude_remaining = [wt for wt in remaining if 'claude/' in wt['branch']]
    if claude_remaining:
        print(f"\n📊 Remaining Claude worktrees: {len(claude_remaining)}")

if __name__ == "__main__":
    main()