"""
Hadamard Time
=============

On a given system and hardware configuration, times Hadamard product for
increasing mesh grid sizes.

"""
import jax
jax.config.update("jax_enable_x64", True)
import os
import sys
import timeit
import math
import jax.numpy as jnp
sys.path.insert(0, os.path.abspath('../..'))  # Adds project root to the PATH

import numpy as np
import torch
from scipy.stats import median_abs_deviation as mad
from tqdm import tqdm

from spinor_gpe.pspinor import pspinor as spin
from spinor_gpe.pspinor import tensor_tools as ttools

# torch.cuda.empty_cache()


def closestDivisors(n):
    """Return the two largest divisors that are closest together."""
    b = round(math.sqrt(n))
    while n % b > 0:
        b -= 1
    return b, n // b


closest = np.vectorize(closestDivisors)

a = np.logspace(12, 24, 25, base=2.0, dtype=int)
# print(a)
# print(closest(a))
close = closest(a)
grids = [(a, b) for a, b in zip(close[0], close[1])]


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

ps = spin.PSpinor(DATA_PATH, overwrite=True,
                  atom_num=ATOM_NUM, omeg=OMEG, g_sc=G_SC,
                  pop_frac=(0.5, 0.5), r_sizes=(8, 8),
                  mesh_points=grids[0])
@jax.jit
def jaxxed_had(op,psi):
    x = [o * p for o, p in zip(op, psi)]
    return x
for i, grid in tqdm(enumerate(grids)):
    print(f'{i}/{len(grids)}')
    try:
        psi = ([jnp.array(torch.rand(grid, dtype=torch.complex128)),
               jnp.array(torch.rand(grid, dtype=torch.complex128))])
        op = ([jnp.array(torch.rand(grid, dtype=torch.float64)),
              jnp.array(torch.rand(grid, dtype=torch.float64))])
        _ = jaxxed_had(psi,op)
        stmt = """jaxxed_had(psi,op)[-1].block_until_ready()"""

        timer = timeit.Timer(stmt=stmt, globals=globals())

        N = timer.autorange()[0]
        if N < 10:
            N *= 10
        vals = timer.repeat(N, 1)
        meas_times[i] = vals
        repeats[i] = N
        size[i] = np.log2(np.prod(grid))
        del timer
        del stmt
        del psi
        del op
        torch.cuda.empty_cache()
    except RuntimeError as ex:
        print(ex)
        break

median = np.array([np.median(times) for times in meas_times])
med_ab_dev = np.array([mad(times, scale='normal') for times in meas_times])

tag = COMPUTER + '_' + DEVICE + '_had'
np.savez('data/' + tag, computer=COMPUTER, device=DEVICE,
         size=size, n_repeats=repeats, med=median, mad=med_ab_dev)

SAVE = 'benchmarks/'  # Default data path is in the /data/ folder

np.save(SAVE + tag, np.array(meas_times, dtype='object'))
