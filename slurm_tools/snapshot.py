#!/usr/bin/env python
from typing import Optional, List
from pathlib import Path
import random
import shutil
import subprocess
import os
import typer
from rich.console import Console

SNAPSHOT_DIR = os.environ.get("SNAPSHOT_DIR", "snapshotted_experiments")
if 'SNAPSHOT_EXCLUDE' in os.environ:
    EXCLUDE = os.environ.split(',')
else:
    EXCLUDE = None

console = Console()
cli = typer.Typer()


@cli.command()
def main(
    command: str,
    exclude: List[str] = None,
    base_dir: str = SNAPSHOT_DIR,
    experiment_id: Optional[str] = None,
    dry_run: bool = False,
    min_experiment_id=200_000,
    max_experiment_id=300_000
):
    """
    This tool helps isolate experiments on NFS by:
    1. Copying the contents of the current directory to another one, keyed either randomly or using a given identifier
    2. Changing the current directory to that new directory
    3. Executing the given command in the new directory

    For example, you can run:
    $ snapshot --experiment-id 42 'echo "my awesome experiment"'
    """
    if exclude is None and EXCLUDE is not None:
        exclude = exclude

    if dry_run:
        console.log("Running in dry run mode, no changes will be made")
    current_dir = os.getcwd()
    if experiment_id is None:
        experiment_id = random.randint(min_experiment_id, max_experiment_id)
    experiment_dir = Path(base_dir) / f"experiment_{experiment_id}"
    if experiment_dir.exists():
        console.log("Experiment code dir exists, deleting before copying")
        shutil.rmtree(experiment_dir)
    console.log(f"Excluding: {exclude} for Copying: {current_dir} to {experiment_dir}")
    if not dry_run:
        if exclude is None:
            shutil.copytree(
                current_dir, experiment_dir,
            )
        else:
            shutil.copytree(
                current_dir, experiment_dir, ignore=shutil.ignore_patterns(*exclude)
            )
        os.chdir(experiment_dir)
    console.log(f"Running: {command} from {os.getcwd()}")
    if not dry_run:
        subprocess.run(command, shell=True, check=True)


if __name__ == "__main__":
    cli()