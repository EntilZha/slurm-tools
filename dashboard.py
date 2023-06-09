from typing import Optional
import pandas as pd
import streamlit as st
from datetime import datetime
import os
import re
import subprocess
from pydantic import BaseModel
from pathlib import Path
import glob

st.set_page_config(layout="wide")
st.markdown(
    """
    <style>
    [data-testid="stSidebar"][aria-expanded="true"] > div:first-child {
        width: 450px;
    }
    [data-testid="stSidebar"][aria-expanded="false"] > div:first-child {
        width: 450px;
        margin-left: -450px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
SLURM_LOG_DIR = os.environ.get("SLURM_DASHBOARD_DIR", "")


# NOTE: This needs to be something manually called, e.g. a button
# to avoid trouble with calling this too much
def squeue():
    output = subprocess.run(
        f'squeue --me --Format "JobId:|,Partition:|,Name:|,State:|,TimeUsed:|,NumNodes:|,Nodelist:|,tres-per-node:|,UserName"',
        check=True,
        shell=True,
        capture_output=True,
        text=True,
    )
    rows = output.stdout.strip().split("\n")
    if len(rows) == 1:
        return "No jobs running"
    else:
        rows = [[f.strip() for f in r.split("|")] for r in rows]
        header = rows[0]
        content = rows[1:]
        return pd.DataFrame(content, columns=header)


def slurm_job_info(job_id):
    job_id = job_id.replace("_0", "")
    output = subprocess.run(
        f"sacct -j {job_id} --format 'JobID,JobName,Partition,Account,AllocCPUS,ReqMem,AllocTRES,State,ExitCode'", check=True, shell=True, capture_output=True, text=True
    )
    return output.stdout


class Job(BaseModel):
    job_id: str
    info: Optional[str]
    cache_state: Optional[str]
    cache_out: Optional[str]
    cache_err: Optional[str]

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
        if self.cache_out is None:
            with open(self.out_path) as f:
                self.cache_out = f.read()
        return self.cache_out

    @property
    def err(self):
        if self.cache_err is None:
            with open(self.err_path) as f:
                self.cache_err = f.read()
        return self.cache_err

    @property
    def state(self):
        if self.cache_state is None:
            if "Submitted job triggered an exception" in self.out:
                self.cache_state = "ERROR"
            elif "Job has timed out" in self.out:
                self.cache_state = "TIMED OUT"
            elif "Job completed successfully" in self.out:
                self.cache_state = "COMPLETED"
            else:
                self.cache_state = "UNKNOWN"
        return self.cache_state


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


if isinstance(squeue_out, str):
    st.text(squeue_out)
else:
    st.table(squeue_out)
current_job_id = None
with st.sidebar:
    st.header("Slurm Jobs")
    job_prefix_filter = st.text_input("Job ID Prefix Filter")
    if len(slurm_jobs) == 0:
        st.warning("There are no slurm jobs in directory, so nothing to do yet")
    else:
        col1, col2, col3, col4 = st.columns(4)
        col1.subheader("Job ID")
        col2.subheader("Time")
        col3.subheader("State")
        col4.subheader("View")
        for job_id, job in sorted(slurm_jobs.items(), reverse=True):
            col1, col2, col3, col4 = st.columns(4)
            if job_prefix_filter != "":
                if not job_id.startswith(job_prefix_filter):
                    continue
            col1.write(job_id)
            col2.write(job.modified.strftime("%Y-%m-%d %H:%M"))
            col3.write(job.state)
            button_placeholder = col4.empty()
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
