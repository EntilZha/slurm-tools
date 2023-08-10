from pathlib import Path
from typing import Optional, cast, Union

from rich.measure import measure_renderables
from rich.text import Text
from rich.protocol import is_renderable
from rich.segment import Segment
from rich.console import RenderableType
from rich.pretty import Pretty

from textual.geometry import Size
from textual.reactive import var
from textual.strip import Strip
from textual.widgets import TextLog

class BottomBufferedTextLog(TextLog):
    current_line: var[int] = var(0)

    def __init__(
        self,
        *,
        buffer_size: int = 300,
        scroll_buffer_size: int = 50,
        max_lines: Optional[int] = None,
        min_width: int = 78,
        wrap: bool = False,
        highlight: bool = False,
        markup: bool = False,
        auto_scroll: bool = True,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
        disabled: bool = False,
    ) -> None:
        self.buffer_size = buffer_size
        self.scroll_buffer_size = scroll_buffer_size
        self.file_lines = []
        self._bottom_buffered_idx = 0
        super().__init__(
            max_lines=max_lines,
            min_width=min_width,
            wrap=wrap,
            highlight=highlight,
            markup=markup,
            auto_scroll=auto_scroll,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )

    def watch_current_line(self, current_line: int) -> None:
        if current_line > self._bottom_buffered_idx - self.scroll_buffer_size:
            self.write_new_buffered_bottom()

    def render_line(self, y: int) -> Strip:
        self.current_line = y + self.scroll_offset.y
        return super().render_line(y)

    def write_new_buffered_bottom(self):
        if self._bottom_buffered_idx + 1 >= len(self.file_lines):
            return
        start = self._bottom_buffered_idx
        end = self._bottom_buffered_idx + self.buffer_size
        lines_to_render = self.file_lines[start:end]
        self.write("".join(lines_to_render))
        self._bottom_buffered_idx += len(lines_to_render)


    def load_log_file(self, path: Path):
        with open(path, newline='\n') as f:
            lines = f.readlines()
        print('Num lines:', len(lines))
        self.file_lines = lines
        self._bottom_buffered_idx = 0
        self.write_new_buffered_bottom()

    def goto_top(self):
        self.clear()
        self.scroll_to(y=0, animate=False)
        self._top_buffered_idx = 0
        self._bottom_buffered_idx = 0
        self.write_new_buffered_bottom()


class BufferedTextLog(TextLog):
    current_line: var[int] = var(0)

    def __init__(
        self,
        *,
        buffer_size: int = 500,
        scroll_buffer_size: int = 50,
        max_lines: Optional[int] = None,
        min_width: int = 78,
        wrap: bool = False,
        highlight: bool = False,
        markup: bool = False,
        auto_scroll: bool = True,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
        disabled: bool = False,
    ) -> None:
        self.buffer_size = buffer_size
        self.scroll_buffer_size = scroll_buffer_size
        self.file_lines = []
        self._top_buffered_idx = 0
        self._bottom_buffered_idx = 0
        super().__init__(
            max_lines=max_lines,
            min_width=min_width,
            wrap=wrap,
            highlight=highlight,
            markup=markup,
            auto_scroll=auto_scroll,
            name=name,
            id=id,
            classes=classes,
            disabled=disabled,
        )

    def write_top(
        self,
        content: Union[RenderableType, object],
        width: Optional[int] = None,
        expand: Optional[bool] = False,
        shrink: bool = True,
        scroll_end: Optional[bool] = None,
    ):
        """Write text or a rich renderable to the top of the lines

        This is exactly the same as write, but adds the lines before all others.

        Args:
            content: Rich renderable (or text).
            width: Width to render or `None` to use optimal width.
            expand: Enable expand to widget width, or `False` to use `width`.
            shrink: Enable shrinking of content to fit width.
            scroll_end: Enable automatic scroll to end, or `None` to use `self.auto_scroll`.

        Returns:
            The `TextLog` instance.
        """

        auto_scroll = self.auto_scroll if scroll_end is None else scroll_end

        renderable: RenderableType
        if not is_renderable(content):
            renderable = Pretty(content)
        else:
            if isinstance(content, str):
                if self.markup:
                    renderable = Text.from_markup(content)
                else:
                    renderable = Text(content)
                if self.highlight:
                    renderable = self.highlighter(renderable)
            else:
                renderable = cast(RenderableType, content)

        console = self.app.console
        render_options = console.options

        if isinstance(renderable, Text) and not self.wrap:
            render_options = render_options.update(overflow="ignore", no_wrap=True)

        render_width = measure_renderables(
            console, render_options, [renderable]
        ).maximum
        container_width = (
            self.scrollable_content_region.width if width is None else width
        )
        if container_width:
            if expand and render_width < container_width:
                render_width = container_width
            if shrink and render_width > container_width:
                render_width = container_width

        segments = self.app.console.render(
            renderable, render_options.update_width(render_width)
        )
        lines = list(Segment.split_lines(segments))
        if not lines:
            return self

        self.max_width = max(
            self.max_width,
            max(sum([segment.cell_length for segment in _line]) for _line in lines),
        )
        strips = Strip.from_lines(lines)
        for strip in strips:
            strip.adjust_cell_length(render_width)
        self.lines = strips + self.lines
        # self.lines.extend(strips)

        if self.max_lines is not None and len(self.lines) > self.max_lines:
            self._start_line += len(self.lines) - self.max_lines
            self.refresh()
            self.lines = self.lines[-self.max_lines :]
        self.virtual_size = Size(self.max_width, len(self.lines))
        if auto_scroll:
            self.scroll_end(animate=False)

        return self

    def watch_current_line(self, current_line: int) -> None:
        if current_line > self._bottom_buffered_idx - self.scroll_buffer_size:
            self.write_new_buffered_bottom()
        
        if self._top_buffered_idx > 0 and current_line < self.scroll_buffer_size:
            print("Render rows above")
            self.write_new_buffered_top()
            self.scroll_to(y=current_line + self.buffer_size, animate=False)

    def render_line(self, y: int) -> Strip:
        self.current_line = y + self.scroll_offset.y
        return super().render_line(y)

    def write_new_buffered_bottom(self):
        if self._bottom_buffered_idx + 1 >= len(self.file_lines):
            return
        start = self._bottom_buffered_idx
        end = self._bottom_buffered_idx + self.buffer_size
        lines_to_render = self.file_lines[start:end]
        self.write("".join(lines_to_render))
        self._bottom_buffered_idx += len(lines_to_render)

    def write_new_buffered_top(self):
        if self._top_buffered_idx <= 0:
            return
        start = max(0, self._top_buffered_idx - self.buffer_size)
        end = self._top_buffered_idx
        lines_to_render = self.file_lines[start:end]
        #self.write_top("".join(lines_to_render))
        self.clear()
        self.write("".join(self.file_lines[start:self._bottom_buffered_idx]))
        self._top_buffered_idx -= max(0, len(lines_to_render))
        print(f"Rendered top rows: n={len(lines_to_render)} file: {start} to {end}")
        print(f"top: {self._top_buffered_idx} bottom: {self._bottom_buffered_idx}")

    def load_log_file(self, path: Path):
        with open(path, newline='\n') as f:
            lines = f.readlines()
        print('Num lines:', len(lines))
        self.file_lines = lines
        self._top_buffered_idx = 0
        self._bottom_buffered_idx = 0
        self.write_new_buffered_bottom()

    def goto_top(self):
        self.clear()
        self.scroll_to(y=0, animate=False)
        self._top_buffered_idx = 0
        self._bottom_buffered_idx = 0
        self.write_new_buffered_bottom()

    def goto_bottom(self):
        self.clear()
        self._top_buffered_idx = len(self.file_lines)
        self._bottom_buffered_idx = len(self.file_lines)
        self.write_new_buffered_top()
        self.scroll_to(y=self.buffer_size, animate=False)
