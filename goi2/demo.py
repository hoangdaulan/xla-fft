"""Synthetic demo only; not a substitute for package 4's real dataset."""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from frequency_filter.pipeline import prepare, reconstruct, to_uint8
from frequency_filter.filters import notch_reject, find_noise_peaks
from frequency_filter.desktop_model import manual_transfer


def main():
    out = Path('results/demo'); out.mkdir(parents=True, exist_ok=True)
    n = 128
    x, y = np.mgrid[:n,:n]
    clean = 128 + 25*np.cos(2*np.pi*x/n) + 20*np.cos(4*np.pi*y/n)
    noisy = to_uint8(clean + 20*np.sin(2*np.pi*(17*x/n+11*y/n))).astype(float)
    clean = to_uint8(clean).astype(float)
    for name, data in [('clean',clean),('noisy',noisy)]:
        Image.fromarray(to_uint8(data)).save(out/f'{name}.png')
    prepared = prepare(noisy, padding='none')
    peaks = find_noise_peaks(prepared.spectrum)
    manual, _ = reconstruct(prepared, manual_transfer((n,n), [(47,53,3)]))
    auto, _ = reconstruct(prepared, notch_reject((n,n), peaks, radius=3))
    scores = {'detected_peaks':peaks, 'metric_domain':'quantized PNG input; rounded 8-bit metrics',
              'manual_method':'binary circular mask, radius 3, row 47 col 53 plus conjugate',
              'auto_method':'Butterworth notch, radius 3, order 4',
              'warning':'Synthetic smooth image; not representative dataset evidence'}
    for name, data in [('noisy',noisy),('manual',manual),('auto',auto)]:
        data8 = to_uint8(data)
        mse = float(np.mean((to_uint8(clean).astype(float)-data8.astype(float))**2))
        scores[name] = {'mse':mse, 'psnr':None if mse == 0 else float(10*np.log10(255**2/mse))}
        Image.fromarray(data8).save(out/f'{name}.png')
    # Portable comparison strip, no GUI dependency.
    strip = np.concatenate([to_uint8(z) for z in (clean,noisy,manual,auto)], axis=1)
    Image.fromarray(strip).save(out/'comparison.png')
    canvas = Image.new('RGB', (768,230), 'white')
    draw = ImageDraw.Draw(canvas)
    for i, (data, label) in enumerate(zip((clean,noisy,manual,auto),
                                        ('Clean','Noisy','Manual binary','Auto BW'))):
        canvas.paste(Image.fromarray(to_uint8(data)).resize((192,192)), (192*i,32))
        draw.text((192*i+10,10), label, fill='black')
    canvas.save(out/'comparison_labeled.png')
    (out/'metrics.json').write_text(json.dumps(scores,indent=2),encoding='utf-8')
    print(json.dumps(scores,indent=2))


if __name__ == '__main__':
    main()
