import shutil
import subprocess

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.logging import get_logger

logger = get_logger(__name__)

FFMPEG_TIMEOUT_SECONDS = 60
# Small slack so float-rounding on probed durations never trips a hard-cap
# re-encode for a video that is already correct to the eye/ear.
DURATION_TOLERANCE_SECONDS = 0.05

MAX_NARRATION_SPEEDUP = 1.10  # FR-017
SCENE_SECONDS = 5.0
NARRATION_SAMPLE_RATE = 24000

RESOLUTIONS = {"16:9": (1280, 720), "9:16": (720, 1280)}


# ffmpeg/ffprobe must never touch the worker's terminal: with an inherited tty stdin,
# ffmpeg's interactive-key reader gets SIGTTIN when the RQ work-horse is not the
# foreground process group, freezing both processes (so no timeout can ever fire).
# stdin=DEVNULL + -nostdin + own session make that impossible.
_SUBPROCESS_ISOLATION = {"stdin": subprocess.DEVNULL, "start_new_session": True}


def _run(cmd: list[str]) -> None:
    if cmd[0] == "ffmpeg":
        # FFMPEG_THREADS caps decoder, filter and encoder threads so assembly can't
        # monopolise the CPU or RAM of a small, shared VPS (every decoder thread holds its
        # own frames). `-threads` is per-file: once before each `-i` (decoders) and once
        # before the output path, which is always the last element of every command here.
        threads = str(get_settings().FFMPEG_THREADS)
        args: list[str] = []
        for arg in cmd[1:-1]:
            if arg == "-i":
                args += ["-threads", threads]
            args.append(arg)
        cmd = [
            cmd[0], "-nostdin", "-filter_threads", threads, "-filter_complex_threads", threads,
            *args, "-threads", threads, cmd[-1],
        ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=FFMPEG_TIMEOUT_SECONDS,
            check=False,
            **_SUBPROCESS_ISOLATION,
        )
    except subprocess.TimeoutExpired as exc:
        logger.error("ffmpeg_timed_out", extra={"cmd": cmd[0]})
        raise AppError(
            "ASSEMBLY_FAILED", "Couldn't finish assembling the video. Please try again."
        ) from exc
    if result.returncode != 0:
        logger.error(
            "ffmpeg_failed",
            extra={"cmd": cmd[0], "returncode": result.returncode, "stderr": result.stderr[-2000:]},
        )
        raise AppError("ASSEMBLY_FAILED", "Couldn't finish assembling the video. Please try again.")


def _probe_duration(path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=FFMPEG_TIMEOUT_SECONDS,
            check=False,
            text=True,
            **_SUBPROCESS_ISOLATION,
        )
    except subprocess.TimeoutExpired as exc:
        raise AppError(
            "ASSEMBLY_FAILED", "Couldn't finish assembling the video. Please try again."
        ) from exc
    if result.returncode != 0 or not result.stdout.strip():
        logger.error("ffprobe_failed", extra={"path": path, "stderr": result.stderr[-2000:]})
        raise AppError("ASSEMBLY_FAILED", "Couldn't finish assembling the video. Please try again.")
    return float(result.stdout.strip())


def normalize_and_concat(clips: list[str], aspect_ratio: str, out_path: str) -> str:
    """Scales/pads every clip to a common resolution+fps, then concatenates
    them (video-only; narration is attached separately)."""
    width, height = RESOLUTIONS[aspect_ratio]
    cmd = ["ffmpeg", "-y"]
    for clip in clips:
        cmd += ["-i", clip]

    filter_parts = []
    for i in range(len(clips)):
        filter_parts.append(
            f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=24[v{i}]"
        )
    concat_inputs = "".join(f"[v{i}]" for i in range(len(clips)))
    filter_complex = ";".join(filter_parts) + f";{concat_inputs}concat=n={len(clips)}:v=1:a=0[outv]"

    cmd += [
        "-filter_complex", filter_complex, "-map", "[outv]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", out_path,
    ]
    _run(cmd)
    return out_path


def fit_scene_narrations(
    narration_paths: list[str],
    out_path: str,
    scene_seconds: float = SCENE_SECONDS,
    max_speedup: float = MAX_NARRATION_SPEEDUP,
) -> str:
    """Builds the narration track scene by scene so scene N's voice plays over scene N's clip
    (FR-017): each narration longer than `scene_seconds` is sped up by at most `max_speedup`
    (AppError('SCRIPT_TOO_LONG') if it still doesn't fit), shorter ones are padded with
    silence, every scene is cut to exactly `scene_seconds`, and the scenes are concatenated."""
    cmd = ["ffmpeg", "-y"]
    parts = []
    for i, path in enumerate(narration_paths):
        duration = _probe_duration(path)
        speedup = 1.0
        if duration > scene_seconds:
            speedup = min(duration / scene_seconds, max_speedup)
            if duration / speedup > scene_seconds + DURATION_TOLERANCE_SECONDS:
                logger.warning(
                    "scene_narration_too_long",
                    extra={"scene": i + 1, "seconds": duration, "limit": scene_seconds},
                )
                raise AppError(
                    "SCRIPT_TOO_LONG",
                    "Script is too long for the chosen duration — please shorten it",
                )
        chain = [f"atempo={speedup:.4f}"] if speedup != 1.0 else []
        chain += [
            f"aresample={NARRATION_SAMPLE_RATE}",
            "aformat=channel_layouts=mono",
            f"apad=whole_dur={scene_seconds}",
            f"atrim=0:{scene_seconds}",
            "asetpts=N/SR/TB",
        ]
        cmd += ["-i", path]
        parts.append(f"[{i}:a]{','.join(chain)}[a{i}]")
    joined = "".join(f"[a{i}]" for i in range(len(narration_paths)))
    filter_complex = ";".join(parts) + f";{joined}concat=n={len(narration_paths)}:v=0:a=1[outa]"
    cmd += ["-filter_complex", filter_complex, "-map", "[outa]", "-c:a", "pcm_s16le", out_path]
    _run(cmd)
    return out_path


def attach_narration(
    video_path: str,
    narration_path: str,
    duration_seconds: float,
    out_path: str,
    max_speedup: float = MAX_NARRATION_SPEEDUP,
) -> str:
    """Attaches narration to the (silent) video, speeding the audio up by at
    most `max_speedup` if it's longer than the video (FR-017). Raises
    AppError('SCRIPT_TOO_LONG') if it still doesn't fit after that speedup."""
    narration_duration = _probe_duration(narration_path)
    speedup = 1.0
    if narration_duration > duration_seconds:
        speedup = min(narration_duration / duration_seconds, max_speedup)
        if (narration_duration / speedup) > duration_seconds + DURATION_TOLERANCE_SECONDS:
            raise AppError(
                "SCRIPT_TOO_LONG",
                "Script is too long for the chosen duration — please shorten it",
            )

    cmd = ["ffmpeg", "-y", "-i", video_path, "-i", narration_path]
    if speedup != 1.0:
        cmd += ["-filter:a", f"atempo={speedup:.4f}"]
    cmd += [
        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-t", str(duration_seconds), "-shortest", "-movflags", "+faststart", out_path,
    ]
    _run(cmd)
    return out_path


def hard_cap_duration(video_path: str, duration_seconds: float, out_path: str) -> str:
    """Forces the final video to exactly duration_seconds regardless of any
    upstream rounding (FR-018): trims if longer, freezes the last frame to
    pad if shorter. Always leaves a file at `out_path` (callers read from
    there unconditionally), even when no adjustment was needed."""
    actual = _probe_duration(video_path)
    if actual > duration_seconds + DURATION_TOLERANCE_SECONDS:
        cmd = [
            "ffmpeg", "-y", "-i", video_path, "-t", str(duration_seconds),
            "-c", "copy", "-movflags", "+faststart", out_path,
        ]
    elif actual < duration_seconds - DURATION_TOLERANCE_SECONDS:
        pad = duration_seconds - actual
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"tpad=stop_mode=clone:stop_duration={pad}",
            "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart", out_path,
        ]
    else:
        shutil.copyfile(video_path, out_path)
        return out_path
    _run(cmd)
    return out_path


def generate_thumbnail(video_path: str, out_path: str) -> str:
    cmd = ["ffmpeg", "-y", "-i", video_path, "-frames:v", "1", "-q:v", "3", out_path]
    _run(cmd)
    return out_path
