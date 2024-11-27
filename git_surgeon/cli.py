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
    help="🧨 Safely delete things permanently from git repositories",
    add_completion=False,
)
console = Console()
settings = Settings()


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
def remove(
    pattern: str = typer.Argument(..., help="File pattern to remove (e.g., '**/.env')"),
    *,
    repo_path: Optional[Path] = None,
    dry_run: bool = False,
    backup: bool = True,
    branches: Optional[list[str]] = None,
    preserve_recent: bool = False,
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
def truncate(
    *,
    before: Optional[str] = None,
    after: Optional[str] = None,
    keep_recent: Optional[int] = None,
    squash: bool = False,
    repo_path: Optional[Path] = None,
    dry_run: bool = False,
    backup: bool = True,
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


@app.command()
def clean(
    *,
    size_threshold: Optional[str] = None,
    patterns: Optional[list[str]] = None,
    sensitive_data: bool = False,
    repo_path: Optional[Path] = None,
    dry_run: bool = False,
    backup: bool = True,
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
def rewrite_authors(
    *,
    mapping_file: Optional[Path] = None,
    old_author: Optional[str] = None,
    new_author: Optional[str] = None,
    update_committer: bool = False,
    repo_path: Optional[Path] = None,
    dry_run: bool = False,
    backup: bool = True,
) -> None:
    """Rewrite author information across repository history."""
    mapping_file = typer.Option(
        mapping_file, "--map", "-m", help="JSON file containing author mappings"
    )
    old_author = typer.Option(
        old_author, "--old", help="Original author (format: 'Name <email>')"
    )
    new_author = typer.Option(
        new_author, "--new", help="New author (format: 'Name <email>')"
    )
    update_committer = typer.Option(
        update_committer, "--update-committer", help="Also update committer information"
    )

    if repo_path is None:
        repo_path = Path.cwd()

    repo = validate_repo(repo_path)
    rewriter = AuthorRewriter(repo)

    # Determine the source of mappings
    if mapping_file:
        if old_author or new_author:
            console.print(
                "[red]Cannot combine mapping file with individual author options[/red]"
            )
            raise typer.Exit(1)
        author_mappings = AuthorRewriter.load_mappings(mapping_file)
    else:
        if not (old_author and new_author):
            console.print(
                "[red]Must provide both --old and --new authors or a mapping file[/red]"
            )
            raise typer.Exit(1)
        author_mappings = [AuthorMapping(old=old_author, new=new_author)]

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


if __name__ == "__main__":
    app()
