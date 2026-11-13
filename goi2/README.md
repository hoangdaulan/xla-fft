# Gói 2 — Fourier Studio, Nhóm 14

Chương trình lọc ảnh mức xám trong miền tần số. Lõi FFT/IFFT radix-2 tự viết;
NumPy FFT chỉ dùng khi chọn backend tham chiếu hoặc trong kiểm thử/benchmark.

## Giao diện desktop Flutter

Từ thư mục gốc repository:

```bash
bash goi2/mo_flutter.sh
```

`goi2/mo_giao_dien.sh` cũng mở bản Flutter. GUI hiện hỗ trợ Linux desktop. Bấm **Mở ảnh** → chọn bộ lọc → **Xem trước** → **Lưu ảnh**.
Tab **So sánh** hiển thị trước/sau; **Phổ & Mask** cho phép xem phổ và chọn mask đối xứng,
hoàn tác hoặc xóa mask. Nút hình thư mục cạnh Lưu ảnh xuất ảnh, phổ thô, mask và cấu hình.
Preview và ảnh lưu dùng cùng thang sáng 0–255; file lưu giữ nguyên kích thước gốc.

Hướng dẫn chi tiết và cách build: [flutter_app/README.md](flutter_app/README.md).
Ảnh giao diện: `docs/gui/flutter_compare.png`, `docs/gui/flutter_mask.png`.
Flutter giao tiếp với lõi Python bằng tiến trình nền; không cần Tkinter/Matplotlib để chạy bản mới.
Bản Tkinter cũ đã chuyển vào `docs/archive/tkinter_legacy.zip`, không còn trong source đang chạy.

## Cấu trúc dự án

```text
goi2/
├── flutter_app/           # Giao diện Flutter Linux
│   └── lib/
│       ├── main.dart      # Điểm khởi chạy
│       ├── app.dart       # Theme và ứng dụng
│       ├── studio_config.dart
│       ├── studio_page.dart
│       ├── bridge.dart    # Kết nối tiến trình Python
│       └── widgets/       # Vẽ phổ và vùng mask
├── frequency_filter/
│   ├── fft.py            # FFT/IFFT radix-2 tự viết
│   ├── filters.py        # Các hàm truyền
│   ├── pipeline.py       # Padding, FFT, lọc, IFFT, crop
│   ├── desktop_model.py  # Xử lý preview và xuất dữ liệu
│   ├── desktop_bridge.py # Giao thức JSON-lines cho Flutter
│   └── __main__.py       # CLI
├── tests/                # 20 unit test Python
├── tools/clean_project.py # Dọn cache, giữ release và dữ liệu
├── docs/                 # Báo cáo, bàn giao và minh họa
├── results/              # Ảnh demo, số liệu và kết quả đã lưu
├── demo.py
├── benchmark.py
├── requirements.txt      # NumPy, Pillow
├── requirements-cli-preview.txt # Matplotlib tùy chọn cho CLI
├── mo_flutter.sh
└── mo_giao_dien.sh        # Alias mở Flutter
```

`.venv` và bản build release được giữ trên máy để ứng dụng mở ngay, không đưa lên Git.
Có thể dọn lại bằng `python tools/clean_project.py` từ thư mục `goi2`.
Lệnh này chỉ dọn cache/build tạm; giữ `.venv`, release bundle, tài liệu và `results`.
Cache, build debug và file IDE được loại khỏi bản bàn giao. `pubspec.lock` được giữ để
tái lập dependency. Các ảnh hướng dẫn đóng cửa sổ để lọc trong `docs/huong_dan_mask`
là minh họa cho chế độ CLI; Flutter dùng nút **Xem trước**.

## Bàn giao GitHub

- [Cài trên máy mới và hướng dẫn bàn giao](docs/GITHUB_BAN_GIAO.md)
- [Đối chiếu từng yêu cầu của gói 2](docs/DOI_CHIEU_NHIEM_VU.md)
- [Kết quả kiểm chứng có thể chạy lại](results/handoff/verification.json)

Chạy `.venv/bin/python tools/verify_handoff.py` từ `goi2` để tạo lại số liệu và log.
Các yêu cầu code bắt buộc đã có; đánh giá dataset/Fiji và dàn báo cáo, slide cuối còn phối hợp nhóm.

## Kiểm tra và build

Từ `goi2`:

```bash
.venv/bin/python -m unittest discover -s tests -v
cd flutter_app
flutter analyze
flutter test
flutter test integration_test/studio_test.dart -d linux
flutter build linux --release
```

## Chạy nhanh bằng dòng lệnh

Mở terminal trong thư mục `goi2`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python demo.py
python -m frequency_filter results/demo/noisy.png --filter auto --padding none --radius 2 --output results/my_run
```

Môi trường `.venv` đã tạo trên máy hiện tại dùng Python runtime của Codex và chia sẻ
NumPy/Pillow từ runtime. Khi chuyển máy hãy tạo lại môi trường, không chép `.venv`.

## Các chức năng

```bash
# FFT → xem phổ → IFFT, không lọc (kiểm tra khôi phục ảnh)
python -m frequency_filter anh.png --filter identity --show

# Bandpass theo Gonzalez: Ideal / Gaussian / Butterworth
python -m frequency_filter anh.png --filter bandpass --kind gaussian --center 30 --width 15 --output results/bandpass

# Khử sọc ngang (đổi horizontal thành vertical để khử sọc dọc)
python -m frequency_filter anh.png --filter stripes --direction horizontal --tolerance 5 --output results/stripes

# Notch đặt tay; mỗi --notch u v tự có thêm cặp đối xứng
python -m frequency_filter anh.png --filter notch --kind butterworth --notch 17 11 --radius 2 --order 4 --output results/notch

# Tự dò đỉnh nhiễu; cần chỉnh tham số tùy ảnh
python -m frequency_filter anh.png --filter auto --kind butterworth --exclude-radius 10 --threshold 6 --max-pairs 12 --radius 3 --output results/auto

# Click vào phổ để chặn các vùng hình tròn; đóng cửa sổ để áp dụng và lưu
python -m frequency_filter anh.png --filter mask --interactive-mask --radius 3 --show --output results/mask_hand

# Chọn vùng cần GIỮ: mask khởi đầu toàn đen, click để tô trắng
python -m frequency_filter anh.png --filter mask --interactive-mask --mask-mode pass --radius 5 --output results/mask_pass

# Nạp mask đã lưu, kích thước phải bằng ảnh phổ sau padding
python -m frequency_filter anh.png --filter mask --mask results/mask_hand/mask.npy --output results/reuse

# Công thức Gaussian theo mã ImageJ, padding gương ở giữa khung vuông
python -m frequency_filter anh.png --filter imagej --padding imagej --large 40 --small 3 --output results/imagej
```

`--show` và `--interactive-mask` cần Matplotlib và môi trường desktop hỗ trợ GUI.
Để dùng hai tùy chọn này, chạy `python -m pip install -r requirements-cli-preview.txt`.
Chương trình vẫn chạy toàn bộ luồng CLI và nạp mask PNG/NPY khi không có GUI.
Chế độ cửa sổ CLI cũ chọn vùng hình tròn bằng click và đóng cửa sổ để áp dụng;
giao diện desktop mới ở trên có nút Xem trước và hoàn tác. Chưa có cọ tự do.

Ảnh đầu vào được chuyển về `L` (8-bit). Dùng ảnh xám 8-bit để so số liệu;
không dùng đầu vào float/16-bit nếu muốn bảo toàn dải giá trị.

## Quy ước cần nhớ

- Tính bằng float64/complex128. FFT thuận dấu âm, nghịch chia `P*Q`.
- Phổ và mask đều **đã dịch tâm**. `u` theo hàng/dọc, `v` theo cột/ngang.
- D0, center, width, radius, tọa độ notch tính theo **bin trên ảnh đã padding**.
  Thay padding làm thay đổi tọa độ; notch của ảnh gốc không tự quy đổi.
- Mặc định zero padding lên `nextpow2(2M) × nextpow2(2N)`, đặt ảnh góc trái trên.
  Đây là điều chỉnh để radix-2 chạy được trên ảnh bất kỳ, không luôn đúng `2M×2N`.
- `--padding symmetric` lặp mép theo gương; `edge` lặp giá trị biên;
  `--minimal-padding` bỏ bước nhân 2; `none` không padding và radix-2 yêu cầu hai chiều là lũy thừa 2.
  Backend `--backend numpy` cho phép không padding ảnh kích thước bất kỳ.
- `--padding imagej`: khung vuông lũy thừa 2 >= 1.5*max(M,N), đặt giữa,
  gương có lặp pixel biên, vị trí nửa pixel làm tròn lên như Java Math.round.
- Bandpass Gonzalez bỏ DC; **không autoscale** khi lưu nên ảnh có thể tối.
  Lọc sọc và bandpass ImageJ giữ DC. Có thể giữ thêm vùng trung tâm bằng
  `--protect-radius` khi lọc sọc, nhưng vùng đó sẽ còn nhiễu nếu đỉnh nằm trong đó.
- Mask PNG: đen = 0 chặn, trắng = 1 giữ; xám = suy giảm một phần. Mask NPY giữ số thực.
  `reject` ghép hai vùng bằng min; `pass` ghép bằng max để bảo đảm đối xứng.
- Chỉ clip [0,255] và làm tròn half-up khi xuất PNG. Không kéo giãn histogram.
  Bộ gói 4 tính metric trên PNG để tuân thủ quy ước 8-bit của gói 1.
- Notch dùng khoảng cách tuần hoàn trên lưới DFT để xử lý đúng cạnh Nyquist.
  Butterworth notch dùng số mũ `n` theo gói 1; bandpass dùng `2n`.

## File đầu ra của mỗi lần chạy

| File | Mục đích |
|---|---|
| `filtered.png` | Ảnh kết quả 8-bit cho metric |
| `input.png` | Ảnh vào đã chuyển xám |
| `filtered_float.npy` | Kết quả float, chưa clip |
| `spectrum.png` | Phổ log power, co về 8-bit, chỉ để xem |
| `spectrum_complex.npy` | Phổ phức đã dịch tâm, còn pha |
| `power_raw.npy` | Power spectrum = abs(F)^2, chưa log/scale |
| `mask.npy`, `mask.png` | Hàm truyền H thực và bản xem 8-bit |
| `config.json` | Tham số, kích thước padding, offset cắt, đỉnh dò, sai số ảo |

## Bàn giao và báo cáo

- `docs/BAN_GIAO.md`: API và điểm cần thống nhất với gói 3/4.
- `docs/CHUONG_4.md`: bản nháp chương 4 và nội dung 2 slide.
- `tests/test_core.py`: kiểm thử toán học và lọc.
- `benchmark.py`: đo riêng FFT, ghi CSV, có NumPy và SciPy nếu đã cài.
- `demo.py`: tạo ảnh sin tổng hợp và so tự dò/đặt tay. Đây là demo, không thay dataset gói 4.

## Trạng thái đối chiếu Fiji

Công thức và cách padding tham khảo `Gói 1.docx` và mã nguồn chính thức:
https://github.com/imagej/ImageJ/blob/master/ij/plugin/filter/FFTFilter.java

**Chưa xác nhận tương đương số liệu trên Fiji.** Python dùng float64 còn FHT ImageJ dùng float32;
gói 3 cần ghi phiên bản, tắt Autoscale/Saturate, xuất H và ảnh ra để đối chiếu.
Bandpass Gonzalez và bandpass ImageJ là hai cấu hình khác nhau; không đồng nhất tham số.
