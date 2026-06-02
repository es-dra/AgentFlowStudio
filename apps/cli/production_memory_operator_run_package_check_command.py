from __future__ import annotations

from pathlib import Path

import typer

from agentflow.memory.production_operator_run_package_check import (
    check_operator_run_package,
    write_operator_run_package_check,
)


def production_memory_loop_check_operator_run_package_command(
    package_path: Path = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to operator_run_package.json.",
    ),
    artifact_root: Path | None = typer.Option(
        None,
        "--artifact-root",
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Optional artifact root. Defaults to the operator loop output root.",
    ),
    output_path: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Optional JSON report path for the operator run package check.",
    ),
) -> None:
    """Check a production-memory operator run package without following refs."""
    try:
        check = check_operator_run_package(package_path, artifact_root=artifact_root)
        if output_path is not None:
            write_operator_run_package_check(check, output_path)
    except ValueError as exc:
        typer.echo(f"Operator run package check failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Operator run package check: {check['check_status']}")
    typer.echo(f"Checked package items: {check['checked_item_count']}")
    typer.echo(f"Missing package items: {len(check['missing_refs'])}")
    typer.echo(f"Mismatched package items: {len(check['mismatched_refs'])}")
    typer.echo(f"Unsafe package items: {len(check['unsafe_refs'])}")
    typer.echo(f"Blocked items: {len(check['blocked_items'])}")
    typer.echo(f"Failed controls: {len(check['failed_controls'])}")
    typer.echo("Provider calls: not started" if not check["provider_calls_started"] else "Provider calls: started")
    typer.echo("Writes long-term memory: false" if not check["writes_long_term_memory"] else "Writes long-term memory: true")
    typer.echo("Writes Company KB: false" if not check["writes_company_kb"] else "Writes Company KB: true")
    if output_path is not None:
        typer.echo(f"Wrote: {str(output_path).replace(chr(92), '/')}")

    if check["check_status"] != "passed":
        raise typer.Exit(code=1)


__all__ = ("production_memory_loop_check_operator_run_package_command",)
