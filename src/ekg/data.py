import os

import numpy as np
import wfdb


def load_raw_data(df, sampling_rate, path):
    if not os.path.exists(path):
        raise FileNotFoundError("Provided dataset path does not exist")
    df_col = "filename_lr" if sampling_rate == 100 else "filename_hr"

    # translate to mV
    data = [wfdb.rdsamp(path / filename) for filename in df[df_col]]

    # meta: {'fs': 100, 'sig_len': 1000, 'n_sig': 12, 'units': ['mV', ...],
    #   'sig_name': ['I','II','III','AVR','AVL','AVF','V1',...,'V6']}
    data = np.array([signal for signal, meta in data])
    return data
