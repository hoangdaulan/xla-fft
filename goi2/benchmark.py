"""FFT-only benchmark for package 4: input creation excluded, warmup included separately."""
import argparse
import csv
from pathlib import Path
from time import perf_counter
import numpy as np
from frequency_filter.fft import fft2d


def benchmark(sizes=(64,128,256,512), repeats=5):
    if repeats < 1 or any(n < 1 or n & (n-1) for n in sizes):
        raise ValueError('Use power-of-two sizes and positive repeats')
    backends = {'radix2': fft2d, 'numpy': np.fft.fft2}
    try:
        from scipy.fft import fft2
        backends['scipy'] = fft2
    except ImportError:
        pass
    rng = np.random.default_rng(14)
    rows = []
    for n in sizes:
        a = rng.normal(size=(n,n))
        reference = np.fft.fft2(a)
        for name, forward in backends.items():
            forward(a)
            elapsed = []
            for _ in range(repeats):
                start = perf_counter(); result = forward(a); elapsed.append(perf_counter()-start)
            rows.append(dict(size=n, backend=name, repeats=repeats,
                             median_seconds=float(np.median(elapsed)), min_seconds=min(elapsed),
                             relative_max_error=float(np.max(np.abs(result-reference))/max(1,float(np.max(np.abs(reference)))))))
    return rows


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--sizes', type=int, nargs='+', default=[64,128,256,512])
    p.add_argument('--repeats', type=int, default=5)
    p.add_argument('--output', type=Path, default=Path('results/benchmark.csv'))
    args = p.parse_args()
    rows = benchmark(args.sizes, args.repeats)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    print(args.output)
