import os
import subprocess
from pathlib import Path

from opt.logging_setup import setup_logging

logger = setup_logging(__name__)


def separate_vocals_demucs(
    input_wav: Path,
    work_dir: Path,
    model: str = "htdemucs",
) -> tuple[Path, Path]:
    work_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    # Force torchaudio to use soundfile backend to avoid torchcodec requirement.
    env["TORCHAUDIO_USE_SOUNDFILE"] = "1"
    command = [
        "demucs",
        "--two-stems=vocals",
        "-n",
        model,
        "--out",
        str(work_dir),
        str(input_wav),
    ]
    logger.info("Starting Demucs separation with model=%s", model)
    result = subprocess.run(command, capture_output=True, text=True, env=env)
    out_dir = work_dir / model / input_wav.stem
    vocals = out_dir / "vocals.wav"
    no_vocals = out_dir / "no_vocals.wav"
    if result.returncode != 0:
        # Some environments emit OpenBLAS warnings on stderr; keep going if outputs exist.
        if vocals.exists() and no_vocals.exists():
            logger.warning("Demucs exited with code %s but outputs exist. stderr=%s", result.returncode, result.stderr.strip())
        else:
            logger.error("Demucs failed: %s", result.stderr.strip())
            raise RuntimeError(f"Demucs failed: {result.stderr}")

    logger.debug("Demucs output: %s", result.stdout.strip())
    if not vocals.exists() or not no_vocals.exists():
        raise FileNotFoundError("Demucs output files not found")
    logger.info("Demucs separation completed: vocals=%s no_vocals=%s", vocals, no_vocals)
    return vocals, no_vocals
