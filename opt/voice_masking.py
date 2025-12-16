import json
import subprocess
import sys
import tempfile
from logging import config, getLogger
from pathlib import Path

from pydub import AudioSegment

BASE_DIR = Path(__file__).resolve().parent
LOG_CONFIG = BASE_DIR / "log_config.json"
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"


def setup_logger():
    with LOG_CONFIG.open("r") as f:
        log_conf = json.load(f)

    file_handler = log_conf.get("handlers", {}).get("fileHandler", {})
    if file_handler:
        file_handler["filename"] = str(BASE_DIR / "info.log")

    config.dictConfig(log_conf)
    return getLogger(__name__)


logger = setup_logger()


def print_progress(file_name: str, percent: int, message: str) -> None:
    print(f"[{file_name}] {percent}% - {message}", flush=True)


def run_ffmpeg(command: list[str], description: str) -> None:
    logger.debug("Running command: %s", " ".join(command))
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("Failed %s: %s", description, result.stderr)
        raise RuntimeError(f"{description} failed: {result.stderr}")
    logger.debug("Finished %s", description)


def extract_audio(input_file: Path, audio_path: Path) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_file),
        "-vn",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "44100",
        str(audio_path),
    ]
    run_ffmpeg(command, "audio extraction")


def mask_human_voice(source_audio: Path, output_audio: Path) -> None:
    audio = AudioSegment.from_file(source_audio)
    # Simple band-stop style masking that suppresses the mid frequencies typical of human speech.
    low_component = (audio.low_pass_filter(200) - 3)
    high_component = (audio.high_pass_filter(3400) - 3)
    masked_audio = low_component.overlay(high_component)
    masked_audio.export(output_audio, format="wav")


def merge_video_and_audio(input_file: Path, audio_path: Path, output_file: Path) -> None:
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_file),
        "-i",
        str(audio_path),
        "-map",
        "0:v",
        "-map",
        "1:a",
        "-c:v",
        "copy",
        "-shortest",
        str(output_file),
    ]
    run_ffmpeg(command, "video/audio merge")


def process_file(input_file: Path) -> None:
    output_file = OUTPUT_DIR / f"{input_file.stem}_voice_masked.mp4"
    logger.info("Processing started: %s -> %s", input_file, output_file)
    print_progress(input_file.name, 5, "入力の読み込み")

    with tempfile.TemporaryDirectory() as tmpdir:
        raw_audio = Path(tmpdir) / "raw.wav"
        masked_audio = Path(tmpdir) / "masked.wav"

        extract_audio(input_file, raw_audio)
        print_progress(input_file.name, 30, "音声抽出完了")

        mask_human_voice(raw_audio, masked_audio)
        print_progress(input_file.name, 65, "人声帯域のマスキング完了")

        merge_video_and_audio(input_file, masked_audio, output_file)
        print_progress(input_file.name, 95, "映像とマスク済み音声の統合")

    print_progress(input_file.name, 100, "処理完了")
    logger.info("Processing finished: %s", output_file)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not INPUT_DIR.exists():
        logger.error("Input directory not found: %s", INPUT_DIR)
        print("Input directory is missing. Nothing to process.", file=sys.stderr)
        return

    input_files = sorted(INPUT_DIR.glob("*.mp4"))
    if not input_files:
        logger.info("No mp4 files found in %s", INPUT_DIR)
        print("No mp4 files to process.")
        return

    for input_file in input_files:
        try:
            process_file(input_file)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to process %s: %s", input_file, exc)
            print(f"Failed to process {input_file.name}: {exc}", file=sys.stderr)


if __name__ == "__main__":
    main()
