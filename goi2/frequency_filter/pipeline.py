from dataclasses import dataclass
import numpy as np
from .fft import fft2d, ifft2d, fftshift, ifftshift, next_power_two
from .filters import partner


@dataclass
class Prepared:
    spectrum: np.ndarray
    original_shape: tuple
    offset: tuple
    backend: str
    padding: str


def prepare(image, padding='zero', backend='radix2', double=True):
    a = np.asarray(image, dtype=np.float64)
    if a.ndim != 2 or not a.size or not np.isfinite(a).all():
        raise ValueError('Expected a nonempty finite grayscale image')
    if backend not in ('radix2', 'numpy'):
        raise ValueError('Backend must be radix2 or numpy')
    m, n = a.shape
    if padding == 'none':
        padded, offset = a, (0, 0)
    elif padding == 'imagej':
        side = max(2, next_power_two(int(np.ceil(1.5*max(m, n)))))
        # Java Math.round(x/2.0): round halves upward, not Python bankers rounding.
        top, left = (side-m+1)//2, (side-n+1)//2
        padded = np.pad(a, ((top, side-m-top), (left, side-n-left)), mode='symmetric')
        offset = (top, left)
    elif padding in ('zero', 'symmetric', 'edge'):
        p, q = (next_power_two(s*(2 if double else 1)) for s in (m, n))
        padded = np.pad(a, ((0, p-m), (0, q-n)), mode='constant' if padding == 'zero' else padding)
        offset = (0, 0)
    else:
        raise ValueError('Unknown padding mode')
    forward = fft2d if backend == 'radix2' else np.fft.fft2
    return Prepared(fftshift(forward(padded)), (m, n), offset, backend, padding)


def reconstruct(prepared, transfer=None):
    f = prepared.spectrum
    h = np.ones(f.shape) if transfer is None else np.asarray(transfer, dtype=float)
    if h.shape != f.shape or not np.isfinite(h).all() or np.any((h < 0) | (h > 1)):
        raise ValueError('Transfer must match spectrum and lie in [0,1]')
    if not np.allclose(h, partner(h), atol=1e-12, rtol=0):
        raise ValueError('Transfer is not conjugate-symmetric; mirror the mask')
    inverse = ifft2d if prepared.backend == 'radix2' else np.fft.ifft2
    spatial = inverse(ifftshift(f*h))
    imaginary = float(np.max(np.abs(spatial.imag)))
    if imaginary > 1e-9*max(1, float(np.max(np.abs(spatial.real)))):
        raise ValueError('Unexpected imaginary residual')
    top, left = prepared.offset
    m, n = prepared.original_shape
    return spatial.real[top:top+m, left:left+n].copy(), imaginary


def filter_freq(image, make_H, pad='zero', backend='radix2', double=True):
    """Gói 4 API: make_H(P,Q) -> centered transfer; returns float64, unclipped."""
    prepared = prepare(image, pad, backend, double)
    return reconstruct(prepared, make_H(*prepared.spectrum.shape))[0]


def power_spectrum(centered_spectrum):
    return np.abs(centered_spectrum)**2


def to_uint8(image):
    # Explicit half-up rounding, unlike np.rint's ties-to-even.
    return np.floor(np.clip(image, 0, 255)+0.5).astype(np.uint8)
