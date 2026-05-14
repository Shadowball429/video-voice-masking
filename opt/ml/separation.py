import os
import subprocess
from pathlib import Path

from opt.logging_setup import setup_logging

logger = setup_logging(__name__)

CHUNK_SECONDS = 180
MIN_CHUNK_SECONDS = 15
DEMUCS_SEGMENT_SECONDS = 6
DEMUCS_OVERLAP = 0.1
DEMUCS_SHIFTS = 0
DEMUCS_JOBS = 0


def _run_checked(command: list[str], description: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"{description} failed (rc={result.returncode}): "
            f"stdout={result.stdout[-500:]} stderr={result.stderr[-500:]}"
        )
    return result


def _convert_to_wav(input_audio: Path, output_wav: Path) -> None:
    _run_checked(
        ["ffmpeg", "-y", "-i", str(input_audio), str(output_wav)],
        f"convert {input_audio.name} to wav",
    )


def _materialize_demucs_outputs(out_dir: Path) -> tuple[Path, Path]:
    vocals = out_dir / "vocals.wav"
    no_vocals = out_dir / "no_vocals.wav"
    vocals_mp3 = out_dir / "vocals.mp3"
    no_vocals_mp3 = out_dir / "no_vocals.mp3"

    if not vocals.exists() and vocals_mp3.exists():
        _convert_to_wav(vocals_mp3, vocals)
    if not no_vocals.exists() and no_vocals_mp3.exists():
        _convert_to_wav(no_vocals_mp3, no_vocals)

    if not vocals.exists() or not no_vocals.exists():
        raise FileNotFoundError(f"Demucs output files not found under {out_dir}")
    return vocals, no_vocals


def _demucs_command(input_wav: Path, work_dir: Path, model: str) -> list[str]:
    return [
        "demucs",
        "--two-stems=vocals",
        "--device",
        "cpu",
        "--segment",
        str(DEMUCS_SEGMENT_SECONDS),
        "--overlap",
        str(DEMUCS_OVERLAP),
        "--shifts",
        str(DEMUCS_SHIFTS),
        "-j",
        str(DEMUCS_JOBS),
        "-n",
        model,
        "--mp3",
        "--mp3-bitrate",
        "320",
        "--mp3-preset",
        "2",
        "--out",
        str(work_dir),
        str(input_wav),
    ]


def _is_oom_error(message: str) -> bool:
    text = message.lower()
    return "rc=-9" in text or "rc=137" in text or "killed" in text or "out of memory" in text


def _run_demucs_once(input_wav: Path, work_dir: Path, model: str, env: dict[str, str]) -> tuple[Path, Path]:
    command = _demucs_command(input_wav, work_dir, model)
    result = subprocess.run(command, capture_output=True, text=True, env=env)
    out_dir = work_dir / model / input_wav.stem

    if result.returncode != 0:
        try:
            return _materialize_demucs_outputs(out_dir)
        except Exception:
            raise RuntimeError(
                f"Demucs failed (rc={result.returncode}) on {input_wav.name}: "
                f"stdout={result.stdout[-1000:]} stderr={result.stderr[-1000:]}"
            )

    return _materialize_demucs_outputs(out_dir)


def _split_wav(input_wav: Path, chunks_dir: Path, chunk_seconds: int) -> list[Path]:
    chunks_dir.mkdir(parents=True, exist_ok=True)
    pattern = chunks_dir / "chunk_%03d.wav"
    _run_checked(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(input_wav),
            "-f",
            "segment",
            "-segment_time",
            str(chunk_seconds),
            "-acodec",
            "pcm_s16le",
            str(pattern),
        ],
        "split input wav",
    )
    return sorted(chunks_dir.glob("chunk_*.wav"))


def _concat_wavs(inputs: list[Path], output_wav: Path) -> None:
    list_file = output_wav.parent / f"{output_wav.stem}_concat.txt"
    with list_file.open("w", encoding="utf-8") as f:
        for wav in inputs:
            f.write(f"file '{wav.as_posix()}'\n")
    _run_checked(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-acodec",
            "pcm_s16le",
            str(output_wav),
        ],
        f"concat wavs into {output_wav.name}",
    )


def _run_demucs_chunked(input_wav: Path, work_dir: Path, model: str, env: dict[str, str]) -> tuple[Path, Path]:
    chunk_seconds = CHUNK_SECONDS
    last_error: Exception | None = None
    attempted_chunks: set[int] = set()
    while chunk_seconds >= MIN_CHUNK_SECONDS:
        if chunk_seconds in attempted_chunks:
            break
        attempted_chunks.add(chunk_seconds)
        logger.warning("Retrying Demucs in chunked mode (%ss chunks): %s", chunk_seconds, input_wav.name)
        chunks = _split_wav(input_wav, work_dir / f"chunks_{chunk_seconds}s", chunk_seconds)
        if not chunks:
            raise RuntimeError("No chunks were created for chunked Demucs processing")

        all_vocals: list[Path] = []
        all_no_vocals: list[Path] = []
        try:
            for i, chunk in enumerate(chunks):
                logger.info("Chunked Demucs: processing %s (%d/%d)", chunk.name, i + 1, len(chunks))
                chunk_work_dir = work_dir / f"chunk_work_{chunk_seconds}s_{i:03d}"
                vocals, no_vocals = _run_demucs_once(chunk, chunk_work_dir, model, env)
                all_vocals.append(vocals)
                all_no_vocals.append(no_vocals)
        except RuntimeError as err:
            last_error = err
            if not _is_oom_error(str(err)):
                raise
            next_chunk = max(chunk_seconds // 2, MIN_CHUNK_SECONDS)
            if next_chunk == chunk_seconds:
                break
            chunk_seconds = next_chunk
            continue

        final_dir = work_dir / model / input_wav.stem
        final_dir.mkdir(parents=True, exist_ok=True)
        final_vocals = final_dir / "vocals.wav"
        final_no_vocals = final_dir / "no_vocals.wav"
        _concat_wavs(all_vocals, final_vocals)
        _concat_wavs(all_no_vocals, final_no_vocals)
        return final_vocals, final_no_vocals

    raise RuntimeError(f"Chunked Demucs failed for {input_wav.name}: {last_error}")


def separate_vocals_demucs(
    input_wav: Path,
    work_dir: Path,
    model: str = "htdemucs",
) -> tuple[Path, Path]:
    work_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["TORCHAUDIO_USE_SOUNDFILE"] = "1"
    env.setdefault("OMP_NUM_THREADS", "1")
    env.setdefault("MKL_NUM_THREADS", "1")
    fallback_models = [model, "mdx_q", "mdx_extra_q", "mdx_extra"]
    unique_models = list(dict.fromkeys(fallback_models))
    logger.info("Starting Demucs separation with models=%s", unique_models)

    last_error: Exception | None = None
    for candidate_model in unique_models:
        try:
            vocals, no_vocals = _run_demucs_once(input_wav, work_dir, candidate_model, env)
            logger.info("Demucs succeeded with model=%s", candidate_model)
            break
        except RuntimeError as err:
            last_error = err
            if _is_oom_error(str(err)):
                logger.warning("Demucs OOM with model=%s. Trying chunked/fallback.", candidate_model)
                try:
                    vocals, no_vocals = _run_demucs_chunked(input_wav, work_dir, candidate_model, env)
                    logger.info("Chunked Demucs succeeded with model=%s", candidate_model)
                    break
                except RuntimeError as chunk_err:
                    last_error = chunk_err
                    if not _is_oom_error(str(chunk_err)):
                        raise
                    continue
            continue
    else:
        raise RuntimeError(
            f"All Demucs model attempts failed for {input_wav.name}. "
            f"Last error: {last_error}"
        )

    logger.info("Demucs separation completed: vocals=%s no_vocals=%s", vocals, no_vocals)
    return vocals, no_vocals
