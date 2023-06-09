import subprocess
import glob
from pathlib import Path

import typer
from rich.console import Console

console = Console()
cli = typer.Typer()


@cli.command()
def main(log_dir: str, latest: bool = True, tail_stdout: bool = False, tail_stderr: bool = False):
    slurm_jobs = []
    for f in glob.glob(f"{log_dir}/*_submission.sh"):
        job_id = int(Path(f).name.split('_')[0])
        slurm_jobs.append(job_id)
    
    slurm_jobs = sorted(slurm_jobs, reverse=latest)
    recent_job_id = slurm_jobs[0]
    array_id = 0
    err_log = Path(log_dir) / f"{recent_job_id}_{array_id}_log.err"
    out_log = Path(log_dir) / f"{recent_job_id}_{array_id}_log.out"
    console.print(f"Showing Slurm Job ID: {recent_job_id}")
    console.print(f"STDOUT: {out_log}")
    if tail_stdout:
        subprocess.run(f"tail -f {out_log}", shell=True)
    else:
        subprocess.run(f"cat {out_log}", shell=True)
    console.print()

    console.print(f"STDERR: {err_log}")
    if tail_stderr:
        subprocess.run(f"tail -f {err_log}", shell=True)
    else:
        subprocess.run(f"cat {err_log}", shell=True)
    console.print()

    console.print(f"squeue --job {recent_job_id}")
    subprocess.run(f"squeue --job {recent_job_id}", shell=True)


if __name__ == '__main__':
    cli()