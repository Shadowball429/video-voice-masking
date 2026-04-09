import subprocess
from pathlib import Path

from opt.logging_setup import setup_logging

logger = setup_logging(__name__)


def _run(command: list[str], description: str) -> subprocess.CompletedProcess[str]:
    logger.debug("Running command: %s", " ".join(command))
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("%s failed: %s", description, result.stderr.strip())
        raise RuntimeError(f"{description} failed: {result.stderr}")
    logger.debug("%s succeeded", description)
    return result


def extract_audio(
    input_path: Path,
    output_wav: Path,
    sample_rate: int = 48000,
    channels: int = 2,
) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        str(sample_rate),
        "-ac",
        str(channels),
        str(output_wav),
    ]
    _run(command, "audio extraction")


def mux_video_with_audio(video_path: Path, audio_path: Path, output_path: Path) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-c:v",
        "copy",
        "-shortest",
        str(output_path),
    ]
    _run(command, "mux video/audio")
