import numpy as np
from scipy.signal import butter, sosfiltfilt


def as_float(x) -> np.ndarray:
    """Convierte cualquier arreglo o entrada numérica en un arreglo de NumPy tipo float."""
    return np.asarray(x, dtype=float)


def _filter_signal(x, fs: float, sos: np.ndarray) -> np.ndarray:
    if not np.isfinite(fs) or fs <= 0:
        raise ValueError("fs debe ser un numero positivo (Hz).")
    a = as_float(x)
    if a.ndim != 1:
        raise ValueError("La senal debe ser un arreglo unidimensional.")
    if len(a) == 0 or not np.all(np.isfinite(a)):
        raise ValueError("La senal debe ser no vacia y contener solo valores finitos.")
    min_len = 3 * (2 * len(sos) + 1)
    if len(a) <= min_len:
        raise ValueError(
            f"La senal es demasiado corta para filtfilt; se requieren mas de {min_len} muestras."
        )
    try:
        return sosfiltfilt(sos, a)
    except ValueError as exc:
        raise ValueError(f"No se pudo filtrar la senal: {exc}") from exc


def remove_dc(x: np.ndarray) -> np.ndarray:
    """Elimina la componente de corriente directa (DC), centrando la señal en cero restando su media."""
    x = as_float(x)
    if x.ndim != 1 or len(x) == 0 or not np.all(np.isfinite(x)):
        raise ValueError("La senal debe ser no vacia, unidimensional y finita.")
    return x - np.mean(x)


def bandpass_emg(
    x: np.ndarray, fs: float, low_hz: float, high_hz: float, order: int = 4
) -> np.ndarray:
    """Aplica un filtro pasabanda para conservar únicamente las frecuencias fisiológicas útiles del EMG."""
    if not 0 < low_hz < high_hz < fs / 2:
        raise ValueError("Debe cumplirse 0 < low_hz < high_hz < fs/2.")
    if not np.isfinite(fs) or fs <= 0:
        raise ValueError("fs debe ser un numero positivo (Hz).")
    sos = butter(order, [low_hz, high_hz], btype="bandpass", fs=fs, output="sos")
    return _filter_signal(x, fs, sos)


def notch_filter(
    x: np.ndarray,
    fs: float,
    center_hz: float = 60.0,
    bandwidth_hz: float = 2.0,
    order: int = 2,
) -> np.ndarray:
    """Aplica un filtro rechazabanda (Notch) para eliminar interferencias eléctricas específicas, como el ruido de la red de corriente (50/60 Hz)."""
    low = center_hz - bandwidth_hz / 2
    high = center_hz + bandwidth_hz / 2
    if not 0 < low < high < fs / 2:
        raise ValueError("La banda notch debe estar dentro de (0, fs/2).")
    if bandwidth_hz <= 0:
        raise ValueError("bandwidth_hz debe ser positivo.")
    if not np.isfinite(fs) or fs <= 0:
        raise ValueError("fs debe ser un numero positivo (Hz).")
    sos = butter(order, [low, high], btype="bandstop", fs=fs, output="sos")
    return _filter_signal(x, fs, sos)


def rectify(x: np.ndarray) -> np.ndarray:
    """Rectifica la señal convirtiendo todos sus valores en amplitudes absolutas (positivas)."""
    return np.abs(as_float(x))


def lowpass_envelope(
    x_rectified: np.ndarray, fs: float, cutoff_hz: float, order: int = 4
) -> np.ndarray:
    """Aplica un filtro pasabajos sobre la señal rectificada para extraer la envolvente lineal que define el perfil de contracción muscular."""
    if not 0 < cutoff_hz < fs / 2:
        raise ValueError("cutoff_hz debe estar entre 0 y fs/2.")
    if not np.isfinite(fs) or fs <= 0:
        raise ValueError("fs debe ser un numero positivo (Hz).")
    sos = butter(order, cutoff_hz, btype="lowpass", fs=fs, output="sos")
    return _filter_signal(x_rectified, fs, sos)


def preprocess_emg(
    x: np.ndarray,
    fs: float,
    low_hz: float = 20.0,
    high_hz: float = 450.0,
    envelope_hz: float = 5.0,
    use_notch: bool = False,
    notch_hz: float = 60.0,
) -> dict[str, np.ndarray]:
    """Return all stages so the dashboard can expose processing provenance."""
    raw = as_float(x)
    dc_removed = remove_dc(raw)
    filtered = bandpass_emg(dc_removed, fs, low_hz, high_hz)
    if use_notch:
        filtered = notch_filter(filtered, fs, notch_hz)
    rectified = rectify(filtered)
    envelope = lowpass_envelope(rectified, fs, envelope_hz)
    return {
        "raw": raw,
        "dc_removed": dc_removed,
        "filtered": filtered,
        "rectified": rectified,
        "envelope": envelope,
    }
