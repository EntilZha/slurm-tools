#!/usr/bin/env python

from pathlib import Path
import asyncio
import os

import typer
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import (
    Markdown,
    Header,
    Footer,
    LoadingIndicator,
    DataTable,
    TextLog,
    TabbedContent,
    TabPane,
    Button,
    Label,
)


SQUEUE = "squeue --me --Format='JobID:|,ArrayJobID:|,ArrayTaskID:|,Partition:|,Name:|,State:|,TimeUsed:|,NumNodes:|,Nodelist:|,STDOUT:|,STDERR:'"
FIELDS = [
    "job_id",
    "array_job_id",
    "array_task_id",
    "partition",
    "name",
    "state",
    "time_used",
    "num_nodes",
    "nodelist",
    "stdout",
    "stderr",
]
DISPLAY_FIELDS = FIELDS[:-2]

cli = typer.Typer()


async def run_squeue():
    if "STUI_CACHE" in os.environ:
        cache = bool(os.environ["STUI_CACHE"])
    else:
        cache = False

    if cache:
        proc = await asyncio.create_subprocess_shell(
            "sleep 3;cat /private/home/par/slurm_tui.txt",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
        lines = stdout.decode("utf8").strip().split("\n")
    else:
        proc = await asyncio.create_subprocess_shell(
            SQUEUE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        lines = stdout.decode("utf8").strip().split("\n")
    table_rows = []
    for idx, l in enumerate(lines):
        if idx == 0:
            continue
        fields = l.strip().split("|")
        if len(fields) != len(FIELDS):
            raise ValueError(
                f"Unequal number of fields: {len(fields)} versus {len(FIELDS)}"
            )
        row = {}
        for i in range(len(fields)):
            curr_field = FIELDS[i]
            value = fields[i]
            row[curr_field] = value

        if "%A" in row["stdout"]:
            row["stdout"] = {
                0: row["stdout"]
                .replace("%A", row["array_job_id"])
                .replace("%a", row["array_task_id"])
            }
            row["stderr"] = {
                0: row["stderr"]
                .replace("%A", row["array_job_id"])
                .replace("%a", row["array_task_id"])
            }
        elif "%n" in row["stdout"]:
            stdout_entries = {}
            stderr_entries = {}
            for node_id in range(int(row["num_nodes"])):
                stdout_entries[node_id] = (
                    row["stdout"]
                    .replace("%j", row["job_id"])
                    .replace("%n", str(node_id))
                )
                stderr_entries[node_id] = (
                    row["stderr"]
                    .replace("%j", row["job_id"])
                    .replace("%n", str(node_id))
                )
            row["stdout"] = stdout_entries
            row["stderr"] = stderr_entries
        elif "%j" in row["stdout"]:
            row["stdout"] = {0: row["stdout"].replace("%j", row["job_id"])}
            row["stderr"] = {0: row["stderr"].replace("%j", row["job_id"])}

        if row["stdout"] == "N/A":
            row["stdout"] = None

        if row["stderr"] == "N/A":
            row["stderr"] = None

        table_rows.append(row)
    lookup_table = {(r["array_job_id"], r["array_task_id"]): r for r in table_rows}
    return table_rows, lookup_table


def read_file(path: Path):
    with open(path) as f:
        return f.readlines()


APP_CSS = """
#queue_table {
    height: 1fr;
}
#loading {
    height: 1fr;
}

.hidden {
    display: none;
}

#logs {
    height: 2fr;
    border: green;
    overflow-y: scroll;
}


#stdout {
    height: auto;
    overflow: hidden;
}

#stderr {
    height: auto;
    overflow: hidden;
}


#stdout_tab {
    height: auto;
}

#stderr_tab {
    height: auto;
}

.green_border {
    border: green;
}

#node_buttons {
    height: 3;
    margin-bottom: 1;
}

.node_button {
    margin: 1 2;
}

.filename_label {
    border: lightblue;
}

Screen {
    scrollbar-color: blue;
    scrollbar-background: gray;
}

#help_container {
    height: auto;
    padding: 1;
    width: 90;
    background: $surface;
    border: thick cyan 80%;
}

HelpScreen {
    align: center middle;
}
"""


HELP = """
- The top half of the viewer shows the output of Slurm `squeue --me`
- The bottom half shows logs for specific slurm jobs/tasks
- Click on rows of the `squeue` table to see the job's stdout/stderr logs below
- Press `r` to refresh squeue (this app does not auto-refresh)
- Press `l` to refresh stdout/err logs
- Press `q` to quit the app
"""


class HelpScreen(ModalScreen):
    def compose(self) -> ComposeResult:
        yield Vertical(
            Label("Help"),
            Markdown(HELP),
            Button("Exit Help", id="exit_help"),
            id="help_container",
        )

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "exit_help":
            self.app.pop_screen()


class SlurmDashboardApp(App):
    TITLE = "Slurm squeue and Log Viewer"
    BINDINGS = [
        ("r", "refresh_slurm", "Refresh Slurm"),
        ("l", "refresh_logs", "Refresh Logs"),
        ("h", "help", "Help"),
        ("q", "quit", "Quit"),
    ]
    CSS = APP_CSS

    def action_help(self) -> None:
        self.push_screen(HelpScreen())

    def action_refresh_logs(self) -> None:
        self._update_log_outputs()

    async def _update_slurm(self):
        self.squeue_rows, self.squeue_lookup = await run_squeue()
        table = self.query_one(DataTable)
        table.clear()
        for (job_id, task_id), row in self.squeue_lookup.items():
            cells = [row[f] for f in DISPLAY_FIELDS]
            table.add_row(*cells, key=f"{job_id}_{task_id}")
        self.query_one("#loading").add_class("hidden")
        self.query_one("#queue_table").remove_class("hidden")

    async def on_mount(self) -> None:
        table = self.query_one(DataTable)
        table.add_columns(*DISPLAY_FIELDS)
        table.cursor_type = "row"
        self.selected_node = 0
        self.num_nodes = 1
        self.entry = None
        self.query_one("#loading").remove_class("hidden")
        self.query_one("#queue_table").add_class("hidden")
        self.run_worker(self._update_slurm(), exclusive=True)
        self.query_one("#stdout").write(
            "No Log File Selected", width=os.get_terminal_size().columns - 2
        )
        self.query_one("#stderr").write(
            "No Log File Selected", width=os.get_terminal_size().columns - 2
        )
        self.query_one("#stdout_filename").update("No Job Selected")
        self.query_one("#stderr_filename").update("No Job Selected")

    def _update_log_outputs(self):
        if self.entry is None:
            return
        if self.entry["stdout"] is None:
            self.query_one("#stdout").clear()
            self.query_one("#stdout").write(
                f"No STDOUT log file configured for selected job"
            )
        else:
            stdout_file = self.entry["stdout"][self.selected_node]
            self.query_one("#stdout").clear()
            self.query_one("#stdout_filename").update(f"STDOUT Log File: {stdout_file}")

            if os.path.exists(stdout_file) and os.path.isfile(stdout_file):
                for line in read_file(stdout_file):
                    self.query_one("#stdout").write(
                        line.strip(),
                        width=os.get_terminal_size().columns - 2,
                    )
            else:
                self.query_one("#stdout").write(
                    f"Path does not exist: {stdout_file}, is it configured with slurm via --output?"
                )

        if self.entry["stderr"] is None:
            self.query_one("#stderr").clear()
            self.query_one("#stderr").write(
                f"No STDERR log file configured for selected job"
            )
        else:
            self.query_one("#stderr").clear()
            stderr_file = self.entry["stderr"][self.selected_node]
            self.query_one("#stderr_filename").update(f"STDERR Log File: {stderr_file}")
            if os.path.exists(stderr_file) and os.path.isfile(stderr_file):
                for line in read_file(stderr_file):
                    self.query_one("#stderr").write(
                        line.strip(),
                        width=os.get_terminal_size().columns - 2,
                    )
            else:
                self.query_one("#stderr").write(
                    f"Path does not exist: {stderr_file}, is it configured with slurm via --error?"
                )

    async def on_data_table_row_selected(self, event: DataTable.RowSelected):
        job_id, task_id = event.row_key.value.split("_")
        key = (job_id, task_id)
        if key in self.squeue_lookup:
            entry = self.squeue_lookup[(job_id, task_id)]
            self.entry = entry
        else:
            raise ValueError(f"Unexpected missing key {key} in:\n{self.squeue_lookup}")
        if self.entry["state"] == "RUNNING":
            self.num_nodes = len(entry["stdout"])
            self.selected_node = 0
            if (
                entry["stdout"] is not None
                and entry["stderr"] is not None
                and len(entry["stdout"]) > 1
            ):
                self.query_one("#node_buttons").remove_class("hidden")
            else:
                self.query_one("#node_buttons").add_class("hidden")
            self._update_log_outputs()
        else:
            out = self.query_one("#stdout")
            err = self.query_one("#stderr")
            out.clear()
            err.clear()
            state = self.entry["state"]
            out.write(f"Selected slurm job has not started yet, is in state: {state}")
            err.write(f"Selected slurm job has not started yet, is in state: {state}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "next_node":
            self.selected_node = (self.selected_node + 1) % self.num_nodes
            self._update_log_outputs()
        elif event.button.id == "prev_node":
            self.selected_node = (self.selected_node - 1) % self.num_nodes
            self._update_log_outputs()

    def compose(self) -> ComposeResult:
        yield Header()
        yield LoadingIndicator(id="loading")
        yield DataTable(id="queue_table", classes="hidden")
        yield Horizontal(
            Button("Previous Node", id="prev_node", classes="node_button"),
            Button("Next Node", id="next_node", classes="node_button"),
            id="node_buttons",
            classes="hidden",
        )
        with TabbedContent(id="logs", classes="green_border"):
            with TabPane("STDOUT"):
                with Vertical(id="stdout_tab"):
                    yield Label(id="stdout_filename", classes="filename_label")
                    yield TextLog(id="stdout", highlight=True, markup=True, wrap=True)
            with TabPane("STDERR"):
                with Vertical(id="stderr_tab"):
                    yield Label(id="stderr_filename", classes="filename_label")
                    yield TextLog(id="stderr", highlight=True, markup=True, wrap=True)
        yield Footer()

    async def action_refresh_slurm(self) -> None:
        self.query_one("#loading").remove_class("hidden")
        self.query_one("#queue_table").add_class("hidden")
        self.run_worker(self._update_slurm(), exclusive=True)


@cli.command()
def main():
    app = SlurmDashboardApp()
    app.run()


if __name__ == "__main__":
    cli()
