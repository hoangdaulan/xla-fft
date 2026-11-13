"""Run: python -m frequency_filter --help"""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image
from .pipeline import prepare, reconstruct, power_spectrum, to_uint8
from .filters import bandpass, notch_reject, suppress_stripes, imagej_bandpass, find_noise_peaks, symmetric_mask


def build_parser():
    p = argparse.ArgumentParser(description='Gói 2 — lọc ảnh mức xám trong miền tần số')
    p.add_argument('input', type=Path)
    p.add_argument('--output', type=Path, default=Path('results/run'))
    p.add_argument('--filter', choices=['identity','bandpass','stripes','notch','auto','mask','imagej'], default='identity')
    p.add_argument('--backend', choices=['radix2','numpy'], default='radix2')
    p.add_argument('--padding', choices=['zero','symmetric','edge','none','imagej'], default='zero')
    p.add_argument('--minimal-padding', action='store_true', help='Pad to next power of 2, without doubling')
    p.add_argument('--kind', choices=['ideal','gaussian','butterworth'], default='gaussian')
    p.add_argument('--center', type=float, default=20)
    p.add_argument('--width', type=float, default=10)
    p.add_argument('--order', type=int, default=4)
    p.add_argument('--radius', type=float, default=3)
    p.add_argument('--notch', type=float, nargs=2, action='append', default=[], metavar=('U','V'))
    p.add_argument('--direction', choices=['horizontal','vertical'], default='horizontal')
    p.add_argument('--tolerance', type=float, default=5)
    p.add_argument('--protect-radius', type=float, default=0)
    p.add_argument('--large', type=float, default=40)
    p.add_argument('--small', type=float, default=3)
    p.add_argument('--exclude-radius', type=float, default=10)
    p.add_argument('--threshold', type=float, default=6)
    p.add_argument('--max-pairs', type=int, default=12)
    p.add_argument('--mask', type=Path, help='.npy [0,1] or grayscale PNG: black rejects, white passes')
    p.add_argument('--mask-mode', choices=['reject','pass'], default='reject')
    p.add_argument('--interactive-mask', action='store_true', help='Click spectrum to add circular mask regions')
    p.add_argument('--show', action='store_true')
    return p


def edit_mask(spectrum, h, radius, mode):
    import matplotlib.pyplot as plt
    from .filters import grid
    u, v, _ = grid(h.shape)
    fig, ax = plt.subplots()
    ax.imshow(np.log1p(power_spectrum(spectrum)), cmap='gray')
    overlay = ax.imshow(h, cmap='Reds', alpha=0.3, vmin=0, vmax=1)
    ax.set_title('Click: circular mask + conjugate pair. Close window to apply.')
    def click(event):
        if event.inaxes != ax or event.xdata is None or event.ydata is None:
            return
        uk, vk = round(event.ydata)-h.shape[0]//2, round(event.xdata)-h.shape[1]//2
        selected = np.hypot(u-uk, v-vk) <= radius
        h[selected] = 0 if mode == 'reject' else 1
        h[:] = symmetric_mask(h, mode)
        overlay.set_data(h)
        fig.canvas.draw_idle()
    fig.canvas.mpl_connect('button_press_event', click)
    plt.show()
    return h


def run(args):
    with Image.open(args.input) as image:
        source_mode = image.mode
        a = np.asarray(image.convert('L'), dtype=float)
    if args.filter == 'imagej' and args.padding != 'imagej':
        raise ValueError('Use --padding imagej with --filter imagej')
    prepared = prepare(a, args.padding, args.backend, not args.minimal_padding)
    shape = prepared.spectrum.shape
    peaks = []
    if args.filter == 'bandpass':
        h = bandpass(shape, args.center, args.width, args.kind, args.order)
    elif args.filter == 'stripes':
        h = suppress_stripes(shape, args.direction, args.tolerance, args.protect_radius)
    elif args.filter in ('notch','auto'):
        peaks = args.notch if args.filter == 'notch' else find_noise_peaks(
            prepared.spectrum, args.exclude_radius, threshold=args.threshold, max_pairs=args.max_pairs)
        if args.filter == 'notch' and not peaks:
            raise ValueError('Provide at least one --notch U V')
        h = notch_reject(shape, peaks, args.radius, args.order, args.kind)
    elif args.filter == 'imagej':
        h = imagej_bandpass(shape, args.large, args.small)
    elif args.filter == 'mask':
        if args.mask:
            if args.mask.suffix.lower() == '.npy':
                h = np.load(args.mask, allow_pickle=False)
            else:
                with Image.open(args.mask) as im:
                    h = np.asarray(im.convert('L'), dtype=float) / 255
            if h.shape != shape:
                raise ValueError(f'Mask shape must be {shape}; received {h.shape}')
            h = symmetric_mask(h, args.mask_mode)
        elif args.interactive_mask:
            h = np.ones(shape) if args.mask_mode == 'reject' else np.zeros(shape)
        else:
            raise ValueError('Provide --mask or --interactive-mask')
    else:
        h = np.ones(shape)
    if args.interactive_mask:
        if args.radius <= 0:
            raise ValueError('Mask radius must be positive')
        h = edit_mask(prepared.spectrum, h, args.radius, args.mask_mode)
    result, imaginary = reconstruct(prepared, h)
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    Image.fromarray(to_uint8(result)).save(out/'filtered.png')
    Image.fromarray(to_uint8(a)).save(out/'input.png')
    Image.fromarray(to_uint8(h*255)).save(out/'mask.png')
    raw_power = power_spectrum(prepared.spectrum)
    display = np.log1p(raw_power)
    display = (display-display.min()) / max(float(np.ptp(display)), 1e-12)*255
    Image.fromarray(to_uint8(display)).save(out/'spectrum.png')
    np.save(out/'spectrum_complex.npy', prepared.spectrum)
    np.save(out/'power_raw.npy', raw_power)
    np.save(out/'mask.npy', h)
    np.save(out/'filtered_float.npy', result)
    config = {k: str(v) if isinstance(v, Path) else v for k,v in vars(args).items()}
    config.update(original_shape=list(a.shape), padded_shape=list(shape), crop_offset=list(prepared.offset),
                  source_mode=source_mode, detected_peaks=peaks, imaginary_residual=imaginary,
                  rounding='clip [0,255], floor(x+0.5)', spectrum_order='centered')
    (out/'config.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'output':str(out), 'peaks':peaks, 'imaginary_residual':imaginary}, ensure_ascii=False))
    if args.show:
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(1,4, figsize=(14,4))
        for ax, data, title in zip(axes, [a, display, h, result], ['Input','Log power','Transfer H','Output']):
            ax.imshow(data, cmap='gray'); ax.set_title(title); ax.axis('off')
        fig.tight_layout(); plt.show()


def main():
    parser = build_parser()
    args = parser.parse_args()
    try:
        run(args)
    except (ValueError, OSError, ImportError) as e:
        parser.exit(2, f'Error: {e}\n')


if __name__ == '__main__':
    main()
