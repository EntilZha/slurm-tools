from pathlib import Path
from typing import Type

from textual.app import App, CSSPathType, ComposeResult
from textual.driver import Driver
from textual.widgets import Header, Footer, TextLog

from slurm_tools.widgets import BufferedTextLog
import typer

class TextLogApp(App):
    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield TextLog(
            highlight=True,
            markup=True,
            wrap=True,
            auto_scroll=False
        )
        yield Footer()
    
    def on_mount(self):
        log = self.query_one(TextLog)
        with open(self.log_file, newline='\n') as f:
            lines = f.readlines()
        log.write("".join(lines))


class BufferedTextLogApp(App):
    BINDINGS = [
        ("b", 'goto_bottom', "Go To Bottom"),
        ("t", 'goto_top', "Go To Top"),
        ("q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield BufferedTextLog(
            buffer_size=500,
            highlight=True,
            markup=True,
            auto_scroll=False
        )
        yield Footer()
    
    def on_mount(self):
        log = self.query_one(BufferedTextLog)
        log.load_log_file(Path(self.log_file))
    
    def action_goto_bottom(self):
        self.query_one(BufferedTextLog).goto_bottom()

    def action_goto_top(self):
        self.query_one(BufferedTextLog).goto_top()


def main(file: str = '/private/home/par/large_log_linenos.out', buffered: bool = True):
    if buffered:
        app = BufferedTextLogApp()
    else:
        app = TextLogApp()
    app.log_file = file
    app.run()

if __name__ == "__main__":
    typer.run(main)

