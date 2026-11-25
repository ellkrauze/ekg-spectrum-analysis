import logging

import neurokit2 as nk
import numpy as np
import pandas as pd
from PyEMD import EMD
from scipy.signal import butter, hilbert, sosfiltfilt

from ekg.const import LEADS, SEED

logger = logging.getLogger(__name__)


def hht(signal, fs, emd):
    """EMD + Hilbert -> instantaneous frequency [Hz] and amplitude of every
    IMF."""
    imfs = emd(signal)  # (n_imfs, n_samples)
    analytic = hilbert(imfs, axis=1)
    amp = np.abs(analytic)[:, 1:]
    phase = np.unwrap(np.angle(analytic), axis=1)
    freq = np.diff(phase, axis=1) / (2 * np.pi) * fs  # one sample shorter
    return imfs, freq, amp


def hilbert_spectrum(signal, fs, emd, freq_bins):
    """HHT marginal spectrum: energy per frequency bin, summed over time."""
    _, freq, amp = hht(signal, fs, emd)
    valid = (freq > 0) & (freq < fs / 2)
    h, _ = np.histogram(freq[valid], bins=freq_bins, weights=amp[valid] ** 2)
    return h


def highpass(sig, fs, cutoff=0.5, order=4):
    """Remove baseline wander below `cutoff` Hz."""
    sos = butter(order, cutoff, btype="highpass", fs=fs, output="sos")
    return sosfiltfilt(sos, sig, axis=0)


def pick_records(
    labels, classes, n: int = 50, single: bool = True, seed: int = None
):
    """Random sample of ecg_ids per class.

    single=True keeps only records with exactly one superclass, so e.g. an [MI,
    CD] record does not blur both classes. Returns {class: array of ecg_ids}.

    """
    if seed is None:
        seed = SEED

    mask_single = labels[classes].sum(axis=1) == 1
    picks = {}
    for class_name in classes:
        ids = labels.index[
            (labels[class_name] == 1) & (mask_single if single else True)
        ]
        picks[class_name] = (
            pd.Series(ids)
            .sample(min(n, len(ids)), random_state=seed)
            .to_numpy()
        )
    return picks


def signal_stats(X, Y, picks, fs):
    """Per-record, per-lead amplitude stats + heart rate (lead II).

    Returns a long DataFrame: ecg_id, cls, lead, ptp [mV], rms [mV], hr [bpm].

    """
    if fs <= 0:
        raise ValueError("Frequency cannot be negative or equal to zero")

    rows = []
    for cls, ids in picks.items():
        for ecg_id in ids:
            rec = highpass(X[Y.index.get_loc(ecg_id)], fs)  # (T, 12)

            cleaned = nk.ecg_clean(
                rec[:, 1], sampling_rate=fs, method="neurokit"
            )
            # get the samples at which R-peaks occur in EKG signal
            _, rpeaks_info = nk.ecg_peaks(cleaned, sampling_rate=fs)
            rr_intervals = np.diff(rpeaks_info["ECG_R_Peaks"]) / fs
            heart_rate = (
                60 / np.median(rr_intervals) if len(rr_intervals) else np.nan
            )

            for k, lead in enumerate(LEADS):
                rows.append(
                    dict(
                        ecg_id=ecg_id,
                        cls=cls,
                        lead=lead,
                        ptp=np.ptp(rec[:, k]),
                        rms=np.sqrt(np.mean(rec[:, k] ** 2)),
                        hr=heart_rate,
                    )
                )
    df = pd.DataFrame(rows)
    df["cls"] = pd.Categorical(df["cls"], categories=list(picks))
    df["lead"] = pd.Categorical(df["lead"], categories=LEADS)
    return df


def class_spectra(
    X, Y, picks, fs, freq_bins, crop=(100, 900), normalize=True, verbose=True
):
    """Marginal spectra for every picked record and lead.

    crop       - drop samples near the edges (EMD / filter edge effects)
    normalize  - divide each spectrum by its total energy, so classes are
                 compared by spectral SHAPE, not by signal amplitude
    Returns {class: array (n_records, 12, n_bins)}.

    """
    emd = EMD()
    a, b = crop
    out = {}
    for cls, ids in picks.items():
        specs = np.zeros((len(ids), len(LEADS), len(freq_bins) - 1))
        for i, ecg_id in enumerate(ids):
            rec = highpass(X[Y.index.get_loc(ecg_id)], fs)[a:b]
            for k in range(len(LEADS)):
                h = hilbert_spectrum(rec[:, k], fs, emd, freq_bins)
                specs[i, k] = h / h.sum() if normalize and h.sum() > 0 else h
        out[cls] = specs
        if verbose:
            logger.debug(f"{cls}: {len(ids)} records done")
    return out


def summarize_spectra(spectra):
    """Median and inter-quartile range across records -> 'typical' spectrum.

    Returns {class: (median, q25, q75)}, each array (12, n_bins).

    """
    return {
        cls: (
            np.median(s, axis=0),
            np.percentile(s, 25, axis=0),
            np.percentile(s, 75, axis=0),
        )
        for cls, s in spectra.items()
    }
