# slurm-tools

This repo contains useful slurm tools.

## Installation

Install conda python and poetry.

1. Run `conda create -n tools python=3.8`
2. Run `conda activate tools`
3. Run `conda install poetry`
4. Run `poetry install`

## Dashboard

When running, the dashboard looks like this:
![dashboard-screenshot](https://user-images.githubusercontent.com/1382460/181595475-85b14f52-cc72-4229-a731-739ec97ae3f2.jpeg)



The dashbaord works by inspecting the files contained within the directory specified by `SLURM_DASHBOARD_DIR` for files that follow the slurm logging format `IDENTIFIER_log.out` and `IDENTIFIER_log.out`, where `IDENTIFIER` can be the the job id and array id appended. This is the default format used by submitit, which is how I submit slurm commands, hence that choice.

You can configure something similar in your jobs in the `sbatch` submit file like so for non-array jobs:

```bash
#SBATCH --output=/log_dir/%j_log.out
#SBATCH --error=/log_dir/%j_log.err
```

or like so for array jobs

```bash
#SBATCH --output=/log_dir/%A_%a_log.out
#SBATCH --error=/log_dir/%A_%a_log.err
```

The dashboard uses this to list all slurm jobs run (except those that fail at launch, so have no log files, likely when the logdir doesn't exist). The dashboard does not automatically call `squeue`, but there is a button to load all the user's submitted jobs with better output format than the default. Similarly, for a given job, there is a button to retrieve `sacct` information, but this is not run by default and has to be user triggered. This design is to avoid overloading the slurm daemon with automated commands while making it easier for a human to view it. If jobs are continually running and you need to refresh the list of jobs, either reload the page or use streamlit's built in rerun button `r`.

Run with `streamlit run dashboard.py`

Configure via:

- By setting environment `SLURM_DASHBOARD_DIR`

## Snapshot Tool

This tool helps isolate experiments on NFS by:
1. Copying the contents of the current directory to another one, keyed either randomly or using a given identifier
2. Changing the current directory to that new directory
3. Executing the given command in the new directory

This helps to later reference what code is actually run, even if the source control version is changed (e.g., submit a long running experiment, continue coding while it runs, and need to reference original code).
This also prevents situations in NFS where a running experiment may try to read newly modified code and crashes due to that (e.g., if the job is pre-empted and then rerun at a later time)

For example, you can run:
```
$ snapshot --experiment-id 42 'echo "my awesome experiment"'
```