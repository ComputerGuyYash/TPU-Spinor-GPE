"""tensor_tools.py module."""
import operator
from functools import reduce
import jax.numpy as jnp
import numpy as np
import torch
from skimage import restoration as rest
import jax

jax.config.update("jax_enable_x64", True)
# ??? How should the individual FFT operations be normalized? Should they
# remain as norm="backward", or, because of the nature of our operations,
# changed to norm="ortho"?


def to_numpy(input_tens):
    """Convert from PyTorch Tensor to NumPy arrays.

    Accepts a single PyTorch Tensor, or a :obj:`list` of PyTorch Tensor,
    as in the wavefunction objects.

    Parameters
    ----------
    input_tens : PyTorch :obj:`Tensor`, or :obj:`list` of PyTorch :obj:`Tensor`
        Input tensor, or list of tensor, to be converted to :obj:`array`,
        on CPU memory.

    Returns
    -------
    output_arr : NumPy :obj:`array` or :obj:`list` of NumPy :obj:`array`
        Output array stored on CPU memory.

    """
    # if isinstance(input_tens, list):
    #     output_tens = [inp for inp in input_tens]

    # elif isinstance(input_tens, torch.Tensor):
    #     output_tens = input_tens.cpu().numpy()

    return input_tens


def to_tensor(input_arr, dev='cpu', dtype=64):
    """Convert from NumPy arrays to Tensors.

    Accepts a single NumPy array, or a :obj:`list` of NumPy arrays, as in the
    wavefunction objects.

    Parameters
    ----------
    input_arr : NumPy :obj:`array`,  or :obj:`list` of NumPy :obj:`array`
        Input array, or list of arrays, to be converted to a :obj:`Tensor`,
        on either CPU or GPU memory.
    dev : :obj:`str`, default='cpu'
        The name of the device on which to store the tensor,
        e.g. {'cpu', 'cuda', 'cuda:0'}
    dtype : :obj:`int`, default=64
        Designator for the torch dtype -

        * 32  : :obj:`torch.float32`;
        * 64  : :obj:`torch.float64`;
        * 128 : :obj:`torch.complex128`

    Returns
    -------
    output_tens : PyTorch :obj:`Tensor` or :obj:`list` of PyTorch :obj:`Tensor`
        Output tensor of `dtype` stored on `dev` memory.

    """
    all_dtypes = {32: jnp.float32, 64: jnp.float64, 128: jnp.complex128}
    if isinstance(input_arr, list):
        output_tens = [jnp.asarray(inp, dtype=all_dtypes[dtype]) for inp in input_arr]

    elif isinstance(input_arr, np.ndarray):
        output_tens = jnp.asarray(input_arr, dtype=all_dtypes[dtype])

    return output_tens


def to_cpu(input_tens):
    """Transfers `input_tens` from GPU to CPU memory.

    Parameters
    ----------
    input_tens : PyTorch :obj:`Tensor` or :obj:`list` of PyTorch :obj:`Tensor`
        Input tensor stored on GPU memory.

    Returns
    -------
    output_tens : PyTorch :obj:`Tensor` or :obj:`list` of PyTorch :obj:`Tensor`
        Output tensor stored on CPU memory.

    """
    if isinstance(input_tens, list):
        output_tens = [inp.cpu() for inp in input_tens]

    elif isinstance(input_tens, torch.Tensor):
        output_tens = input_tens.cpu()

    return output_tens


def to_gpu(input_tens, dev='cuda'):
    """Transfers `input_tens` from CPU to GPU memory.

    Parameters
    ----------
    input_tens : PyTorch :obj:`Tensor` or :obj:`list` of PyTorch :obj:`Tensor`
        Input tensor stored on GPU memory.
    dev : :obj:`str`, default='cuda'
        The name of the device on which to store the tensor,
        e.g. {'cuda', 'cuda:0'}

    Returns
    -------
    output_tens : PyTorch :obj:`Tensor` or :obj:`list` of PyTorch :obj:`Tensor`

    """
    if isinstance(input_tens, list):
        assert isinstance(input_tens[0], torch.Tensor), f"Cannot move a \
            non-Tensor object of dtype `{type(input_tens[0])}` to GPU memory."
        output_tens = [inp.to(dev) for inp in input_tens]

    elif isinstance(input_tens.to(dev), torch.Tensor):
        output_tens = input_tens

    return output_tens


def fft_1d(psi, delta_r=(1, 1), axis=0) -> list:
    """Compute the forward 1D FFT of `psi` along a single axis.

    Parameters
    ----------
    psi : :obj:`list` of NumPy :obj:`array` or PyTorch :obj:`Tensor`
        The input wavefunction.
    delta_r : NumPy :obj:`array`, default=(1,1)
        A two-element list of the real-sapce x- and y-mesh spacings,
        respectively.
    axis : :obj:`int`, default=0
        The axis along which to transform; note that 0 -> y-axis, and
        1 -> x-axis.

    Returns
    -------
    psik_axis : :obj:`list` of NumPy :obj:`array` or PyTorch :obj:`Tensor`
        The FFT of psi along `axis`.

    """
    true_ax = [1, 0]
    normalization = delta_r[axis] / np.sqrt(2 * np.pi)

    if isinstance(psi[0], np.ndarray):
        psik_axis = [np.fft.fftn(p, axes=[true_ax[axis]]) * normalization
                     for p in psi]
        psik_axis = [np.fft.fftshift(pk, axes=true_ax[axis])
                     for pk in psik_axis]
    elif isinstance(psi[0], torch.Tensor):
        psik_axis = [torch.fft.fftn(p, dim=[true_ax[axis]]) * normalization
                     for p in psi]
        psik_axis = [torch.fft.fftshift(pk, dim=true_ax[axis])
                     for pk in psik_axis]

    return psik_axis


def ifft_1d(psik, delta_r=(1, 1), axis=0) -> list:
    """Compute the inverse 1D FFT of `psi` along a single axis.

    Parameters
    ----------
    psik : :obj:`list` of NumPy :obj:`array` or PyTorch :obj:`Tensor`
        The input wavefunction.
    delta_r : NumPy :obj:`array`, default=(1,1)
        A two-element list of the real-sapce x- and y-mesh spacings,
        respectively.
    axis : :obj:`int`, default=0
        The axis along which to transform; note that 0 -> x-axis, and
        1 -> y-axis.

    Returns
    -------
    psi_axis : :obj:`list` of NumPy :obj:`array` or PyTorch :obj:`Tensor`
        The FFT of psi along `axis`.

    """
    true_ax = [1, 0]  # Makes the x/y axes correspond to 0/1
    normalization = delta_r[axis] / np.sqrt(2 * np.pi)
    if isinstance(psik[0], np.ndarray):
        psi_axis = [np.fft.ifftshift(pk, axes=true_ax[axis]) for pk in psik]
        psi_axis = [np.fft.ifftn(p, axes=[true_ax[axis]]) / normalization
                    for p in psi_axis]
    elif isinstance(psik[0], torch.Tensor):
        psi_axis = [torch.fft.ifftshift(pk, dim=true_ax[axis]) for pk in psik]
        psi_axis = [torch.fft.ifftn(p, dim=true_ax[axis]) / normalization
                    for p in psi_axis]

    return psi_axis

@jax.jit
def fft_2d(psi, delta_r=(1, 1)) -> list:
    print("Recompiling fft2d")
    """Compute the forward 2D FFT of `psi`.

    Parameters
    ----------
    psi : :obj:`list` of NumPy :obj:`array` or PyTorch :obj:`Tensor`
        The input wavefunction.
    delta_r : NumPy :obj:`array`, default=(1,1)
        A two-element list of the real-space x- and y-mesh spacings,
        respectively. Typically, use `ps.space['dr']`.

    Returns
    -------
    psik : :obj:`list` of NumPy :obj:`array` or PyTorch :obj:`Tensor`
        The k-space FFT of the input wavefunction.

    """

    if isinstance(psi[0], np.ndarray):
        normalization = prod(delta_r) / (2 * np.pi)  #: FFT normalization factor
        psik = [np.fft.fftn(p) * normalization for p in psi]
        psik = [np.fft.fftshift(pk) for pk in psik]

    elif isinstance(psi[0], torch.Tensor):
        normalization = prod(delta_r) / (2 * np.pi)  #: FFT normalization factor
        psik = [torch.fft.fftn(p) * normalization for p in psi]
        psik = [torch.fft.fftshift(pk) for pk in psik]
    else:
        normalization = (delta_r[0]*delta_r[1]) / (2 * jnp.pi)  #: FFT normalization factor
        psik = [jnp.fft.fftn(p) * normalization for p in psi]
        psik = [jnp.fft.fftshift(pk) for pk in psik]

        return list(psi)
    return psik

@jax.jit
def ifft_2d(psik, delta_r=(1, 1)) -> list:
    print("Recompiling ifft2d")

    """Compute the inverse 2D FFT of `psik`.

    Parameters
    ----------
    psik : :obj:`list` of NumPy :obj:`array` or PyTorch :obj:`Tensor`
        The input wavefunction.
    delta_r : NumPy :obj:`array`, default=(1,1)
        A two-element list of the real-sapce x- and y-mesh spacings,
        respectively. Typically, use `ps.space['dr']`.

    Returns
    -------
    psi : :obj:`list` of NumPy :obj:`array` or PyTorch :obj:`Tensor`
        The real-space FFT of the input wavefunction.

    """

    if isinstance(psik[0], np.ndarray):
        normalization = prod(delta_r) / (2 * np.pi)  #: FFT normalization factor
        psik = [np.fft.ifftshift(pk) for pk in psik]
        psi = [np.fft.ifftn(p) / normalization for p in psik]

    elif isinstance(psik[0], torch.Tensor):
        normalization = prod(delta_r) / (2 * np.pi)  #: FFT normalization factor
        psik = [torch.fft.ifftshift(pk) for pk in psik]
        psi = [torch.fft.ifftn(p) / normalization for p in psik]
    else:
        normalization = (delta_r[0]*delta_r[1]) / (2 * jnp.pi)  #: FFT normalization factor
        psik = [jnp.fft.ifftshift(pk) for pk in psik]
        psi = [jnp.fft.ifftn(p) / normalization for p in psik]

        return psi
    return psi


def norm(psi, vol_elem, atom_num, pop_frac=None):
    """
    Normalize spinor wavefunction to the expected atom numbers and populations.

    This function normalizes to the total expected atom number `atom_num`,
    and to the expected population fractions `pop_frac`. Normalization is
    essential in processes where the total atom number is not conserved,
    (e.g. imaginary time propagation).

    Parameters
    ----------
    psi : :obj:`list` of NumPy :obj:`arrays` or PyTorch :obj:`Tensors`.
        The wavefunction to normalize.
    vol_elem : :obj:`float`
        Volume element for either real- or k-space.
    atom_num : :obj:`int`
        The total expected atom number.
    pop_frac : array-like, optional
        The expected population fractions in each spin component.

    Returns
    -------
    psi_norm : :obj:`list` of NumPy :obj:`arrays` or PyTorch :obj:`Tensors`.
        The normalized wavefunction.
    dens_norm : :obj:`list` of NumPy :obj:`arrays` or PyTorch :obj:`Tensors`.
        The densities of the normalized wavefunction's components

    """
    dens = density(psi)
    if isinstance(dens[0], np.ndarray):
        if pop_frac is None:
            norm_factor = np.sum(dens[0] + dens[1]) * vol_elem / atom_num
            psi_norm = [p / np.sqrt(norm_factor) for p in psi]
            dens_norm = [d / norm_factor for d in dens]
        else:
            # TODO: Implement population fraction normalization.
            raise NotImplementedError("Normalizing to the expected population "
                                      "fractions is not yet implemented for "
                                      "NumPy arrays.")

    elif isinstance(dens[0], torch.Tensor):
        if pop_frac is None:
            norm_factor = torch.sum(dens[0] + dens[1]) * vol_elem / atom_num
            psi_norm = [p / np.sqrt(norm_factor.item()) for p in psi]
            dens_norm = [d / norm_factor.item() for d in dens]
        else:
            raise NotImplementedError("Normalizing to the expected population "
                                      "fractions is not implemented for "
                                      "PyTorch tensors.")
    else:
        norm_factor = jnp.sum(dens[0] + dens[1]) * vol_elem / atom_num
        # psi_norm = [psi[0]/jnp.sqrt(norm_factor),psi[1]/jnp.sqrt(norm_factor)]
        psi_norm = []
        for p in psi:
            # print(p/jnp.sqrt(norm_factor))
            psi_norm.append(p / jnp.sqrt(norm_factor))
        # psi_norm = [p / jnp.sqrt(norm_factor) for p in psi]
        dens_norm = [d / norm_factor for d in dens]
    return psi_norm, dens_norm


def grad(psi, delta_r):
    """Compute the spatial gradient of a wavefunction :obj:`list`.

    Parameters
    ----------
    psi :
    delta_r :

    """
    if isinstance(psi, list):
        gradient = [grad_comp(p, delta_r) for p in psi]
    else:
        gradient = grad_comp(psi, delta_r)

    return gradient


def grad_comp(psi_comp, delta_r):
    """Spatial gradient of a single wavefunction component.

    Raises
    ------
    TypeError
        If `psi_comp` is neither an :obj:`array` or a :obj:`Tensor` of the
        correct shape.
    """
    if isinstance(psi_comp, np.ndarray):
        delta_r = np.array(delta_r)
        g_comp = np.gradient(psi_comp, *delta_r)
    elif isinstance(psi_comp, torch.Tensor):
        raise NotImplementedError(("Spatial gradients for tensors are not yet "
                                  "implemented."))
    else:
        delta_r = jnp.array(delta_r)
        g_comp = jnp.gradient(psi_comp, *delta_r)
        # raise TypeError(f"`psi_comp` is of type {type(psi_comp)} and shape "
                        # f"{psi_comp.shape}.")

    return g_comp


def grad_sq_comp(psi_comp, delta_r):
    """Take a list of tensors or np arrays; checks type."""
    grd_x, grd_y = grad_comp(psi_comp, delta_r)

    return grd_x**2 + grd_y**2


def grad_sq(psi, delta_r):
    """Compute the gradient squared of a wavefunction."""
    if isinstance(psi, list):
        g_sq = [grad_sq_comp(p, delta_r) for p in psi]
    else:
        g_sq = grad_sq_comp(psi, delta_r)

    return g_sq


def conj(psi):
    """Complex conjugate of a complex tensor."""
    if isinstance(psi, list):
        conjugate = [conj_comp(p) for p in psi]
    else:
        conjugate = conj_comp(psi)
    return conjugate


def conj_comp(psi_comp):
    """Complex conjugate of a single wavefunction component."""
    if isinstance(psi_comp, np.ndarray):
        cconj = np.conj(psi_comp)
    elif isinstance(psi_comp, torch.Tensor):
        cconj = torch.conj(psi_comp)
    else:
        raise TypeError(f"`psi_comp` is of type {type(psi_comp)} and shape "
                        f"{psi_comp.shape}.")

    return cconj


def density(psi):
    """
    Compute the density of a spinor wavefunction.

    Parameters
    ----------
    psi : :obj:`list` of 2D NumPy :obj:`array` or PyTorch :obj:`Tensor`
        The input spinor wavefunction.

    Returns
    -------
    dens : NumPy :obj:`array`, PyTorch :obj:`Tensor`, or :obj:`list` thereof
        The density of each component's wavefunction.

    """
    if isinstance(psi, list):
        dens = [norm_sq(p) for p in psi]
    else:
        dens = norm_sq(psi)
    return dens

def norm_sq(psi_comp):
    """Compute the density (norm-squared) of a single wavefunction component.

    Parameters
    ----------
    psi_comp : NumPy :obj:`array` or PyTorch :obj:`Tensor`
        A single wavefunction component.

    Returns
    -------
    psi_sq : NumPy :obj:`array` or PyTorch :obj:`Tensor`
        The norm-square of the wavefunction.

    Raises
    ------
    TypeError
        If `psi_comp` is neither an :obj:`array` or a :obj:`Tensor` of the
        correct shape.
    """
    if isinstance(psi_comp, np.ndarray):
        psi_sq = np.abs(psi_comp)**2

    elif isinstance(psi_comp, torch.Tensor):
        psi_sq = torch.abs(psi_comp)**2
    else:
        psi_sq = jnp.abs(psi_comp)**2
        # raise TypeError(f"`psi_comp` is of type {type(psi_comp)} and shape "
                        # f"{psi_comp.shape}.")
    return psi_sq


def calc_atoms(psi, vol_elem=1.0):
    """Calculate the total number of atoms.

    Parameters
    ----------
    psi : :obj:`list` of 2D NumPy :obj:`array` or PyTorch :obj:`Tensor`
        The input spinor wavefunction.
    vol_elem : :obj:`float`
        2D volume element of the space.

    Returns
    -------
    atom_num : :obj:`float`
        The total atom number in both spin components.

    """
    pops = calc_pops(psi, vol_elem=vol_elem)
    atom_num = sum(pops)

    return atom_num


def calc_pops(psi, vol_elem=1.0):
    """Calculate the populations in each spin component.

    Parameters
    ----------
    psi : :obj:`list` of 2D NumPy :obj:`array` or PyTorch :obj:`Tensor`
        The input spinor wavefunction.
    vol_elem : :obj:`float`
        2D volume element of the space.

    Returns
    -------
    pops : :obj:`list` of :obj:`float`
        The atom number in each spin component.
    """
    dens = density(psi)
    pops = [float(d.sum() * vol_elem) for d in dens]

    return pops


def phase(psi, uwrap=False, dens=None):
    """Compute the phase of a real-space spinor wavefunction.

    Parameters
    ----------
    psi : :obj:`list` of 2D NumPy :obj:`array` or PyTorch :obj:`Tensor`
        The input spinor wavefunction.

    Returns
    -------
    phase : NumPy :obj:`array`, PyTorch :obj:`Tensor`, or :obj:`list` thereof
        The phase of each component's wavefunction.
    """
    if dens is not None:
        assert len(psi) == len(dens), ("`psi` and `dens` should have the same "
                                       "length.")
    elif (dens is None and isinstance(psi, list)):
        dens = [None] * len(psi)

    if isinstance(psi, list):
        phase_psi = [phase_comp(p, uwrap, d) for p, d in zip(psi, dens)]
    else:
        phase_psi = phase_comp(psi, uwrap, dens)

    return phase_psi


def phase_comp(psi_comp, uwrap=False, dens=None):
    """Compute the phase (angle) of a single complex wavefunction component.

    Parameters
    ----------
    psi_comp : NumPy :obj:`array` or PyTorch :obj:`Tensor`
        A single wavefunction component.

    Returns
    -------
    angle : NumPy :obj:`array` or PyTorch :obj:`Tensor`
        The phase (angle) of the component's wavefunction.

    """
    if isinstance(psi_comp, np.ndarray):
        ang = jnp.angle(psi_comp)
        if uwrap:
            ang = rest.unwrap_phase(ang)
    elif isinstance(psi_comp, torch.Tensor):
        ang = torch.angle(psi_comp)
        if uwrap:
            raise NotImplementedError("Unwrapping the complex phase is not "
                                      "implemented for PyTorch tensors.")
    else:
        ang = jnp.angle(psi_comp)
        # if uwrap:
            # ang = rest.unwrap_phase(ang)
            # ang = jnp.array(ang)
    if dens is not None:
        ang = ang.at[dens < (dens.max() * 1e-6)].set(0)
        # ang[dens < (dens.max() * 1e-6)] = 0
    return ang


def inner_prod():
    """Calculate the inner product of two wavefunctions."""


def evolution_op(t_step, energy):
    """Compute the unitary time-evolution operator for the given energy.

    Parameters
    ----------
    energy :
    time_step :

    """
    if isinstance(energy, list):
        ev_op = [jnp.exp(-1.0j * eng * t_step) for eng in energy]
    else:
        ev_op = jnp.exp(-1.0j * energy * t_step)

    return ev_op


def coupling_op(t_step, coupling=None, expon=torch.tensor(0)):
    """Compute the time-evolution operator for the coupling term.

    Parameters
    ----------
    t_step : :obj:`float`
        Sub-time step.
    coupling : 2D PyTorch complex :obj:`Tensor`, optional.
        The coupling mesh. Default is none if `self.is_coupling = False`.
        In this case, the evolution operator returned will the identity
        matrix.
    expon : 2D PyTorch real :obj:`Tensor`, optional.
        The exponential argument in the bare coupling term. If there is
        no coupling, then this is 0 by default.

    Returns
    -------
    coupl_ev_op : 2D PyTorch :obj:`Tensor`, optional.

    """
    if coupling is None:
        coupling = torch.tensor(0)

    arg = coupling * t_step / 2
    cosine = jnp.cos(arg)
    sine = -1.0j * jnp.sin(arg)
    coupl_op = [[cosine, sine * jnp.exp(-1.0j * expon)],
                [sine * jnp.exp(1.0j * expon), cosine]]
    return coupl_op


def prod(factors):
    """General function for multiplying the elements of a 1D data structure.

    Operates similar to the `sum` function from the standard library.

    """
    return reduce(operator.mul, factors, 1)


def expect_val(psi):
    """Compute the expectation value of the supplied spatial operator."""
    raise NotImplementedError(("Function for computing the expectation "
                               "value of an arbitrary spatial operator "
                               "is not implemented."))
