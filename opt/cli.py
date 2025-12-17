import shutil
import sys
import tempfile
from pathlib import Path
from typing import Literal, Optional

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

import typer

from opt.audio.postprocess import apply_noise_gate, high_freq_restore, suppress_vocal_band
from opt.audio.preprocess import load_audio, peak_normalize, subtract_vocals, write_audio
from opt.io.ffmpeg import extract_audio, list_audio_streams, mute_audio_track, mux_video_with_audio
from opt.logging_setup import setup_logging
from opt.ml.separation import separate_vocals_demucs
from opt.reporting.metrics import vad_speech_ratio

app = typer.Typer(add_completion=False, help="Game video VC removal tool")

BASE_DIR = Path(__file__).resolve().parent
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"

Preset = Literal["light", "balanced", "aggressive"]
Mode = Literal["auto", "tracks", "ai", "hybrid"]

PRESETS: dict[Preset, dict[str, float]] = {
    "light": {"strength": 1.1, "gate_db": -35.0, "hf_restore": 0.1, "vocal_band_cut_db": -10.0},
    "balanced": {"strength": 1.35, "gate_db": -42.0, "hf_restore": 0.1, "vocal_band_cut_db": -15.0},
    "aggressive": {"strength": 1.6, "gate_db": -48.0, "hf_restore": 0.05, "vocal_band_cut_db": -18.0},
}

logger = setup_logging(__name__)


def print_progress(label: str, percent: int, message: str) -> None:
    print(f"[{label}] {percent}% - {message}", flush=True)


def resolve_preset(
    preset: Optional[Preset],
    strength: float,
    gate_db: float,
    hf_restore: float,
    vocal_band_cut_db: float,
) -> dict[str, float]:
    if preset and preset in PRESETS:
        params = PRESETS[preset].copy()
        params.update(
            {
                "strength": strength if strength is not None else params["strength"],
                "gate_db": gate_db if gate_db is not None else params["gate_db"],
                "hf_restore": hf_restore if hf_restore is not None else params["hf_restore"],
                "vocal_band_cut_db": vocal_band_cut_db if vocal_band_cut_db is not None else params["vocal_band_cut_db"],
            }
        )
        logger.info("Using preset %s with overrides %s", preset, params)
        return params

    params = {
        "strength": strength if strength is not None else PRESETS["balanced"]["strength"],
        "gate_db": gate_db if gate_db is not None else PRESETS["balanced"]["gate_db"],
        "hf_restore": hf_restore if hf_restore is not None else PRESETS["balanced"]["hf_restore"],
        "vocal_band_cut_db": vocal_band_cut_db if vocal_band_cut_db is not None else PRESETS["balanced"]["vocal_band_cut_db"],
    }
    logger.info("Using custom params %s", params)
    return params


def collect_inputs(input_path: Optional[Path]) -> list[Path]:
    if input_path:
        return [input_path]
    return sorted(INPUT_DIR.glob("*.mp4"))


def determine_mode(requested: Mode, audio_streams: list[dict]) -> Mode:
    if requested != "auto":
        return requested
    if len(audio_streams) > 1:
        return "tracks"
    return "ai"


@app.command()
def run(
    mode: Mode = typer.Option("auto", help="auto -> track mute if possible, else demucs"),
    preset: Optional[Preset] = typer.Option("balanced", help="Parameter preset"),
    strength: Optional[float] = typer.Option(None, min=0.0, max=2.0, help="Voice removal strength (allows over-subtraction)"),
    gate_db: Optional[float] = typer.Option(None, help="Noise gate threshold in dB"),
    hf_restore: Optional[float] = typer.Option(None, help="Restore high frequencies amount"),
    vocal_band_cut_db: Optional[float] = typer.Option(None, help="Additional vocal band cut in dB (negative to cut)"),
    replace_with_no_vocals: bool = typer.Option(
        False, help="Use Demucs estimated non-vocal stem as the final audio without further processing"
    ),
    export_intermediates: bool = typer.Option(False, help="Save estimated voice stem"),
    input_path: Optional[Path] = typer.Option(None, help="Explicit mp4 path (default: opt/input/*.mp4 first)"),
    track_index: Optional[int] = typer.Option(None, help="Track index to mute in tracks mode"),
):
    """
    mp4ゲーム動画からボイスチャットを抑圧するツール。
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    params = resolve_preset(preset, strength, gate_db, hf_restore, vocal_band_cut_db)

    targets = collect_inputs(input_path)
    if not targets:
        msg = "No mp4 files found in opt/input"
        logger.error(msg)
        typer.echo(msg, err=True)
        raise typer.Exit(code=1)

    for video_file in targets:
        label = video_file.name
        audio_streams = list_audio_streams(video_file)
        chosen_mode = determine_mode(mode, audio_streams)

        logger.info("Mode=%s video=%s", chosen_mode, video_file)

        if chosen_mode == "tracks":
            idx = track_index if track_index is not None else max(len(audio_streams) - 1, 0)
            output_file = OUTPUT_DIR / f"{video_file.stem}_muted_track{idx}.mp4"
            print_progress(label, 10, f"トラック解析: {len(audio_streams)}本")
            mute_audio_track(video_file, idx, output_file)
            print_progress(label, 100, f"トラック{idx}をミュートして出力: {output_file.name}")
            typer.echo(f"Done: {output_file}")
            continue

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)
            extracted = tmpdir_path / "input.wav"
            print_progress(label, 10, "音声抽出")
            extract_audio(video_file, extracted)

            if chosen_mode in ("ai", "hybrid"):
                print_progress(label, 25, "Demucsで分離")
                vocals_path, no_vocals_path = separate_vocals_demucs(extracted, tmpdir_path / "demucs")
            else:
                logger.error("Unsupported mode: %s", chosen_mode)
                typer.echo(f"Unsupported mode: {chosen_mode}", err=True)
                raise typer.Exit(code=1)

            original_audio, sr = load_audio(extracted)
            vocals_audio, _ = load_audio(vocals_path, target_sr=sr)

            if replace_with_no_vocals:
                print_progress(label, 55, "Demucs出力へ差し替え")
                no_vocals_audio, _ = load_audio(no_vocals_path, target_sr=sr)
                processed = peak_normalize(no_vocals_audio, peak_db=-1.0)
            else:
                print_progress(label, 55, "抽出ボイスの減算")
                processed = subtract_vocals(original_audio, vocals_audio, params["strength"])
                processed = suppress_vocal_band(processed, sr, params["vocal_band_cut_db"])
                processed = apply_noise_gate(processed, params["gate_db"])
                processed = high_freq_restore(processed, sr, params["hf_restore"])
                processed = peak_normalize(processed, peak_db=-1.0)

            if chosen_mode == "hybrid":
                speech_ratio = vad_speech_ratio(original_audio, sr)
                logger.info("VAD speech ratio=%.3f (参考値)", speech_ratio)

            processed_audio_path = tmpdir_path / "processed.wav"
            write_audio(processed_audio_path, processed, sr)

            print_progress(label, 80, "映像へ戻す")
            suffix = "_demucs_no_vocals" if replace_with_no_vocals else "_no_vc"
            output_file = OUTPUT_DIR / f"{video_file.stem}{suffix}.mp4"
            mux_video_with_audio(video_file, processed_audio_path, output_file)

            est_no_vc_dst = OUTPUT_DIR / f"{video_file.stem}_estimated_no_vocals.wav"
            shutil.copy(no_vocals_path, est_no_vc_dst)
            logger.info("Exported estimated non-vocals to %s", est_no_vc_dst)

            if export_intermediates:
                est_vc_dst = OUTPUT_DIR / f"{video_file.stem}_estimated_vc.wav"
                shutil.copy(vocals_path, est_vc_dst)
                logger.info("Exported estimated vocals to %s", est_vc_dst)

        print_progress(label, 100, f"完了: {output_file.name}")
        typer.echo(f"Done: {output_file}")


if __name__ == "__main__":
    app()
