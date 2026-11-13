# Hướng dẫn bàn giao qua GitHub

## Những gì đưa lên repository

Đưa cả thư mục project gốc, gồm README, tài liệu nhóm và `goi2`. Giữ `pubspec.lock`,
font kèm giấy phép, ảnh demo, số liệu kiểm chứng và source Linux runner.
`.gitignore` đã loại `.venv`, cache, build, cấu hình máy và các lần chạy riêng.
Không cần đưa binary release lên Git để chạy từ source.

Không xóa `results/demo`: nút ảnh mẫu, các phép thử và demo dùng những ảnh này.
`results/my_run`, `results/mask_hand` là kết quả riêng trên máy, không thuộc source upload.
Bản Tkinter trong ZIP chỉ để tham khảo, Flutter không phụ thuộc vào nó.

## Máy nhận cần cài gì?

Đã kiểm chứng trên Ubuntu Linux x64, Python 3.12, Flutter 3.44.4 / Dart 3.12.2.
`pubspec.yaml` yêu cầu Dart >=3.12.2,<4.0.0; không coi một Flutter SDK cũ bất kỳ là đủ.
Flutter SDK phải có trong PATH (`flutter --version`).

Sau khi clone repository, từ thư mục gốc:

```bash
sudo apt-get install -y python3-venv python3-pip clang cmake ninja-build libgtk-3-dev
cd goi2
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd flutter_app
flutter pub get
flutter build linux --release
cd ..
bash mo_flutter.sh
```

Nếu chỉ dùng code Python/CLI, không cần cài Flutter hay các công cụ GTK.
CLI xem biểu đồ bằng `--show`/`--interactive-mask` cần thêm
`python -m pip install -r requirements-cli-preview.txt` trong môi trường đã kích hoạt.
GUI Flutter chỉ cần NumPy/Pillow ở phía Python.

## Kiểm tra sau khi clone

Từ `goi2`:

```bash
.venv/bin/python tools/verify_handoff.py
.venv/bin/python tools/check_source_checkout.py
.venv/bin/python -m frequency_filter results/demo/noisy.png --filter auto --padding none --radius 3 --kind butterworth --output results/clone_test
cd flutter_app
flutter analyze
flutter test
flutter test integration_test/studio_test.dart -d linux
```

Test tích hợp cần phiên desktop có màn hình. Nó dùng mock cho lựa chọn đường dẫn hộp thoại;
những phép FFT, lọc, PNG và NPY vẫn được chạy bằng Python thật.
Các file trong `results/handoff` là báo cáo để nhóm đối chiếu; thời gian chạy phụ thuộc máy.

## Demo thủ công ngắn

1. Bấm **Mở ảnh**, chọn `goi2/results/demo/noisy.png`.
2. Chọn **Mask thủ công**, **Chặn vùng chọn**, radius **3**, **Không padding**.
3. Bấm **Xem trước** để tạo phổ đúng kích thước.
4. Click đỉnh trên-trái: cột 53/hàng 47 trên phổ 128×128 (chỉ số từ 0).
   Cặp đối xứng tự được thêm. Bấm **Xem trước** lần nữa.
5. Tab **So sánh** để xem, **Lưu ảnh** để chọn file; nút thư mục xuất bộ dữ liệu.
6. Thử **Notch tự dò**, chọn **Butterworth**, radius **3**, bậc **4**, không padding,
   bỏ tâm **10**, ngưỡng **6**, tối đa **12** cặp; xem lại vị trí đỉnh trước khi lưu.

Không dùng tọa độ trên cho ảnh khác hoặc cấu hình padding khác.

## Tài liệu gửi cho nhóm

- `DOI_CHIEU_NHIEM_VU.md`: từng yêu cầu, bằng chứng và mục còn chờ.
- `BAN_GIAO.md`: API cho gói 3/4, quy ước padding và metric.
- `CHUONG_4.md`: bản nháp nội dung báo cáo, cần dàn trang và số liệu cuối.
- `../results/handoff/verification.json`: phiên bản, kiểm thử Python và sai số FFT.
- `../results/handoff/flutter_review.json`: kết quả kiểm tra Flutter/Linux.
- `../results/handoff/source_checkout.json`: kiểm tra ignore và bản sao chỉ source.
- `../results/handoff/manual_vs_auto.csv`: so mask tay, notch đặt tay và tự dò.
- `../results/handoff/comparison_config.json`: cấu hình tái lập phép so sánh.

Bạn tự tạo repository/commit/push bằng tài khoản của mình. Lần rà soát này chỉ chuẩn bị
source và kiểm chứng local, không thực hiện đăng tải lên GitHub.
