"""yt-dlp integration kept separate from the TUI for easy testing."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional, cast
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import yt_dlp


@dataclass(frozen=True)
class FormatOption:
    format_id: str
    label: str
    height: Optional[int]
    ext: str
    audio_only: bool = False
    requires_merge: bool = False


@dataclass(frozen=True)
class VideoInfo:
    title: str
    duration: Optional[int]
    formats: tuple[FormatOption, ...]
    playlist: tuple["VideoEntry", ...] = ()


@dataclass(frozen=True)
class VideoEntry:
    url: str
    title: str
    duration: Optional[int]


@dataclass(frozen=True)
class DownloadProgress:
    downloaded: int
    total: Optional[int]
    speed: Optional[float]
    filename: str


ProgressCallback = Callable[[DownloadProgress], None]


class DownloadError(RuntimeError):
    """Raised when metadata extraction or downloading fails."""


class Downloader:
    """Download videos through yt-dlp without exposing its dictionary API."""

    def fetch_info(self, url: str) -> VideoInfo:
        if self._is_playlist_url(url):
            return self._fetch_playlist_info(url)
        url = self._single_video_url(url)
        return self._fetch_video_info(url)

    def _fetch_video_info(self, url: str) -> VideoInfo:
        try:
            options = {
                    "quiet": True,
                    "no_warnings": True,
                    "ignoreconfig": True,
                    "noplaylist": True,
                    "socket_timeout": 10,
                    "retries": 1,
                    "extractor_retries": 1,
                }
            with yt_dlp.YoutubeDL(cast(Any, options)) as ydl:
                data = ydl.extract_info(url, download=False)
        except Exception as exc:
            message = str(exc).strip() or exc.__class__.__name__
            raise DownloadError(message) from exc

        formats = self._formats(data.get("formats") or [], allow_merge=self._has_ffmpeg())
        if not formats:
            raise DownloadError(
                "No compatible formats were found. Install FFmpeg for more video formats."
            )
        return VideoInfo(
            title=data.get("title") or "video",
            duration=data.get("duration"),
            formats=formats,
        )

    def _fetch_playlist_info(self, url: str) -> VideoInfo:
        try:
            options = {
                    "quiet": True,
                    "no_warnings": True,
                    "ignoreconfig": True,
                    "noplaylist": False,
                    "extract_flat": True,
                    "playlistend": 25,
                    "socket_timeout": 10,
                    "retries": 1,
                    "extractor_retries": 1,
                }
            with yt_dlp.YoutubeDL(cast(Any, options)) as ydl:
                data = ydl.extract_info(url, download=False)
        except Exception as exc:
            message = str(exc).strip() or exc.__class__.__name__
            raise DownloadError(message) from exc

        raw_entries = list(cast(Any, data.get("entries") or ()))[:25]
        entries = tuple(
            VideoEntry(
                url=self._entry_url(entry),
                title=entry.get("title") or f"Video {index}",
                duration=entry.get("duration"),
            )
            for index, entry in enumerate(raw_entries, 1)
            if entry
        )
        if not entries:
            raise DownloadError("The playlist does not contain any videos.")
        first = self._fetch_video_info(entries[0].url)
        return VideoInfo(first.title, first.duration, first.formats, entries)

    def download(
        self,
        url: str,
        format_id: str,
        output_dir: Path,
        title: str,
        on_progress: Optional[ProgressCallback] = None,
        audio_only: bool = False,
        requires_merge: bool = False,
    ) -> Path:
        url = self._single_video_url(url)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_template = str(output_dir / f"{self._safe_title(title)}.%(ext)s")

        def hook(data: dict) -> None:
            if on_progress and data["status"] == "downloading":
                on_progress(
                    DownloadProgress(
                        downloaded=data.get("downloaded_bytes", 0),
                        total=data.get("total_bytes") or data.get("total_bytes_estimate"),
                        speed=data.get("speed"),
                        filename=data.get("filename", ""),
                    )
                )

        options = {
            "format": (
                format_id
                if audio_only or not requires_merge
                else f"{format_id}+bestaudio/best"
            ),
            "outtmpl": output_template,
            "progress_hooks": [hook],
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "ignoreconfig": True,
            "retries": 1,
            "extractor_retries": 1,
            "merge_output_format": "mp4",
            "socket_timeout": 15,
        }
        try:
            with yt_dlp.YoutubeDL(cast(Any, options)) as ydl:
                ydl.download([url])
        except Exception as exc:
            raise DownloadError(str(exc)) from exc

        files = sorted(output_dir.glob(f"{self._safe_title(title)}.*"))
        if not files:
            raise DownloadError("yt-dlp completed without producing a file")
        return files[0]

    @staticmethod
    def _formats(
        raw_formats: list[dict], allow_merge: bool = True
    ) -> tuple[FormatOption, ...]:
        options: list[FormatOption] = []
        seen: set[tuple[str, Optional[int], Optional[int], bool]] = set()
        for item in raw_formats:
            format_id = item.get("format_id")
            height = item.get("height")
            has_video = item.get("vcodec") != "none" and bool(height)
            has_audio = item.get("acodec") != "none" and item.get("acodec")
            if not has_video and not has_audio:
                continue
            ext = item.get("ext") or "video"
            audio_only = not has_video
            requires_merge = has_video and not has_audio
            if requires_merge and not allow_merge:
                continue
            bitrate = item.get("abr")
            key = (ext, height, bitrate if audio_only else None, audio_only)
            if not format_id or key in seen:
                continue
            if audio_only:
                bitrate_label = f" · {bitrate:.0f}kbps" if bitrate else ""
                note = f"AUDIO · {ext.upper()}{bitrate_label}"
            else:
                note = f"VIDEO · {ext.upper()} · {height}p"
            options.append(
                FormatOption(format_id, note, height, ext, audio_only, requires_merge)
            )
            seen.add(key)
        options.sort(
            key=lambda option: (
                option.audio_only,
                option.height or 0,
                option.ext,
            ),
            reverse=True,
        )
        return tuple(options)

    @staticmethod
    def _safe_title(title: str) -> str:
        cleaned = "".join(char for char in title if char.isalnum() or char in " .-_")
        return " ".join(cleaned.split()).strip(" .")[:180] or "video"

    @staticmethod
    def _has_ffmpeg() -> bool:
        import shutil

        return shutil.which("ffmpeg") is not None

    @staticmethod
    def _single_video_url(url: str) -> str:
        """Drop playlist and radio parameters when a YouTube video is requested."""
        parts = urlsplit(url)
        if "youtube.com" not in parts.netloc and parts.netloc != "youtu.be":
            return url
        if parts.netloc == "youtu.be":
            return url
        query = parse_qs(parts.query)
        video_id = query.get("v", [None])[0]
        if not video_id:
            return url
        return urlunsplit(("https", "www.youtube.com", "/watch", urlencode({"v": video_id}), ""))

    @staticmethod
    def _is_playlist_url(url: str) -> bool:
        query = parse_qs(urlsplit(url).query)
        return bool(query.get("list"))

    @staticmethod
    def _entry_url(entry: dict) -> str:
        webpage_url = entry.get("webpage_url")
        if webpage_url:
            return webpage_url
        url = entry.get("url")
        if isinstance(url, str) and url.startswith(("http://", "https://")):
            return url
        entry_id = entry.get("id")
        if not isinstance(entry_id, str) or not entry_id:
            raise DownloadError("Playlist contains an entry without a video URL.")
        return f"https://www.youtube.com/watch?v={entry_id}"
