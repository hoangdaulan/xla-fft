"""Repeatable package-2 audit; run with .venv/bin/python tools/verify_handoff.py."""
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import platform
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import numpy as np
from PIL import Image,ImageDraw,__version__ as pillow_version
from frequency_filter.fft import fft2d,ifft2d
from frequency_filter.desktop_bridge import DEFAULTS
from frequency_filter.desktop_model import process,read_image
from frequency_filter.pipeline import to_uint8
from benchmark import benchmark


def quality(clean, candidate):
    mse=float(np.mean((to_uint8(clean).astype(float)-to_uint8(candidate).astype(float))**2))
    return {'mse':mse,'psnr_db':None if mse==0 else float(10*np.log10(255**2/mse))}


def main():
    out=ROOT/'results/handoff';out.mkdir(parents=True,exist_ok=True)
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    stream=io.StringIO()
    tests=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    (out/'python_tests.txt').write_text(stream.getvalue(),encoding='utf-8')
    rng=np.random.default_rng(14)
    x=rng.normal(size=(64,64))
    f=fft2d(x);reference=np.fft.fft2(x)
    validation=dict(seed=14,shape=[64,64],input='standard normal float64',
      fft_max_abs_error=float(np.max(abs(f-reference))),
      fft_relative_max_error=float(np.max(abs(f-reference))/np.max(abs(reference))),
      roundtrip_max_abs_error=float(np.max(abs(ifft2d(f)-x))),
      parseval_relative_error=float(abs(np.sum(abs(f)**2)/x.size-np.sum(x*x))/np.sum(x*x)))
    assert validation['fft_relative_max_error']<1e-10
    assert validation['roundtrip_max_abs_error']<1e-10
    assert validation['parseval_relative_error']<1e-10
    clean,_=read_image(ROOT/'results/demo/clean.png')
    noisy,_=read_image(ROOT/'results/demo/noisy.png')
    settings={**DEFAULTS,'padding':'none','radius':3.,'kind':'butterworth','order':4}
    # Same centers used by clicking the actual manual-mask UI for this synthetic fixture.
    action=(47,53,3.)  # frequency (-17,-11), paired with (17,11)
    manual=process(noisy,{**settings,'filter':'mask'},[action])
    auto=process(noisy,{**settings,'filter':'auto'})
    # A controlled same-family reference separates peak detection from hard/soft mask differences.
    from frequency_filter.filters import notch_reject
    from frequency_filter.pipeline import reconstruct
    placed_notch,_=reconstruct(auto.prepared,notch_reject(noisy.shape,[(17,11)],radius=3,order=4))
    assert any(tuple(peak) in ((17,11),(-17,-11)) for peak in auto.peaks)
    rows=[]
    for name,image in [('noisy',noisy),('manual_binary_mask',manual.output),
                       ('manual_butterworth_notch',placed_notch),('auto_butterworth_notch',auto.output)]:
        rows.append({'method':name,**quality(clean,image)})
        Image.fromarray(to_uint8(image)).save(out/f'{name}.png')
    assert rows[-1]['mse']<rows[0]['mse']
    with (out/'manual_vs_auto.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=['method','mse','psnr_db'])
        writer.writeheader();writer.writerows(rows)
    comparison=Image.new('RGB',(960,230),'white');draw=ImageDraw.Draw(comparison)
    for i,(name,image) in enumerate([('Clean',clean),('Noisy',noisy),('Manual binary',manual.output),
                                    ('Manual BW',placed_notch),('Auto BW',auto.output)]):
        comparison.paste(Image.fromarray(to_uint8(image)).resize((192,192)),(192*i,32))
        draw.text((192*i+8,10),name,fill='black')
    comparison.save(out/'comparison.png')
    with (out/'comparison_config.json').open('w') as file:
        json.dump(dict(settings=settings,manual_actions=[action],auto_peaks=auto.peaks,
          metric_domain='clip+half-up round to uint8; both input PNGs already quantized',
          limitations=['One smooth synthetic image; not the group dataset',
            'Manual binary and automatic Butterworth use different transfer shapes',
            'Manual BW versus Auto BW uses the same family/radius/order',
            'Human selection time is not measured']),file,ensure_ascii=False,indent=2)
    timing=benchmark(sizes=(64,128),repeats=3)
    with (out/'benchmark_smoke.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(timing[0]));writer.writeheader();writer.writerows(timing)
    report=dict(generated_at_utc=datetime.now(timezone.utc).isoformat(),
      environment=dict(python=platform.python_version(),numpy=np.__version__,pillow=pillow_version,platform=platform.platform()),
      python_tests=dict(run=tests.testsRun,failures=len(tests.failures),errors=len(tests.errors),passed=tests.wasSuccessful()),
      numerical_validation=validation,manual_vs_auto=rows,auto_peaks=auto.peaks,
      benchmark_smoke=dict(sizes=[64,128],repeats=3,backends=sorted(set(row['backend'] for row in timing))),
      scope='Code handoff verification only; not a final Fiji or real-dataset evaluation')
    (out/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    # Keep the historical path used by chapter 4, with explicit scope and current test count.
    (ROOT/'results/validation.json').write_text(json.dumps({**validation,
      'python':platform.python_version(),'numpy':np.__version__,'unit_tests':tests.testsRun,
      'status':'passed' if tests.wasSuccessful() else 'failed',
      'source':'tools/verify_handoff.py; full report: results/handoff/verification.json'},indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if not tests.wasSuccessful():raise SystemExit(1)


if __name__=='__main__':main()
