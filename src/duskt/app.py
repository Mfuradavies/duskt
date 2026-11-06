"""Textual user interface for Duskt."""

import asyncio
from pathlib import Path
from typing import Generic, Optional, TypeVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual import work
from textual.message import Message
from textual.strip import Strip
from textual.widgets import Footer, Input, ProgressBar, SelectionList, Static
from textual.widgets._selection_list import Selection
import pyperclip
from rich.segment import Segment
from rich.style import Style
from textual.widgets._option_list import OptionDoesNotExist

from .downloader import (
    DownloadError,
    Downloader,
    DownloadProgress,
    FormatOption,
    VideoEntry,
    VideoInfo,
)

SelectionType = TypeVar("SelectionType")


class ClipboardInput(Input):
    """Input with a clipboard fallback for terminals that don't paste Ctrl+V."""

    BINDINGS = [
        Binding("ctrl+v", "paste_clipboard", "Paste", show=False),
        Binding("ctrl+shift+v", "paste_clipboard", "Paste", show=False),
        Binding("shift+insert", "paste_clipboard", "Paste", show=False),
    ]

    def action_paste_clipboard(self) -> None:
        try:
            self.insert_text_at_cursor(pyperclip.paste())
        except pyperclip.PyperclipException as exc:
            self.notify(f"Clipboard unavailable: {exc}", severity="error")


class RadioSelectionList(SelectionList[SelectionType], Generic[SelectionType]):
    """SelectionList with simple radio indicators instead of checkbox buttons."""

    def render_line(self, y: int) -> Strip:
        line = super(SelectionList, self).render_line(y)
        _, scroll_y = self.scroll_offset
        selection_index = scroll_y + y
        try:
            selection = self.get_option_at_index(selection_index)
        except OptionDoesNotExist:
            return line

        component_style = "selection-list--button"
        if selection.value in self._selected:
            component_style += "-selected"
        if self.highlighted == selection_index:
            component_style += "-highlighted"

        underlying_style = next(iter(line)).style or self.rich_style
        indicator_style = self.get_component_rich_style(component_style)
        indicator_style += Style(meta={"option": selection_index})
        return Strip(
            [
                Segment(
                    "●" if selection.value in self._selected else "○",
                    style=indicator_style,
                ),
                Segment(" ", style=underlying_style),
                *line,
            ]
        )

    def _get_left_gutter_width(self) -> int:
        return 2


class FormatSelector(RadioSelectionList[FormatOption]):
    """Compact Space-to-select format picker."""

    BINDINGS = [
        Binding("space", "select", "Toggle", show=False),
        Binding("enter", "confirm", "Confirm", show=False),
    ]

    class Confirmed(Message):
        pass

    def action_confirm(self) -> None:
        self.post_message(self.Confirmed())


class VideoSelector(RadioSelectionList[VideoEntry]):
    """Space-to-select playlist videos."""

    BINDINGS = [
        Binding("space", "select", "Toggle", show=False),
        Binding("enter", "confirm", "Confirm", show=False),
    ]

    class Confirmed(Message):
        pass

    def action_confirm(self) -> None:
        self.post_message(self.Confirmed())


class DusktApp(App[None]):
    TITLE = "duskt"
    CSS_PATH = "app.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("s", "settings", "Settings"),
    ]
    FETCH_TIMEOUT_SECONDS = 30

    def __init__(self) -> None:
        super().__init__()
        self.downloader = Downloader()
        self.video_url = ""
        self.video_info: Optional[VideoInfo] = None
        self.selected_videos: tuple[VideoEntry, ...] = ()
        self.fetch_spinner = None
        self.fetch_spinner_frames = ("-", "|", "/", "\\")
        self.fetch_spinner_index = 0

    def compose(self) -> ComposeResult:
        with Container(id="app-container"):
            with Horizontal(id="topbar"):
                yield Static(
                    "DDDDDDDD   U     U  SSSSSSSS  K    K  TTTTTTTTTT\n"
                    "D       D  U     U  S         K   K       T      \n"
                    "D       D  U     U  SSSSSSSS  KKK         T      \n"
                    "D       D  U     U         S  K   K       T      \n"
                    "DDDDDDDD   UUUUUUU  SSSSSSSS  K    K      T      \n"
                    "                                  \n"
                    "DDDDDDDD   U     U  SSSSSSSS  K    K  TTTTTTTTTT\n"
                    "DD       D  U     U  S         K   K       T      \n"
                    "DD       D  U     U  SSSSSSSS  KKK         T      \n"
                    "DD       D  U     U         S  K   K       T      \n"
                    "DDDDDDDD   UUUUUUU  SSSSSSSS  K    K      T      ",
                    id="logo",
                )
            with Vertical(classes="panel", id="url-panel"):
                yield Static("URL", classes="prompt")
                yield ClipboardInput(
                    placeholder="paste a video link, then press Enter", id="url-input"
                )
                yield Static("", id="url-error", classes="status")
            with Vertical(classes="panel hidden", id="details-panel"):
                yield Static("Title", classes="prompt")
                yield Static("", id="title-display")
                yield Static("", id="metadata", classes="muted")
                with Vertical(id="playlist-panel", classes="hidden"):
                    yield Static(
                        "Videos  (↑ ↓ move · Space select · Enter confirm)",
                        classes="prompt",
                    )
                    yield VideoSelector(id="video-selector", compact=True)
                yield Static(
                    "Formats  (↑ ↓ move · Space select · Enter confirm)",
                    classes="prompt hidden",
                    id="format-prompt",
                )
                yield FormatSelector(id="format-selector", compact=True)
                yield Static("", id="details-error", classes="error")
            with Vertical(classes="panel hidden", id="progress-panel"):
                yield Static("Download", classes="prompt")
                yield Static("", id="download-name")
                yield ProgressBar(total=100, show_eta=False, id="progress")
                yield Static("Waiting for download…", id="progress-text")
        yield Footer()

    def action_settings(self) -> None:
        self.notify("Settings are not configurable yet.", severity="information")

    def on_mount(self) -> None:
        self.query_one("#url-input", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "url-input":
            self._fetch()
    def on_format_selector_confirmed(self, _event: FormatSelector.Confirmed) -> None:
        del _event
        self._start_download()

    def on_video_selector_confirmed(self, _event: VideoSelector.Confirmed) -> None:
        del _event
        selected = tuple(self.query_one("#video-selector", VideoSelector).selected)
        if not selected:
            self.query_one("#details-error", Static).update("Select at least one video with Space.")
            return
        self.selected_videos = selected
        self.query_one("#playlist-panel").add_class("hidden")
        self.query_one("#format-prompt").remove_class("hidden")
        self.query_one("#format-selector", FormatSelector).focus()

    def _fetch(self) -> None:
        url = self.query_one("#url-input", Input).value.strip()
        error = self.query_one("#url-error", Static)
        if not url:
            error.update("Enter a video URL first.")
            return
        self.video_url = url
        self.fetch_spinner_index = 0
        self.fetch_spinner = self.set_interval(0.15, self._update_fetch_status)
        self._update_fetch_status()
        self.query_one("#url-input", Input).disabled = True
        self._fetch_worker()

    def _update_fetch_status(self) -> None:
        frame = self.fetch_spinner_frames[self.fetch_spinner_index]
        self.fetch_spinner_index = (self.fetch_spinner_index + 1) % len(
            self.fetch_spinner_frames
        )
        self.query_one("#url-error", Static).update(f"Fetching video details {frame}")

    def _stop_fetch_spinner(self) -> None:
        if self.fetch_spinner is not None:
            self.fetch_spinner.stop()
            self.fetch_spinner = None

    @work
    async def _fetch_worker(self) -> None:
        try:
            info = await asyncio.wait_for(
                asyncio.to_thread(self.downloader.fetch_info, self.video_url),
                timeout=self.FETCH_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            self._stop_fetch_spinner()
            self.query_one("#url-error", Static).update(
                "Fetching timed out after 30 seconds. Check the URL or your connection."
            )
            self.query_one("#url-input", Input).disabled = False
            self.query_one("#url-input", Input).focus()
            return
        except DownloadError as exc:
            self._stop_fetch_spinner()
            self.query_one("#url-error", Static).update(f"Could not fetch video: {exc}")
            self.query_one("#url-input", Input).disabled = False
            self.query_one("#url-input", Input).focus()
            return
        self._stop_fetch_spinner()
        self.video_info = info
        self.query_one("#url-error", Static).update("")
        self.query_one("#url-panel").add_class("hidden")
        self.query_one("#details-panel").remove_class("hidden")
        self.query_one("#title-display", Static).update(info.title)
        duration = f"{info.duration // 60}:{info.duration % 60:02d}" if info.duration else "unknown length"
        self.query_one("#metadata", Static).update(
            f"{duration} · {len(info.formats)} formats available"
        )
        if info.playlist:
            self.selected_videos = ()
            playlist = self.query_one("#playlist-panel")
            playlist.remove_class("hidden")
            video_selector = self.query_one("#video-selector", VideoSelector)
            video_selector.set_options(
                [
                    Selection(
                        (
                            f"{entry.title} ({entry.duration // 60}:{entry.duration % 60:02d})"
                            if entry.duration
                            else entry.title
                        ),
                        entry,
                    )
                    for entry in info.playlist
                ]
            )
            video_selector.highlighted = 0
            video_selector.focus()
        else:
            self.selected_videos = (VideoEntry(self.video_url, info.title, info.duration),)
            self.query_one("#format-prompt").remove_class("hidden")
            self.query_one("#format-selector", FormatSelector).focus()
        selector = self.query_one("#format-selector", FormatSelector)
        selector.set_options(
            [Selection(option.label, option) for option in info.formats]
        )
        selector.highlighted = 0

    def _start_download(self) -> None:
        if not self.video_info:
            return
        options = list(self.query_one("#format-selector", FormatSelector).selected)
        if not options:
            self.query_one("#details-error", Static).update("Select at least one format with Space.")
            return
        self.query_one("#details-error", Static).update("")
        self.query_one("#details-panel").add_class("hidden")
        self.query_one("#progress-panel").remove_class("hidden")
        self.query_one("#download-name", Static).update(
            f"{len(self.selected_videos)} video(s)"
        )
        self._download_worker(options, self.selected_videos)

    @work
    async def _download_worker(
        self, options: list[FormatOption], videos: tuple[VideoEntry, ...]
    ) -> None:
        total_units = len(options) * len(videos)
        completed_units = 0
        for video_index, video in enumerate(videos, 1):
            for option in options:
                def progress(data: DownloadProgress) -> None:
                    self.call_from_thread(
                        self._update_progress,
                        data,
                        completed_units,
                        total_units,
                        video_index,
                        len(videos),
                    )

                try:
                    await asyncio.to_thread(
                        self.downloader.download,
                        video.url,
                        option.format_id,
                        Path.home() / "Downloads",
                        f"{video.title}-"
                        f"{'audio' if option.audio_only else f'{option.height}p'}-{option.ext}"
                        if len(options) > 1
                        else video.title,
                        progress,
                        option.audio_only,
                        option.requires_merge,
                    )
                except Exception as exc:
                    self.query_one("#progress-text", Static).update(f"Download failed: {exc}")
                    return
                completed_units += 1
                self.query_one("#progress", ProgressBar).update(
                    progress=completed_units / total_units * 100
                )
        self.query_one("#progress-text", Static).update(
            f"✓ Downloaded {len(videos)} video(s)"
        )

    def _update_progress(
        self,
        data: DownloadProgress,
        completed_units: int,
        total_units: int,
        video_index: int,
        total_videos: int,
    ) -> None:
        if data.total:
            current_fraction = min(data.downloaded / data.total, 1)
        else:
            current_fraction = 0
        overall_percent = (completed_units + current_fraction) / total_units * 100
        self.query_one("#progress", ProgressBar).update(progress=overall_percent)
        percent = f"{overall_percent:.0f}%"
        speed = f"{data.speed / 1_000_000:.1f} MB/s" if data.speed else "—"
        self.query_one("#progress-text", Static).update(
            f"video {video_index}/{total_videos} · {percent} · {speed}"
        )


def main() -> None:
    DusktApp().run()
