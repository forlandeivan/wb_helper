from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
import json
import logging
import os
import shlex
import subprocess
import sys
import tempfile

from wb_helper.domain import ExtractionResult

logger = logging.getLogger(__name__)


class ReelExtractionError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@lru_cache(maxsize=1)
def get_ytdlp_version(ytdlp_bin: str) -> str | None:
    try:
        completed = subprocess.run(
            [*_build_ytdlp_command_prefix(ytdlp_bin), "--version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout.strip() or None


class YtDlpReelExtractor:
    def __init__(
        self,
        ytdlp_bin: str,
        timeout_seconds: int,
        *,
        cookies_file: str | None = None,
        cookies_content: str | None = None,
        instagram_sessionid: str | None = None,
    ) -> None:
        self._ytdlp_bin = ytdlp_bin
        self._timeout_seconds = timeout_seconds
        self._cookies_file = cookies_file
        self._cookies_content = cookies_content
        self._instagram_sessionid = instagram_sessionid

    def extract(self, normalized_url: str, source_id: str) -> ExtractionResult:
        cookies_path = _prepare_cookies_file(
            cookies_file=self._cookies_file,
            cookies_content=self._cookies_content,
            instagram_sessionid=self._instagram_sessionid,
        )
        command = [
            *_build_ytdlp_command_prefix(self._ytdlp_bin),
            "--skip-download",
            "--dump-single-json",
            "--no-warnings",
        ]
        if cookies_path:
            command.extend(["--cookies", cookies_path])
        command.extend(["--", normalized_url])
        logger.info("running_extractor", extra={"source_id": source_id, "command": command[:3]})

        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise ReelExtractionError("timeout", "Extractor timed out") from exc
        except OSError as exc:
            raise ReelExtractionError("binary_missing", "yt-dlp is not available") from exc
        finally:
            if cookies_path and cookies_path != self._cookies_file:
                _remove_temp_file(cookies_path)

        if completed.returncode != 0:
            stderr = (completed.stderr or "").lower()
            if (
                "login required" in stderr
                or "rate-limit reached" in stderr
                or "rate limit reached" in stderr
                or "use --cookies" in stderr
            ):
                raise ReelExtractionError("auth_required", "Instagram requires authentication or hit rate limit")
            if "private" in stderr or "not available" in stderr:
                raise ReelExtractionError("private_or_unavailable", "Reel is private or unavailable")
            raise ReelExtractionError("extract_failed", completed.stderr.strip() or "Extractor failed")

        try:
            payload = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise ReelExtractionError("invalid_json", "Extractor returned invalid JSON") from exc

        caption = (payload.get("description") or payload.get("caption") or "").strip()
        resolved_source_id = str(payload.get("id") or source_id)
        extractor_name = str(payload.get("extractor_key") or payload.get("extractor") or "yt-dlp")

        return ExtractionResult(
            source_url=str(payload.get("webpage_url") or normalized_url),
            source_id=resolved_source_id,
            caption_raw=caption,
            extractor=extractor_name,
            extractor_version=get_ytdlp_version(self._ytdlp_bin),
            extracted_at=datetime.now(timezone.utc),
        )


def _build_ytdlp_command_prefix(ytdlp_bin: str) -> list[str]:
    command = shlex.split(ytdlp_bin, posix=os.name != "nt")
    if not command:
        return [sys.executable, "-m", "yt_dlp"]
    executable_name = os.path.basename(command[0]).lower()
    if executable_name in {"python", "python.exe", os.path.basename(sys.executable).lower()}:
        return [*command, "-m", "yt_dlp"]
    return command


def _prepare_cookies_file(
    *,
    cookies_file: str | None,
    cookies_content: str | None,
    instagram_sessionid: str | None,
) -> str | None:
    if cookies_file:
        return cookies_file

    cookie_text = _build_cookie_text(
        cookies_content=cookies_content,
        instagram_sessionid=instagram_sessionid,
    )
    if cookie_text is None:
        return None

    fd, temp_path = tempfile.mkstemp(prefix="wb-helper-cookies-", suffix=".txt")
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(cookie_text)
    return temp_path


def _build_cookie_text(*, cookies_content: str | None, instagram_sessionid: str | None) -> str | None:
    if cookies_content:
        normalized = cookies_content.replace("\\n", "\n").strip()
        if not normalized:
            return None
        if not normalized.startswith("# HTTP Cookie File") and not normalized.startswith("# Netscape HTTP Cookie File"):
            normalized = "# Netscape HTTP Cookie File\n" + normalized
        return normalized.rstrip() + "\n"

    if instagram_sessionid:
        return (
            "# Netscape HTTP Cookie File\n"
            ".instagram.com\tTRUE\t/\tTRUE\t2147483647\tsessionid\t"
            f"{instagram_sessionid.strip()}\n"
        )

    return None


def _remove_temp_file(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        logger.warning("temp_cookie_cleanup_failed", extra={"path": path})
