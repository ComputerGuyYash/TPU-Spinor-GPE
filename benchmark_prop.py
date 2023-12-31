"""
Propagation Time
================

For a given system and hardware configuration (CPU or GPU), this script
generates `PSpinor` objects of increasing mesh grid size in a for-loop,
starting from (64, 64) up to (4096, 4096), or until the memory limit is
reached. After generating the `PSpinor`, it performs a brief propagation
in imaginary time, returning a `TensorPropagator` object `prop`. The script
then measures the time for a single function call of `prop.full_step()`, and
repeats that N times. With the measured times for each grid size, saves the
median and median absolute deviation.

"""
import os
import sys
import timeit

import numpy as np
import torch
from scipy.stats import median_abs_deviation as mad

sys.path.insert(0, os.path.abspath('../../..'))  # Adds project root to PATH

from spinor_gpe.pspinor import pspinor as spin

torch.cuda.empty_cache()
grids = [(64, 64),
         (64, 128),
         (128, 128),
         (128, 256),
         (256, 256),
         (256, 512),
         (512, 512),
         (512, 1024),
         (1024, 1024),
         (1024, 2048),
         (2048, 2048),
         (2048, 4096),
         (4096, 4096)]
# grids = [grids[0]]
n_grids = len(grids)
meas_times = [[0] for i in range(n_grids)]
repeats = np.zeros(n_grids)
size = np.zeros(n_grids)


DATA_PATH = 'benchmarks/Bench_001'  # Default data path is in the /data/ folder

W = 2 * np.pi * 50
ATOM_NUM = 1e2
OMEG = {'x': W, 'y': W, 'z': 40 * W}
G_SC = {'uu': 1, 'dd': 1, 'ud': 1.04}

DEVICE = 'jax'
COMPUTER = 'Kaggle'

for i, grid in enumerate(grids):
    print(i)
    try:
        # Create a PSpinor object
        ps = spin.PSpinor(DATA_PATH, overwrite=True,
                          atom_num=ATOM_NUM, omeg=OMEG, g_sc=G_SC,
                          pop_frac=(0.5, 0.5), r_sizes=(8, 8),
                          mesh_points=grid)
        ps.coupling_setup(wavel=790.1e-9, kin_shift=False)
        res, prop = ps.imaginary(1/50, 1, DEVICE, is_sampling=False)
        _ = prop.full_step(prop.psik)[-1].block_until_ready()
        stmt = """prop.full_step(prop.psik)[-1].block_until_ready()"""  # A full time step function call.

        # Create a code timing object.
        timer = timeit.Timer(stmt=stmt, globals=globals())

        # Estimate the number of timing repetitions to make
        N = timer.autorange()[0]
        if N < 10:
            N *= 10

        vals = timer.repeat(N, 1)  # Time and repeat N times.

        # Save timing values.
        meas_times[i] = vals
        repeats[i] = N
        size[i] = np.log2(np.prod(grid))
        del timer
        del stmt
        del res
        del prop
        del ps
        torch.cuda.empty_cache()
    except RuntimeError as ex:
        print(ex)
        break

median = np.array([np.median(times) for times in meas_times])
med_ab_dev = np.array([mad(times, scale='normal') for times in meas_times])

tag = COMPUTER + '_' + DEVICE+ '_prop'
np.savez('data/' + tag, computer=COMPUTER, device=DEVICE,
         size=size, n_repeats=repeats, med=median, mad=med_ab_dev)
SAVE = 'benchmarks/'  # Default data path is in the /data/ folder

np.save(SAVE + tag, np.array(meas_times, dtype='object'))
