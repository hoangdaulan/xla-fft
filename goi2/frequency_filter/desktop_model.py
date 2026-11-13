"""Display-independent processing and export for the desktop application."""
from dataclasses import dataclass
from pathlib import Path
import json
from time import perf_counter
import numpy as np
from PIL import Image
from .pipeline import prepare, reconstruct, power_spectrum, to_uint8
from .filters import (bandpass, notch_reject, suppress_stripes, imagej_bandpass,
                      find_noise_peaks, symmetric_mask)


@dataclass
class Preview:
    source: np.ndarray
    prepared: object
    transfer: np.ndarray
    output: np.ndarray
    config: dict
    peaks: list
    seconds: float
    imaginary: float


def read_image(path):
    with Image.open(path) as im:
        return np.asarray(im.convert('L'), dtype=np.float64), im.mode


def manual_transfer(shape, actions, mode='reject'):
    h = np.ones(shape) if mode == 'reject' else np.zeros(shape)
    rows, cols = np.ogrid[:shape[0], :shape[1]]
    for row, col, radius in actions:
        if not np.isfinite([row, col, radius]).all() or radius <= 0:
            raise ValueError('Bán kính mask phải lớn hơn 0 và hữu hạn.')
        selected = (rows-row)**2 + (cols-col)**2 <= radius**2
        h[selected] = 0 if mode == 'reject' else 1
    return symmetric_mask(h, mode)


def process(image, settings, actions=(), cached=None):
    started = perf_counter()
    config = dict(settings)
    config['mask_actions'] = [list(a) for a in actions]
    mode = settings['filter']
    padding = 'imagej' if mode == 'imagej' else settings['padding']
    backend = settings['backend']
    # Caller supplies a cache only for the same source and preparation settings.
    p = cached if cached is not None and cached.padding == padding and cached.backend == backend else prepare(image, padding, backend)
    shape = p.spectrum.shape
    peaks = []
    if mode == 'bandpass':
        h = bandpass(shape, settings['center'], settings['width'], settings['kind'], settings['order'])
    elif mode == 'stripes':
        h = suppress_stripes(shape, settings['direction'], settings['tolerance'], settings['protect'])
    elif mode == 'auto':
        peaks = find_noise_peaks(p.spectrum, settings['exclude'], threshold=settings['threshold'], max_pairs=settings['max_pairs'])
        h = notch_reject(shape, peaks, settings['radius'], settings['order'], settings['kind'])
    elif mode == 'mask':
        h = manual_transfer(shape, actions, settings['mask_mode'])
    elif mode == 'imagej':
        h = imagej_bandpass(shape, settings['large'], settings['small'])
    elif mode == 'identity':
        h = np.ones(shape)
    else:
        raise ValueError('Chế độ lọc không hợp lệ.')
    output, imaginary = reconstruct(p, h)
    config.update(padding=padding, original_shape=list(image.shape), padded_shape=list(shape),
                  crop_offset=list(p.offset), detected_peaks=peaks, rounding='clip [0,255], floor(x+0.5)',
                  spectrum_order='centered', imaginary_residual=imaginary)
    return Preview(image, p, h, output, config, peaks, perf_counter()-started, imaginary)


def save_image(path, result):
    path = Path(path)
    if path.suffix.lower() not in ('.png', '.tif', '.tiff', '.bmp'):
        raise ValueError('Chọn định dạng PNG, TIFF hoặc BMP để lưu ảnh không mất dữ liệu.')
    Image.fromarray(to_uint8(result.output)).save(path)


def export_bundle(directory, result):
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    save_image(out/'filtered.png', result)
    Image.fromarray(to_uint8(result.source)).save(out/'input.png')
    Image.fromarray(to_uint8(result.transfer*255)).save(out/'mask.png')
    power = power_spectrum(result.prepared.spectrum)
    display = np.log1p(power)
    display = (display-display.min())/max(float(np.ptp(display)),1e-12)*255
    Image.fromarray(to_uint8(display)).save(out/'spectrum.png')
    for name, data in [('filtered_float',result.output),('mask',result.transfer),
                       ('spectrum_complex',result.prepared.spectrum),('power_raw',power)]:
        np.save(out/f'{name}.npy', data)
    (out/'config.json').write_text(json.dumps(result.config, ensure_ascii=False, indent=2), encoding='utf-8')
