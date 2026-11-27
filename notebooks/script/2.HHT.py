#!/usr/bin/env python
# coding: utf-8

get_ipython().run_line_magic('reload_ext', 'autoreload')
get_ipython().run_line_magic('autoreload', '2')


# # Hilbert Huang Transform

import ast
import logging
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import wfdb
import yaml
from PyEMD import EMD

from ekg.config import load_config, setup
from ekg.const import CLASSES

logger = logging.getLogger(__name__)
setup()
cfg = load_config("config.yml")

PATH = cfg["paths"]["raw_data"]
PATH_PROCESSED = cfg["paths"]["processed_data"]
SAMPLING_RATE = cfg["data"]["sampling_rate"]

logger.debug("config: %s", cfg)


# make sure to run `python scripts/clean_dataset.py`
Y = pd.read_pickle(PATH_PROCESSED / "metadata.pkl")
labels = pd.read_csv(PATH_PROCESSED / "labels.csv", index_col="ecg_id")
X = np.load(PATH_PROCESSED / "X.npy")


# # Split data into train and test
# test_fold = cfg['data']['test_fold']
# # Train
# X_train = X[np.where(Y['strat_fold'] != test_fold)]
# y_train = Y[(Y['strat_fold'] != test_fold)]['diagnostic_superclass']
# # Test
# X_test = X[np.where(Y['strat_fold'] == test_fold)]
# y_test = Y[Y['strat_fold'] == test_fold]['diagnostic_superclass']


lead_idx = 1  # 0=I, 1=II, ... (II shows P-QRS-T clearly)
signal = X[0][:, lead_idx]  # (1000,) — 10 s of one lead
t = np.arange(len(signal)) / SAMPLING_RATE

emd = EMD()
IMFs = emd(signal)

# plot the wave
plt.figure(figsize=(10, 3))
plt.plot(t, signal)
plt.xlabel("Time [s]")
plt.ylabel("Voltage [mV]")
# plt.title(f"ECG Signal (lead II) — ecg_id {ecg_id}")
plt.show()

# plot the first 5 IMFs
n = min(5, len(IMFs))
fig, axes = plt.subplots(n, 1, figsize=(10, 2.5 * n), sharex=True)
for i, ax in enumerate(axes):
    ax.plot(t, IMFs[i])
    ax.set_title(f"IMF {i + 1}")
axes[-1].set_xlabel("Time [s]")
plt.tight_layout()
plt.show()


# ### HHT

# Compute the one-dimensional discrete Fourier Transform
# Then shift it
fft_signal = np.fft.fft(signal)
signal_shifted = np.fft.fftshift(fft_signal)

n_rows = 4
fig, axes = plt.subplots(n_rows, 1, figsize=(10, 2.5 * n_rows))

axes[0].plot(t, signal)
axes[0].set_title(f"Raw signal")
axes[0].set_xlabel("Time, s")

axes[1].plot(t, fft_signal)
axes[1].set_title("FFT signal")
axes[1].set_xlabel("Time, s")

axes[2].plot(t, signal_shifted)
axes[2].set_title("Shifted FFT signal")
axes[2].set_xlabel("Time, s")

axes[3].plot(
    np.linspace(-0.5, 0.5, signal_shifted.shape[0]), np.abs(signal_shifted) ** 2
)
axes[3].set_xlabel("Normalized Frequency")
axes[3].set_title("Energy Spectrum")

plt.tight_layout()
plt.show()


# baseline wander
from ekg.signal import highpass

fixed_signal = highpass(signal, fs=SAMPLING_RATE)
fig, axes = plt.subplots(2, 1, figsize=(10, 2.5 * 2))

axes[0].plot(t, signal)
axes[0].set_title(f"Raw signal")
axes[0].set_xlabel("Time, s")

axes[1].plot(t, fixed_signal)
axes[1].set_title("Fixed")
axes[1].set_xlabel("Time, s")

plt.tight_layout()
plt.show()


emd = EMD()
IMFs = emd(fixed_signal)

# plot the wave
plt.figure(figsize=(10, 3))
plt.plot(t, fixed_signal)
plt.xlabel("Time [s]")
plt.ylabel("Voltage [mV]")
# plt.title(f"ECG Signal (lead II) — ecg_id {ecg_id}")
plt.show()

# plot the first 5 IMFs
n = min(5, len(IMFs))
fig, axes = plt.subplots(n, 1, figsize=(10, 2.5 * n), sharex=True)
for i, ax in enumerate(axes):
    ax.plot(t, IMFs[i])
    ax.set_title(f"IMF {i + 1}")
axes[-1].set_xlabel("Time [s]")
plt.tight_layout()
plt.show()

