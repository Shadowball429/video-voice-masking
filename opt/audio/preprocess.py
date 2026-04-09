from pathlib import Path
from typing import Tuple

import numpy as np
import soundfile as sf
import torch
import torchaudio

from opt.logging_setup import setup_logging

logger = setup_logging(__name__)

AudioTuple = Tuple[np.ndarray, int]


def load_audio(path: Path, target_sr: int = 48000) -> AudioTuple:
    data, sr = sf.read(path, dtype="float32", always_2d=True)
    logger.debug("Loaded audio %s with shape %s @ %s Hz", path, data.shape, sr)
    if sr != target_sr:
        tensor = torch.from_numpy(data.T)
        resampled = torchaudio.functional.resample(tensor, sr, target_sr)
        data = resampled.T.numpy()
        sr = target_sr
        logger.debug("Resampled to %s Hz", target_sr)
    return data, sr


def write_audio(path: Path, audio: np.ndarray, sample_rate: int) -> None:
    sf.write(path, audio, sample_rate)
    logger.debug("Wrote audio %s shape %s @ %s Hz", path, audio.shape, sample_rate)


def peak_normalize(audio: np.ndarray, peak_db: float = -1.0) -> np.ndarray:
    peak = float(np.max(np.abs(audio)))
    if peak == 0:
        return audio
    target = 10 ** (peak_db / 20)
    audio *= target / peak
    return audio
