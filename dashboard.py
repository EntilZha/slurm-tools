from typing import Optional
import streamlit as st
from datetime import datetime
import os
import re
import subprocess
from pydantic import BaseModel
from pathlib import Path
import glob

st.set_page_config(layout="wide")

SLURM_LOG_DIR = os.environ.get("SLURM_DASHBOARD_DIR", "")


# NOTE: This needs to be something manually called, e.g. a button
# to avoid trouble with calling this too much
def squeue():
    output = subprocess.run(
        f'squeue --format="%.18i %.9P %.30j %.8u %.8T %.10M %.9l %.6D %R" --me',
        check=True,
        shell=True,
        capture_output=True,
        text=True,
    )
    rows = output.stdout.strip().split("\n")
    if len(rows) == 1:
        return "No jobs running"
    else:
        return rows


def slurm_job_info(job_id):
    job_id = job_id.replace("_0", "")
    output = subprocess.run(
        f"sacct -j {job_id}", check=True, shell=True, capture_output=True, text=True
    )
    return output.stdout


class Job(BaseModel):
    job_id: str
    info: Optional[str]

    @property
    def out_path(self):
        return Path(SLURM_LOG_DIR) / f"{self.job_id}_log.out"

    @property
    def err_path(self):
        return Path(SLURM_LOG_DIR) / f"{self.job_id}_log.err"

    @property
    def modified(self):
        return datetime.fromtimestamp(
            max(self.out_path.stat().st_mtime, self.err_path.stat().st_mtime)
        )

    @property
    def out(self):
        with open(self.out_path) as f:
            return f.read()

    @property
    def err(self):
        with open(self.err_path) as f:
            return f.read()


def load_job_logs():
    jobs = {}
    for p in glob.glob(f"{SLURM_LOG_DIR}/*_log.out"):
        filename = Path(p).name
        job_id = re.match("(.*)_log\.out", filename).group(1)
        if job_id not in jobs:
            jobs[job_id] = Job(job_id=job_id)
    for p in glob.glob(f"{SLURM_LOG_DIR}/*_log.err"):
        filename = Path(p).name
        job_id = re.match("(.*)_log\.err", filename).group(1)
        if job_id not in jobs:
            jobs[job_id] = Job(job_id=job_id)
    return jobs


st.header(f"Slurm Dashboard for {SLURM_LOG_DIR}")

st.subheader("Currently Running Jobs via squeue")
run_squeue = st.button("Refresh squeue")
if run_squeue:
    squeue_out = squeue()
else:
    squeue_out = "Click 'Refresh squeue' to update jobs"

slurm_jobs = load_job_logs()


st.text(squeue_out)
current_job_id = None
with st.sidebar:
    st.header("Slurm Jobs")
    if len(slurm_jobs) == 0:
        st.warning("There are no slurm jobs in directory, so nothing to do yet")
    else:
        for job_id, job in sorted(slurm_jobs.items(), reverse=True):
            col1, col2, col3 = st.columns(3)
            col1.write(job_id)
            col2.write(job.modified)
            button_placeholder = col3.empty()
            view_job = button_placeholder.button("View", key=job_id)
            if view_job:
                current_job_id = job_id

if len(slurm_jobs) == 0:
    st.warning("There are no slurm jobs in directory, so nothing to do yet")
else:
    if current_job_id is None:
        current_job_id = sorted(slurm_jobs.keys(), reverse=True)[0]
    current_job = slurm_jobs[current_job_id]

    st.header(f"Job ID: {current_job_id}")
    if st.button("Load sacct Info"):
        job_info = slurm_job_info(current_job_id)
        current_job.info = job_info
        st.subheader("Job Info")

    if current_job.info is not None:
        st.code(job_info)

    out, err = st.tabs(["Standard Out", "Standard Error"])
    out.subheader("Standard Out")
    out.code(current_job.out)
    err.subheader("Standard Err")
    err.code(current_job.err)
