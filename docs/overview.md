# Git Surgeon 🔪

Git Surgeon is a powerful command-line tool that makes complex git operations accessible and safe. It provides a suite of precision tools for repository maintenance, history rewriting, and code migration tasks that would otherwise require complex and error-prone git commands.

## Core Philosophy

Git Surgeon follows these key principles:

1. **Safety First**: Every operation creates automatic backups and includes dry-run capabilities
2. **Clear Communication**: Operations clearly explain what they'll do before executing
3. **Precision**: Complex operations are broken down into understandable, precise steps
4. **Reversibility**: When possible, operations can be undone or rolled back
5. **Education**: Help users understand what's happening behind the scenes

## Current Features

### File Operations

#### File Purging
Remove files or patterns from repository history while maintaining integrity.

```bash
git surgeon remove "**/.env" --backup --preserve-recent
git surgeon remove "*.log" --before 2023-01-01
```

**Capabilities:**
- Remove specific files or glob patterns
- Preserve most recent versions optionally
- Target specific branches or all branches
- Handle large binary files efficiently
- Maintain commit history integrity

#### History Truncation
Manage repository history while preserving current state.

```bash
git surgeon truncate --before="1 year ago" --squash
git surgeon truncate --after abc123 --branches=main,develop
```

**Capabilities:**
- Truncate by date, commit, or commit range
- Squash remaining history optionally
- Preserve tags and references
- Handle multiple branches
- Maintain tree integrity

#### Repository Cleanup
Clean and optimize repository content.

```bash
git surgeon clean --large-files=50MB
git surgeon clean --sensitive-data="password|secret|key"
```

**Capabilities:**
- Remove large files over size threshold
- Clean sensitive data matching patterns
- Optimize repository size
- Handle binary files
- Clean up refs and objects

## Planned Features

### Branch Surgery 🔀

#### Splice Operation
Transplant commit ranges between branches with precision.

```bash
git surgeon splice --source feature --range abc123..def456 --into main --at ghi789
```

**Capabilities:**
- Move commit ranges between branches
- Preserve commit metadata
- Handle merge conflicts intelligently
- Maintain related references
- Optional commit message rewriting

#### Excise Operation
Remove specific commits while preserving changes.

```bash
git surgeon excise --range abc123..def456 --preserve-changes
```

**Capabilities:**
- Remove commit ranges
- Preserve cumulative changes
- Handle merge commits
- Maintain branch topology
- Preserve related refs

#### Bifurcate Operation
Split branches at specific points.

```bash
git surgeon bifurcate --at abc123 --into feature-1,feature-2
```

**Capabilities:**
- Split branch history
- Handle divergent changes
- Preserve commit metadata
- Update related references
- Optional branch renaming

### History Reconstruction 🏗️

#### Author Rewriting
Fix author and committer information across history.

```bash
git surgeon rewrite-authors --map authors.json --update-committer
```

**Capabilities:**
- Update author emails and names
- Fix committer information
- Handle co-authors
- Preserve commit dates
- Support bulk updates

#### Timeline Correction
Fix commit timestamps and ordering.

```bash
git surgeon fix-timeline --normalize-dates --sequential
```

**Capabilities:**
- Normalize commit dates
- Fix timezone issues
- Ensure sequential ordering
- Handle merge commits
- Preserve relative timing

#### Message Normalization
Standardize commit messages across history.

```bash
git surgeon normalize-messages --style conventional --fix-typos
```

**Capabilities:**
- Apply consistent formatting
- Fix common typos
- Add missing references
- Update issue links
- Bulk message updates

### Repository Transplants 🌱

#### Code Migration
Move code between repositories while preserving history.

```bash
git surgeon transplant --from repo-a --dir src/legacy --to repo-b --as lib/core
```

**Capabilities:**
- Preserve file history
- Handle subdirectories
- Maintain commit messages
- Update references
- Handle binary files

#### Repository Splitting
Split repositories while preserving history.

```bash
git surgeon split --dirs frontend,backend --into separate-repos/
```

**Capabilities:**
- Split by directory
- Preserve commit history
- Handle shared dependencies
- Update references
- Maintain tags

### Forensics & Analysis 🔍

#### History Analysis
Analyze repository for issues and patterns.

```bash
git surgeon analyze --find-large-files --trace-sensitive-data
```

**Capabilities:**
- Find problematic commits
- Trace data exposure
- Analyze commit patterns
- Find bisection breaks
- Generate reports

#### Performance Optimization
Identify and fix performance issues.

```bash
git surgeon optimize --compact-objects --rewrite-trees
```

**Capabilities:**
- Compact binary objects
- Optimize tree structure
- Clean up refs
- Remove unreachable objects
- Improve clone performance

## Safety Features 🛡️

### Automatic Backups
- Creates repository backup before operations
- Stores backup metadata for recovery
- Provides restore instructions

### Dry Run Mode
- Shows affected commits
- Estimates size impact
- Lists file changes
- Identifies potential issues

### Validation Checks
- Verifies repository state
- Checks for uncommitted changes
- Validates branch states
- Ensures ref integrity

### Recovery Tools
- Restore from backups
- Undo operations when possible
- Fix broken references
- Repair corrupted objects

## Requirements

- Python 3.9+
- Git 2.34.0+
- Storage space for backups
- System tools: `git-filter-repo`

## Installation

```bash
pip install git-surgeon
```

## Contributing

We welcome contributions! Please see our contributing guidelines for more information.

## License

MIT License - See LICENSE file for details.