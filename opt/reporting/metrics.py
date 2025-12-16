import numpy as np
import webrtcvad

from opt.logging_setup import setup_logging

logger = setup_logging(__name__)


def vad_speech_ratio(audio: np.ndarray, sample_rate: int, frame_ms: int = 30) -> float:
    vad = webrtcvad.Vad(2)
    frame_length = int(sample_rate * frame_ms / 1000)
    if frame_length <= 0 or audio.shape[0] < frame_length:
        return 0.0

    audio_mono = audio if audio.ndim == 1 else audio.mean(axis=1)
    pcm = np.clip(audio_mono, -1.0, 1.0)
    int16_audio = (pcm * 32767).astype(np.int16).tobytes()

    voiced = 0
    total = 0
    for start in range(0, len(int16_audio), frame_length * 2):
        frame = int16_audio[start : start + frame_length * 2]
        if len(frame) < frame_length * 2:
            break
        if vad.is_speech(frame, sample_rate):
            voiced += 1
        total += 1

    ratio = voiced / total if total else 0.0
    logger.debug("Estimated VAD speech ratio: %.3f", ratio)
    return ratio
