# 🧨 Git Surgeon

> _Because some git operations require surgical precision_ 🔪

[![Build Status](https://img.shields.io/github/actions/workflow/status/hyperb1iss/git-surgeon/cicd.yml?branch=main&logo=github&logoColor=white)](https://github.com/hyperb1iss/git-surgeon/actions/workflows/cicd.yml)
[![PyPI version](https://img.shields.io/pypi/v/git-surgeon.svg?logo=python&logoColor=white)](https://pypi.org/project/git-surgeon/)
[![Python Versions](https://img.shields.io/pypi/pyversions/git-surgeon?logo=python&logoColor=white)](https://pypi.org/project/git-surgeon/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg?logo=opensource)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Type Checking: mypy](https://img.shields.io/badge/type%20checking-mypy-blue?logo=python)](https://github.com/python/mypy)

Git Surgeon is a powerful command-line tool for safely performing complex and potentially destructive operations on git repositories. Think of it as a precise scalpel for your git history! 🔪

## ✨ Features

- 🧹 **File Purging**: Remove sensitive files or patterns from entire git history
- ✂️ **History Truncation**: Safely truncate repository history while preserving state
- 🧰 **Repository Cleanup**: Remove large files and sensitive data
- 🔒 **Safety First**: Automatic backups and dry-run capabilities
- 🎯 **Precise Control**: Fine-grained control over operations
- 🚀 **User-Friendly**: Clear progress indicators and error messages
- 💡 **Smart Detection**: Identifies potential issues before they happen

## 🚀 Installation

### Using pip

```bash
pip install git-surgeon
```

### Using Poetry (Development)

```bash
git clone https://github.com/hyperb1iss/git-surgeon
cd git-surgeon
poetry install
```

## 🎯 Quick Start

```bash
# Remove all .env files from history
git-surgeon remove-file "**/.env" --backup

# Truncate history to keep only recent commits
git-surgeon truncate --keep-recent 100

# Clean up large files
git-surgeon clean --size-threshold 50MB
```

## 🔧 Commands

### File Operations

#### Remove Files

```bash
# Remove specific files from history
git-surgeon remove-file "path/to/file" --backup

# Remove using glob patterns
git-surgeon remove-file "**/*.log" --preserve-recent

# Remove from specific branches
git-surgeon remove-file "secrets.json" --branches main,develop
```

#### History Truncation

```bash
# Keep only recent history
git-surgeon truncate --keep-recent 50

# Truncate before a date
git-surgeon truncate --before "2023-01-01"

# Truncate after a specific commit
git-surgeon truncate --after abc123
```

#### Repository Cleanup

```bash
# Remove large files
git-surgeon clean --size-threshold 50MB

# Clean sensitive data
git-surgeon clean --sensitive-data

# Cleanup with custom patterns
git-surgeon clean --patterns "**/*.zip,**/*.jar"
```

## 🛡️ Safety Features

### Automatic Backups

Every destructive operation automatically creates a backup:

```bash
# Operations create timestamped backups
my_repo_backup_20240125_120130/
```

### Dry Run Mode

Preview changes before applying them:

```bash
# See what would be removed
git-surgeon remove-file "*.log" --dry-run

# Preview truncation impact
git-surgeon truncate --before 2023-01-01 --dry-run
```

### State Validation

Git Surgeon performs multiple safety checks:

- Verifies repository state
- Checks for uncommitted changes
- Validates branch states
- Ensures backup creation

## 🎯 Use Cases

### Removing Sensitive Data

```bash
# Remove all .env files
git-surgeon remove-file "**/.env"

# Clean up API keys and tokens
git-surgeon clean --sensitive-data
```

### Repository Maintenance

```bash
# Remove old logs and temp files
git-surgeon remove-file "**/*.log,**/*.tmp"

# Clean up large build artifacts
git-surgeon clean --size-threshold 100MB
```

### History Management

```bash
# Keep only recent history
git-surgeon truncate --keep-recent 100

# Remove history before specific date
git-surgeon truncate --before "6 months ago"
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

### Configuration File

```yaml
# .git-surgeon.yaml
backup:
  enabled: true
  directory: "/path/to/backups"

cleanup:
  size_threshold: 50MB
  sensitive_patterns:
    - "password"
    - "secret"
    - "key"
    - "token"
    - "credential"
```

## 🤝 Contributing

Yes please! Contributions are welcome:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Setup

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
