"""Transfer functions use CENTERED spectra; coordinates are (row, column)."""
import numpy as np


def grid(shape):
    u = np.arange(shape[0])[:, None] - shape[0] // 2
    v = np.arange(shape[1])[None, :] - shape[1] // 2
    return u, v, np.hypot(u, v)


def partner(h):
    """H(-u,-v), modulo dimensions (correct also on Nyquist axes)."""
    m, n = h.shape
    return h[np.ix_((2 * (m // 2) - np.arange(m)) % m,
                    (2 * (n // 2) - np.arange(n)) % n)]


def symmetric_mask(h, mode='reject'):
    h = np.asarray(h, dtype=float)
    if h.ndim != 2 or not np.isfinite(h).all() or np.any((h < 0) | (h > 1)):
        raise ValueError('Mask must be finite, 2D, and in [0,1]')
    if mode not in ('reject', 'pass'):
        raise ValueError('Mask mode must be reject or pass')
    return np.minimum(h, partner(h)) if mode == 'reject' else np.maximum(h, partner(h))


def _positive(*values):
    if not all(np.isfinite(x) and x > 0 for x in values):
        raise ValueError('Parameters must be positive and finite')


def bandpass(shape, center=20, width=10, kind='gaussian', order=2):
    _positive(center, width, order)
    if int(order) != order:
        raise ValueError('Order must be an integer')
    _, _, d = grid(shape)
    if kind == 'ideal':
        return ((d >= center - width / 2) & (d <= center + width / 2)).astype(float)
    with np.errstate(divide='ignore', invalid='ignore', over='ignore'):
        if kind == 'gaussian':
            h = np.exp(-((d*d - center*center) / (d*width))**2)
        elif kind == 'butterworth':
            h = 1 - 1 / (1 + ((d*width) / (d*d-center*center))**(2*order))
        else:
            raise ValueError('Unknown bandpass family')
    h[d == 0] = 0
    return h


def notch_reject(shape, centers, radius=3, order=4, kind='butterworth'):
    _positive(radius, order)
    if int(order) != order:
        raise ValueError('Order must be an integer')
    u, v, _ = grid(shape)
    h = np.ones(shape)
    for uk, vk in centers:
        if not np.isfinite([uk, vk]).all():
            raise ValueError('Notch coordinates must be finite')
        for sign in (-1, 1):
            # Periodic distance ensures conjugate symmetry near Nyquist borders.
            du = (u - sign*uk + shape[0]/2) % shape[0] - shape[0]/2
            dv = (v - sign*vk + shape[1]/2) % shape[1] - shape[1]/2
            d = np.hypot(du, dv)
            if kind == 'ideal':
                h *= d > radius
            elif kind == 'gaussian':
                h *= 1 - np.exp(-d*d / (2*radius*radius))
            elif kind == 'butterworth':
                with np.errstate(divide='ignore', over='ignore'):
                    h *= 1 / (1 + (radius / d)**order)
            else:
                raise ValueError('Unknown notch family')
    return h


def suppress_stripes(shape, direction='horizontal', tolerance=5, protect_radius=0):
    if direction not in ('horizontal', 'vertical'):
        raise ValueError('Direction must be horizontal or vertical')
    if not np.isfinite(tolerance) or not 0 <= tolerance < 100:
        raise ValueError('Tolerance must be in [0,100)')
    if not np.isfinite(protect_radius) or protect_radius < 0:
        raise ValueError('Protection radius must be nonnegative')
    u, v, d = grid(shape)
    coord = v if direction == 'horizontal' else u
    h = np.broadcast_to(1 - np.exp(-coord**2 * ((100-tolerance)/100)**2), shape).copy()
    h[d <= protect_radius] = 1  # DC retained, like ImageJ.
    return h


def imagej_bandpass(shape, large=40, small=3):
    _positive(large)
    if not np.isfinite(small) or small < 0 or small >= large:
        raise ValueError('Require 0 <= small < large')
    if shape[0] != shape[1]:
        raise ValueError('ImageJ mode requires square padding')
    _, _, d = grid(shape)
    h = (1 - np.exp(-d*d*(2*large/shape[0])**2)) * np.exp(-d*d*(2*small/shape[0])**2)
    h[shape[0]//2, shape[1]//2] = 1
    return h


def find_noise_peaks(spectrum, exclude_radius=10, window=7, threshold=6, max_pairs=12):
    """Local maxima of log amplitude, threshold median + k*MAD; heuristic."""
    if window < 3 or window % 2 != 1 or max_pairs < 1 or threshold <= 0 or exclude_radius < 0:
        raise ValueError('Invalid peak detection parameters')
    s = np.log1p(np.abs(spectrum))
    u, v, d = grid(s.shape)
    background = s[d > exclude_radius]
    if not background.size:
        return []
    med = np.median(background)
    mad = np.median(np.abs(background - med))
    cutoff = med + threshold * max(float(mad), 1e-12)
    # Ignore floating-point dust on spectra of exact analytic sinusoids.
    amplitude = np.abs(spectrum)
    floor = float(np.max(amplitude)) * 1e-10
    candidate = (s > cutoff) & (d > exclude_radius) & (amplitude > floor)
    for dy in range(-window//2+1, window//2+1):
        for dx in range(-window//2+1, window//2+1):
            candidate &= s >= np.roll(s, (dy, dx), axis=(0, 1))
    # Canonicalize pairs modulo array shape, including Nyquist coordinates.
    locations = np.argwhere(candidate)
    locations = sorted(locations, key=lambda ij: float(s[tuple(ij)]), reverse=True)
    peaks, seen = [], set()
    for row, col in locations:
        pair = ((2*(s.shape[0]//2)-int(row)) % s.shape[0],
                (2*(s.shape[1]//2)-int(col)) % s.shape[1])
        key = min((int(row), int(col)), pair)
        if key not in seen:
            peaks.append((int(row)-s.shape[0]//2, int(col)-s.shape[1]//2))
            seen.add(key)
        if len(peaks) == max_pairs:
            break
    return peaks
