# Git Workflow Master

## Branch Strategy

### Git Flow Model
```
┌─────────────────────────────────────────────────────────────────┐
│                         main (production)                       │
│    ●────────●────────●────────●────────●────────●────────●───────▶│
│              │                │                │                  │
│              │    releases    │                │                  │
│              └───────●───────┘                │                  │
│                     │                         │                  │
│                     ▼                         ▼                  │
│              develop                 hotfixes (if needed)        │
│    ●────────●────────●────────●────────●────────●────────●───────▶│
│              │       │       │       │       │                    │
│              │       │       │       │       │                    │
│              ▼       ▼       ▼       ▼       ▼                    │
│         feature/  feature/  feature/  feature/  feature/         │
│         auth      orders    payments  search    analytics         │
│              │       │       │       │       │                    │
│              └───────┴───────┴───────┴───────┴────────────────────▶│
```

### Branch Naming Conventions
```bash
# Feature branches
feature/user-authentication
feature/order-history-page
feature/add-dark-mode

# Bugfix branches
bugfix/fix-login-redirect
bugfix/order-total-calculation
bugfix/memory-leak-api

# Hotfix branches
hotfix/critical-security-patch
hotfix/production-data-fix

# Release branches
release/v1.2.0
release/v2.0.0-beta

# Chore branches
chore/update-dependencies
chore/refactor-database-layer
chore/add-type-hints
```

## Essential Git Commands

### Undo Operations
```bash
# Undo last commit (keep changes staged)
git reset --soft HEAD~1

# Undo last commit (keep changes unstaged)
git reset HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1

# Revert a specific commit
git revert <commit-hash>

# Undo staged file
git restore --staged file.txt

# Undo changes to file
git restore file.txt

# Restore file from specific commit
git restore --source=HEAD~2 file.txt
```

### Interactive Rebase
```bash
# Rebase last 5 commits interactively
git rebase -i HEAD~5

# Commands in rebase editor:
# pick = use commit
# reword = change commit message
# edit = pause for amending
# squash = combine with previous
# fixup = combine, discard message
# drop = remove commit

# Example .gitconfig aliases
[alias]
    interactive-rebase = rebase -i HEAD~5
    squash-head = reset --soft HEAD~1
    amend = commit --amend --no-edit
```

### History Rewriting
```bash
# Combine last 3 commits into one
git reset --soft HEAD~3
git commit -m "Combined: Implement user auth and order processing"

# Split a commit
git rebase -i HEAD~1  # mark as 'edit'
git reset HEAD~1
git add file1.txt
git commit -m "Part 1: Add file1"
git add file2.txt
git commit -m "Part 2: Add file2"
git rebase --continue

# Reorder commits
git rebase -i HEAD~5  # reorder lines in editor

# Edit commit message
git commit --amend -m "New commit message"

# Add forgotten file to last commit
git add forgotten.txt
git commit --amend --no-edit
```

## Working with Remote

### Synchronization
```bash
# Fetch all remotes
git fetch --all

# Fetch and prune deleted branches
git fetch --prune

# Pull with rebase (cleaner history)
git pull --rebase origin main

# Force push (use carefully!)
git push --force-with-lease origin feature-branch

# Push new branch
git push -u origin feature-branch

# Delete remote branch
git push origin --delete feature-branch
```

### Tags and Releases
```bash
# Create annotated tag
git tag -a v1.2.0 -m "Version 1.2.0 - Add user profiles"

# Tag specific commit
git tag -a v1.2.0 <commit-hash> -m "Version 1.2.0"

# Push tags
git push origin v1.2.0
git push origin --tags

# List tags
git tag -l "v1.*"

# Delete tag
git tag -d v1.2.0
git push origin --delete v1.2.0
```

## Advanced Git Operations

### Cherry-Picking
```bash
# Cherry-pick single commit
git cherry-pick <commit-hash>

# Cherry-pick without committing
git cherry-pick -n <commit-hash>

# Cherry-pick range (not inclusive of first)
git cherry-pick <start-hash>..<end-hash>

# Continue after resolving conflicts
git cherry-pick --continue

# Abort cherry-pick
git cherry-pick --abort
```

### Stashing
```bash
# Save work in progress
git stash save "WIP: user profile feature"

# Stash including untracked files
git stash -u

# Stash with message
git stash push -m "Partial implementation of auth"

# List stashes
git stash list
# Output: stash@{0}: WIP: user profile feature
#         stash@{1}: Partial implementation of auth

# Apply stash (keep in stash list)
git stash apply stash@{0}

# Apply and remove from list
git stash pop

# Drop stash
git stash drop stash@{0}

# Stash specific file only
git stash push -m "partial" path/to/file.txt

# Create branch from stash
git stash branch new-branch-name stash@{0}
```

### Git Bisect (Bug Finding)
```bash
# Start bisect
git bisect start

# Mark current commit as bad
git bisect bad

# Mark known good commit
git bisect good v1.0.0

# After testing, mark commit as good/bad
git bisect good  # or git bisect bad

# Git will show next candidate
# Continue until bug is found

# End bisect
git bisect reset
```

## Git Hooks

### Pre-commit Hook Example
```bash
#!/bin/bash
# .git/hooks/pre-commit

# Run tests that are affected by changed files
echo "Running affected tests..."

# Get list of changed Python files
CHANGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$')

if [ -n "$CHANGED_FILES" ]; then
    echo "Running pytest on: $CHANGED_FILES"
    pytest $CHANGED_FILES || {
        echo "Tests failed. Commit aborted."
        exit 1
    }
fi

# Run linter
ruff check $CHANGED_FILES || {
    echo "Linting failed. Commit aborted."
    exit 1
}

echo "Pre-commit checks passed!"
exit 0
```

### Commit Message Validation
```bash
#!/bin/bash
# .git/hooks/commit-msg

COMMIT_MSG=$(cat "$1")
BRANCH_NAME=$(git symbolic-ref --short HEAD)

# Pattern for conventional commits
PATTERN="^(feat|fix|docs|style|refactor|test|chore)(\(.+\))?: .{1,50}"

if ! [[ "$COMMIT_MSG" =~ $PATTERN ]]; then
    echo "Commit message format invalid."
    echo "Expected: type(scope): description"
    echo "Example: feat(auth): add OAuth2 support"
    exit 1
fi

exit 0
```

## Aliases and Shortcuts

```bash
# .gitconfig
[alias]
    # Status
    s = status -sb
    st = status
    
    # Branching
    b = branch -a
    co = checkout
    cob = checkout -b
    
    # Committing
    c = commit
    ca = commit -a
    amend = commit --amend --no-edit
    ammend = commit --amend -m
    
    # History
    l = log --oneline --decorate --graph --all
    ll = log --pretty=format:"%h %s %an %ar" --graph
    recent = for-each-ref --count=10 --sort=-committerdate --format="%(_%{refname}) %(_%{objectname:short}) %(_%{contents:short})"
    
    # Staging
    unstage = restore --staged
    staged = diff --cached
    
    # Cleanup
    clean-branches = fetch --prune && branch -vv | grep ': gone]' | awk '{print $1}' | xargs -r git branch -d
    sync = !git fetch --all && git rebase origin/main
    
    # Search
    grep = grep -n
    who = shortlog -n --email --no-merges
    
    # Advanced
    undo = reset --hard HEAD~1
    aliases = config --get-regexp 'alias.*'
```

## Conventional Commits

### Format
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types
| Type | Description |
|------|-------------|
| feat | New feature |
| fix | Bug fix |
| docs | Documentation only |
| style | Formatting, no code change |
| refactor | Code restructuring |
| test | Adding/updating tests |
| chore | Maintenance, dependencies |
| perf | Performance improvement |
| ci | CI/CD changes |
| build | Build system changes |

### Examples
```bash
feat(auth): add OAuth2 login support

fix(api): handle null response in user endpoint

docs(readme): update installation instructions

refactor(order): extract payment processing

test(payment): add integration tests for Stripe
```

## Troubleshooting

### Common Issues

```bash
# Detached HEAD state
git checkout main

# Merged wrong branch
git reset --hard origin/main
git merge --no-ff correct-branch

# Lost commits after hard reset
git reflog
git checkout <commit-hash>

# Conflict markers left in files
git diff --name-only | xargs -I {} sh -c 'sed -i "/^<<<<<<</,/^>>>>>>>/d" {}'

# Permission denied (ssh key issue)
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_rsa
```
