# 🔪 Git Surgeon

> _Because some git operations require surgical precision_

[![Build Status](https://img.shields.io/github/actions/workflow/status/hyperb1iss/git-surgeon/cicd.yml?branch=main&logo=github&logoColor=white)](https://github.com/hyperb1iss/git-surgeon/actions/workflows/cicd.yml)
[![PyPI version](https://img.shields.io/pypi/v/git-surgeon.svg?logo=python&logoColor=white)](https://pypi.org/project/git-surgeon/)
[![Python Versions](https://img.shields.io/pypi/pyversions/git-surgeon?logo=python&logoColor=white)](https://pypi.org/project/git-surgeon/)
[![License](https://img.shields.io/badge/license-GPLv2-blue.svg?logo=gnu)](LICENSE)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg?logo=ruff)](https://github.com/astral-sh/ruff)
[![Type Checking: mypy](https://img.shields.io/badge/type%20checking-mypy-blue?logo=python)](https://github.com/python/mypy)

Git Surgeon is a powerful command-line tool for safely performing complex and potentially destructive operations on git repositories. Think of it as a precise scalpel for your git history! 🔪

## ✨ Features

- 🧹 **File Purging**: Remove sensitive files or patterns from entire git history
- ✂️ **History Truncation**: Safely truncate repository history while preserving state
- 🧰 **Repository Cleanup**: Remove large files and sensitive data
- 👥 **Author Rewriting**: Update author and committer information across history
- 🔒 **Safety First**: Automatic backups and dry-run capabilities
- 🎯 **Precise Control**: Fine-grained control over operations

## 🚀 Installation

Git Surgeon requires Python 3.10 or higher and depends on the git-filter-repo tool for some operations. You can install it using either pip or Poetry.

### Using pip

For most users, installing via pip is the recommended method:

```bash
pip install git-surgeon
```

### Using Poetry (Development)

For developers who want to contribute or modify the code, Poetry provides better dependency management and isolation:

```bash
git clone https://github.com/hyperb1iss/git-surgeon
cd git-surgeon
poetry install
```

## 🎯 Quick Start

Git Surgeon provides several core operations for managing your repository's history. Here are some common use cases:

```bash
# Remove all .env files from history
git-surgeon remove "**/.env" --backup

# Truncate history to keep only recent commits
git-surgeon truncate --keep-recent 100

# Clean up large files
git-surgeon clean --size-threshold 50MB
```

## 🔧 Commands

### File Operations

#### Remove Files

The remove command helps you permanently delete files from your repository's history. This is particularly useful for removing sensitive data that was accidentally committed:

```bash
# Remove specific files from history
git-surgeon remove "path/to/file" --backup

# Remove using glob patterns
git-surgeon remove "**/*.log" --preserve-recent

# Remove from specific branches
git-surgeon remove "secrets.json" --branches main,develop
```

#### History Truncation

The truncate command allows you to manage your repository's history by keeping only the commits you need. This can help reduce repository size and simplify history:

```bash
# Keep only recent history
git-surgeon truncate --keep-recent 50

# Truncate before a date
git-surgeon truncate --before "2023-01-01"

# Truncate after a specific commit
git-surgeon truncate --after abc123
```

#### Repository Cleanup

The cleanup command helps you maintain a healthy repository by removing large files and cleaning up sensitive data:

```bash
# Remove large files
git-surgeon clean --size-threshold 50MB

# Clean sensitive data
git-surgeon clean --sensitive-data

# Cleanup with custom patterns
git-surgeon clean --patterns "**/*.zip,**/*.jar"
```

#### Author Rewriting

The author rewriting feature uses git-filter-repo to safely update author and committer information across your repository's history:

```bash
# Rewrite a single author
git-surgeon rewrite-authors --old "Old Name <old@email.com>" --new "New Name <new@email.com>"

# Rewrite multiple authors using a mapping file
git-surgeon rewrite-authors --mapping-file authors.json

# Update both author and committer information
git-surgeon rewrite-authors --mapping-file authors.json --update-committer

# Example authors.json format:
[
  {
    "old": "Old Name <old@email.com>",
    "new": "New Name <new@email.com>"
  },
  {
    "old": "Another Old <another@old.com>",
    "new": "Another New <another@new.com>"
  }
]
```

## 🛡️ Safety Features

Git Surgeon prioritizes the safety of your repository by implementing several protective measures:

### Automatic Backups

Before performing any destructive operation, Git Surgeon automatically creates a timestamped backup of your repository:

```bash
# Operations create timestamped backups
my_repo_backup_20240125_120130/
```

### Dry Run Mode

All operations support a dry-run mode that shows you exactly what would happen without making any changes:

```bash
# See what would be removed
git-surgeon remove "*.log" --dry-run

# Preview truncation impact
git-surgeon truncate --before 2023-01-01 --dry-run
```

### State Validation

Before performing any operation, Git Surgeon performs comprehensive safety checks:

- Verifies repository state
- Checks for uncommitted changes
- Validates branch states
- Ensures backup creation
- Validates the integrity of the git repository
- Detects detached HEAD state
- Checks for untracked files

## 🎯 Use Cases

### Removing Sensitive Data

When sensitive data like API keys or credentials accidentally make it into your repository, Git Surgeon can help remove them completely:

```bash
# Remove all .env files
git-surgeon remove "**/.env"

# Clean up API keys and tokens
git-surgeon clean --sensitive-data
```

### Repository Maintenance

Keep your repository clean and efficient by removing unnecessary files and optimizing history:

```bash
# Remove old logs and temp files
git-surgeon remove "**/*.log,**/*.tmp"

# Clean up large build artifacts
git-surgeon clean --size-threshold 100MB
```

### History Management

Manage your repository's history to keep it focused and relevant:

```bash
# Keep only recent history
git-surgeon truncate --keep-recent 100

# Remove history before specific date
git-surgeon truncate --before "2023-01-01"
```

## 🔧 Configuration

Git Surgeon can be configured through command-line options or configuration files:

### Command Line Options

```bash
# General options
--backup           Create backup before operation
--dry-run         Show what would be done
--force           Skip confirmation prompts

# Pattern options
--preserve-recent  Keep files in most recent commit
--branches        Specify branches to process
```

## 🤝 Contributing

Yes please! Contributions are welcome:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Setup

The project uses Poetry for dependency management and includes several development tools:

```bash
# Clone the repository
git clone https://github.com/hyperb1iss/git-surgeon
cd git-surgeon

# Install dependencies
poetry install

# Run tests
poetry run pytest

# Run type checking
poetry run mypy git_surgeon

# Run linting
poetry run ruff check git_surgeon
```

## 📄 License

This project is licensed under the GNU General Public License 2.0 - see the [LICENSE](LICENSE) file for details.

---

<div align="center">

Created by [Stefanie Jane 🌠](https://github.com/hyperb1iss)

If you find ChromaCat useful, [buy me a Monster Ultra Violet](https://ko-fi.com/hyperb1iss)! ⚡️

</div>
