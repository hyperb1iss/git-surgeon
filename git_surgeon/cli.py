"""Command-line interface for git-surgeon operations."""

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.traceback import install

from git_surgeon.config import Settings
from git_surgeon.core import GitRepo
from git_surgeon.operations import FilePurger, HistoryTruncator, RepoCleanup
from git_surgeon.operations.author_rewriter import AuthorMapping, AuthorRewriter

# Install rich traceback handler
install(show_locals=True)

app = typer.Typer(
    help="🧨 A powerful Git history surgery tool for cleaning, purging, truncating, "
    + "and rewriting repository history",
    add_completion=False,
)
console = Console()
settings = Settings()

# Common CLI options
REPO_PATH_OPTION = typer.Option(
    None, help="Path to git repository (defaults to current directory)"
)
DRY_RUN_OPTION = typer.Option(
    False, help="Show what would be done without making changes"
)
BACKUP_OPTION = typer.Option(True, help="Create a backup before making changes")

# Clean command options
SIZE_THRESHOLD_OPTION = typer.Option(
    None, help="Remove files larger than this size (e.g., '10MB', '1GB')"
)
PATTERNS_OPTION = typer.Option(
    None,
    help="File patterns to match when cleaning large files (e.g., '*.zip', '*.jar')",
)
SENSITIVE_DATA_OPTION = typer.Option(
    False,
    help="Scan and remove common sensitive data patterns (passwords, keys, etc.)",
)

# Remove command options
PATTERN_ARGUMENT = typer.Argument(
    ..., help="File pattern to remove (e.g., '**/.env', '*.log')"
)
BRANCHES_OPTION = typer.Option(
    None, help="Specific branches to process (defaults to all branches)"
)
PRESERVE_RECENT_OPTION = typer.Option(
    False,
    help="Keep files in the most recent commit even if they match the pattern",
)

# Rewrite authors options
OLD_AUTHOR_OPTION = typer.Option(
    None, "--old", help="Original author to replace (format: 'Name <email>')"
)
NEW_AUTHOR_OPTION = typer.Option(
    None, "--new", help="New author information (format: 'Name <email>')"
)
UPDATE_COMMITTER_OPTION = typer.Option(
    False, help="Also update committer information, not just author"
)

# Truncate options
BEFORE_OPTION = typer.Option(
    None,
    help="Remove history before this date/ref (e.g., '2023-01-01' or 'abc123')",
)
AFTER_OPTION = typer.Option(
    None, help="Remove history after this date/ref (e.g., '2023-12-31' or 'def456')"
)
KEEP_RECENT_OPTION = typer.Option(None, help="Keep only the N most recent commits")
SQUASH_OPTION = typer.Option(
    False, help="Combine all remaining commits into a single commit"
)

# Module-level options
MAP_OPTION = typer.Option(
    None, "--map", "-m", help="JSON file containing author mappings"
)


def validate_repo(repo_path: Path) -> GitRepo:
    """Validate and return a GitRepo instance."""
    try:
        repo = GitRepo(repo_path)
        repo.validate_state()
        return repo
    except Exception as e:
        console.print(f"[red]Error:[/red] {e!s}")
        raise typer.Exit(1) from e


@app.command()
def clean(
    *,
    size_threshold: Optional[str] = SIZE_THRESHOLD_OPTION,
    patterns: Optional[list[str]] = PATTERNS_OPTION,
    sensitive_data: bool = SENSITIVE_DATA_OPTION,
    repo_path: Optional[Path] = REPO_PATH_OPTION,
    dry_run: bool = DRY_RUN_OPTION,
    backup: bool = BACKUP_OPTION,
) -> None:
    """Clean up repository by removing large files or sensitive data."""
    if repo_path is None:
        repo_path = Path.cwd()

    repo = validate_repo(repo_path)
    cleanup = RepoCleanup(repo)

    with console.status("[bold green]Analyzing repository...") as status:
        if dry_run:
            console.print("[yellow]Dry run complete[/yellow]")
            raise typer.Exit(0)

        if backup:
            status.update("[bold blue]Creating backup...")
            repo.create_backup()

        if size_threshold:
            status.update(f"[bold red]Removing files larger than {size_threshold}...")
            cleanup.clean_large_files(size_threshold, patterns=patterns)

        if sensitive_data:
            status.update("[bold red]Removing sensitive data...")
            cleanup.clean_sensitive_data(settings.sensitive_patterns)

    console.print("[bold green]Operation completed successfully! 🎉")


@app.command()
def remove(
    pattern: str = PATTERN_ARGUMENT,
    *,
    repo_path: Optional[Path] = REPO_PATH_OPTION,
    dry_run: bool = DRY_RUN_OPTION,
    backup: bool = BACKUP_OPTION,
    branches: Optional[list[str]] = BRANCHES_OPTION,
    preserve_recent: bool = PRESERVE_RECENT_OPTION,
) -> None:
    """Remove all traces of files matching pattern from repository history."""
    if repo_path is None:
        repo_path = Path.cwd()

    repo = validate_repo(repo_path)

    with console.status("[bold green]Analyzing repository...") as status:
        purger = FilePurger(repo, pattern)
        matches = purger.find_matches()

        if not matches:
            console.print("[yellow]No files found matching pattern")
            raise typer.Exit(0)

        # Show summary panel
        console.print(
            Panel(
                f"Found [bold]{len(matches)}[/bold] files matching pattern\n"
                f"Total size: [bold]{purger.calculate_size_impact():,}[/bold] bytes\n"
                f"Affected commits: [bold]{len(purger.affected_commits)}[/bold]",
                title="Analysis Results",
                expand=False,
            )
        )

        if dry_run:
            console.print("[yellow]Dry run complete[/yellow]")
            raise typer.Exit(0)

        if not typer.confirm("Do you want to proceed?"):
            raise typer.Exit(0)

        if backup:
            status.update("[bold blue]Creating backup...")
            repo.create_backup()

        status.update("[bold red]Purging files...")
        purger.execute(branches=branches, preserve_recent=preserve_recent)

    console.print("[bold green]Operation completed successfully! 🎉")


@app.command()
def rewrite_authors(
    *,
    mapping: Optional[Path] = MAP_OPTION,
    old: Optional[str] = OLD_AUTHOR_OPTION,
    new: Optional[str] = NEW_AUTHOR_OPTION,
    update_committer: bool = UPDATE_COMMITTER_OPTION,
    repo_path: Optional[Path] = REPO_PATH_OPTION,
    dry_run: bool = DRY_RUN_OPTION,
    backup: bool = BACKUP_OPTION,
) -> None:
    """Rewrite author information across repository history."""
    if repo_path is None:
        repo_path = Path.cwd()

    repo = validate_repo(repo_path)
    rewriter = AuthorRewriter(repo)

    # Determine the source of mappings
    if mapping:
        if old or new:
            console.print(
                "[red]Cannot combine mapping file with individual author options[/red]"
            )
            raise typer.Exit(1)
        author_mappings = AuthorRewriter.load_mappings(mapping)
    else:
        if not (old and new):
            console.print(
                "[red]Must provide both --old and --new authors or a mapping file[/red]"
            )
            raise typer.Exit(1)
        author_mappings = [AuthorMapping(old=old, new=new)]

    with console.status("[bold green]Analyzing repository...") as status:
        if dry_run:
            console.print("[yellow]Dry run complete[/yellow]")
            raise typer.Exit(0)

        if backup:
            status.update("[bold blue]Creating backup...")
            repo.create_backup()

        status.update("[bold red]Rewriting author information...")
        rewriter.rewrite_authors(author_mappings, update_committer=update_committer)

    console.print("[bold green]Operation completed successfully! 🎉")


@app.command()
def truncate(
    *,
    before: Optional[str] = BEFORE_OPTION,
    after: Optional[str] = AFTER_OPTION,
    keep_recent: Optional[int] = KEEP_RECENT_OPTION,
    squash: bool = SQUASH_OPTION,
    repo_path: Optional[Path] = REPO_PATH_OPTION,
    dry_run: bool = DRY_RUN_OPTION,
    backup: bool = BACKUP_OPTION,
) -> None:
    """Truncate repository history."""
    if repo_path is None:
        repo_path = Path.cwd()

    repo = validate_repo(repo_path)
    truncator = HistoryTruncator(repo)

    if not any([before, after, keep_recent]):
        console.print(
            "[red]Error:[/red] Must specify one of: --before, --after, or --keep-recent"
        )
        raise typer.Exit(1)

    with console.status("[bold green]Analyzing repository...") as status:
        if dry_run:
            # Show what would be done
            console.print("[yellow]Dry run complete[/yellow]")
            raise typer.Exit(0)

        if backup:
            status.update("[bold blue]Creating backup...")
            repo.create_backup()

        status.update("[bold red]Truncating history...")

        if before:
            truncator.truncate_before(before, squash=squash)
        elif after:
            truncator.truncate_after(after, squash=squash)
        elif keep_recent:
            truncator.keep_recent(keep_recent, squash=squash)

    console.print("[bold green]Operation completed successfully! 🎉")


if __name__ == "__main__":
    app()
