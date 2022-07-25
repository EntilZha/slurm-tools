# slurm-tools

## Installation

Install conda python and poetry.

1. Run `conda create -n tools python=3.8`
2. Run `poetry install`

## Dashboard

The dashbaord works by inspecting the files contained within the directory specified by `SLURM_DASHBOARD_DIR` for files that follow the slurm logging format `IDENTIFIER_log.out` and `IDENTIFIER_log.out`, where `IDENTIFIER` can be the the job id and array id appended. This is the default format used by submitit, which is how I submit slurm commands, hence that choice.

The dashboard uses this to list all slurm jobs run (except those that fail at launch, so have no log files, likely when the logdir doesn't exist). The dashboard does not automatically call `squeue`, but there is a button to load all the user's submitted jobs with better output format than the default. Similarly, for a given job, there is a button to retrieve `sacct` information, but this is not run by default and has to be user triggered. This design is to avoid overloading the slurm daemon with automated commands while making it easier for a human to view it. If jobs are continually running and you need to refresh the list of jobs, either reload the page or use streamlit's built in rerun button `r`.

Run with `streamlit run dashboard.py`

Configure via:

- By setting environment `SLURM_DASHBOARD_DIR`
