"""Iterative Cooley–Tukey radix-2; no numpy.fft calls in this module."""
import numpy as np


def next_power_two(n):
    if n < 1:
        raise ValueError('Length must be positive')
    return 1 << (int(n) - 1).bit_length()


def _fft_axis(values, axis):
    a = np.moveaxis(np.asarray(values, dtype=np.complex128), axis, -1)
    n = a.shape[-1]
    if n < 1 or n & (n - 1):
        raise ValueError('Radix-2 requires power-of-two dimensions')
    # Bit-reversed input order, followed by log2(n) butterfly stages.
    indices = np.arange(n)
    rev = np.zeros(n, dtype=int)
    for _ in range(n.bit_length() - 1):
        rev = (rev << 1) | (indices & 1)
        indices >>= 1
    a = a[..., rev].copy()
    size = 2
    while size <= n:
        blocks = a.reshape(*a.shape[:-1], n // size, size)
        even = blocks[..., :size // 2].copy()
        odd = blocks[..., size // 2:].copy()
        odd *= np.exp(-2j * np.pi * np.arange(size // 2) / size)
        blocks[..., :size // 2] = even + odd
        blocks[..., size // 2:] = even - odd
        size *= 2
    return np.moveaxis(a, -1, axis)


def fft1d(x):
    x = np.asarray(x)
    if x.ndim != 1:
        raise ValueError('Expected a 1D array')
    return _fft_axis(x, 0)


def fft2d(x):
    x = np.asarray(x)
    if x.ndim != 2:
        raise ValueError('Expected a 2D array')
    return _fft_axis(_fft_axis(x, 1), 0)


def ifft2d(spectrum):
    spectrum = np.asarray(spectrum)
    return np.conj(fft2d(np.conj(spectrum))) / spectrum.size


def fftshift(x):
    return np.roll(x, tuple(s // 2 for s in x.shape), axis=tuple(range(x.ndim)))


def ifftshift(x):
    return np.roll(x, tuple(-(s // 2) for s in x.shape), axis=tuple(range(x.ndim)))
