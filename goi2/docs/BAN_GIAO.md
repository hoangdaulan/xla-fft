# Bàn giao gói 2 cho gói 3 và gói 4

## API cho gói 4

Chạy script từ `goi2`, hoặc thêm đường dẫn thư mục này vào PYTHONPATH.

```python
import numpy as np
from frequency_filter import fft2d, ifft2d, filter_freq
from frequency_filter.filters import bandpass, notch_reject
from frequency_filter.pipeline import prepare, reconstruct, to_uint8

# Chỉ FFT: gói 4 gọi trực tiếp để benchmark, không tính I/O hoặc padding
F = fft2d(np.zeros((256, 256)))
x = ifft2d(F)

# Luồng lọc trả float64, chưa clip
out = filter_freq(image, lambda P, Q: bandpass((P, Q), center=30, width=10), pad='zero')
out8 = to_uint8(out)  # metric 8-bit theo quy ước gói 1

# Tái sử dụng phổ khi thử nhiều H trên cùng ảnh
p = prepare(image, padding='symmetric', backend='radix2')
H = notch_reject(p.spectrum.shape, centers=[(17, 11)], radius=3)
out, imaginary_residual = reconstruct(p, H)
```

```bash
python benchmark.py --sizes 64 128 256 512 1024 --repeats 5 --output results/benchmark.csv
```

SciPy là tùy chọn: `python -m pip install scipy`. Nếu chưa cài thì CSV chỉ có radix2 và NumPy.
Warmup một lượt mỗi backend, đo FFT thuận, lấy median/min. Ảnh random được tạo ngoài vùng đo,
seed 14. Gói 4 bổ sung CPU, OS, phiên bản thư viện và cấu hình threads khi công bố số liệu.
Kết quả đo tại máy hiện tại nằm trong `results/benchmark.csv`; không suy rộng thành tốc độ mọi máy.

## Cấu hình cần thống nhất

1. Mặc định zero padding là nextpow2(2M), nextpow2(2N). Nếu nhóm yêu cầu đúng 2M×2N
   cho ảnh gốc không có kích thước lũy thừa 2 thì dùng backend NumPy không tự viết,
   hoặc đổi dataset; hiện API vẫn chọn padding lũy thừa 2 cho cả hai backend để so cùng cấu hình.
2. ImageJ cần dùng `padding=imagej`, `imagej_bandpass`; không lấy bandpass vòng của Gonzalez để so.
3. Sọc ngang tạo năng lượng trên cột giữa phổ; sọc dọc tạo năng lượng trên hàng giữa.
4. Tọa độ nhiễu tổng hợp cần nhân tỉ lệ kích thước padding khi chuyển từ ảnh gốc.
   Padding zero/gương còn gây rò phổ: không kỳ vọng chỉ còn đúng hai pixel đỉnh.
5. Metric chất lượng dùng ảnh sạch làm chuẩn, cùng bước clip/làm tròn 8-bit.
6. Năng lượng đỉnh dùng phổ thô cùng kích thước, cùng miền Ω xác định trước khi lọc.
   Nếu FFT lại ảnh đã crop/clip, đó là phép đo khác với abs(H*F)^2 trên khung padding.
7. Tự dò là heuristic; cấu trúc thật và biên ảnh có thể bị coi là nhiễu. Gói 4 cần đo
   trên nhiều ảnh, lưu config, so cùng radius/order và báo số đỉnh, thời gian dò/đặt tay.

## Gói 3 cần trả lại

Phiên bản Fiji/ImageJ, ảnh đầu vào, macro/tham số, trạng thái Autoscale/Saturate,
ảnh H từ Display filter, ảnh ra 8-bit và raw power nếu có. Chưa có các file này nên
chưa thể kết luận Python khớp Fiji. Không dùng ảnh phổ hiển thị 8-bit để so phổ định lượng.
