import shutil
import sys
import tempfile
from pathlib import Path
from typing import Optional

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

import typer

from opt.audio.preprocess import load_audio, peak_normalize, write_audio
from opt.io.ffmpeg import extract_audio, mux_video_with_audio
from opt.logging_setup import setup_logging
from opt.ml.separation import separate_vocals_demucs

app = typer.Typer(add_completion=False, help="Game video VC removal tool")

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

logger = setup_logging(__name__)


def print_progress(label: str, percent: int, message: str) -> None:
    print(f"[{label}] {percent}% - {message}", flush=True)


def collect_inputs(input_path: Optional[Path]) -> list[Path]:
    if input_path:
        return [input_path]
    return sorted(INPUT_DIR.glob("*.mp4"))


@app.command()
def run(
    input_path: Optional[Path] = typer.Option(None, help="Explicit mp4 path (default: opt/input/*.mp4 first)"),
):
    """
    mp4ゲーム動画からボイスチャットを除去するツール（Demucs専用）。
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    targets = collect_inputs(input_path)
    if not targets:
        msg = "No mp4 files found in opt/input"
        logger.info(msg)
        typer.echo(msg)
        return

    for video_file in targets:
        label = video_file.name
        logger.info("Mode=demucs-only video=%s", video_file)

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            extracted = tmpdir_path / "input.wav"
            print_progress(label, 10, "音声抽出")
            extract_audio(video_file, extracted)

            print_progress(label, 25, "Demucsで分離")
            _, no_vocals_path = separate_vocals_demucs(extracted, tmpdir_path / "demucs")
            print_progress(label, 55, "Demucs出力へ差し替え")
            no_vocals_audio, sr = load_audio(no_vocals_path)
            processed = peak_normalize(no_vocals_audio, peak_db=-1.0)

            processed_audio_path = tmpdir_path / "processed.wav"
            write_audio(processed_audio_path, processed, sr)

            print_progress(label, 80, "映像へ戻す")
            output_file = OUTPUT_DIR / f"{video_file.stem}_demucs_no_vocals.mp4"
            mux_video_with_audio(video_file, processed_audio_path, output_file)

            est_no_vc_dst = OUTPUT_DIR / f"{video_file.stem}_estimated_no_vocals.wav"
            shutil.copy(no_vocals_path, est_no_vc_dst)
            logger.info("Exported estimated non-vocals to %s", est_no_vc_dst)

        print_progress(label, 100, f"完了: {output_file.name}")
        typer.echo(f"Done: {output_file}")


if __name__ == "__main__":
    app()
