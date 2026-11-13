# Fourier Studio · Flutter Linux

Giao diện desktop cho gói 2 của Nhóm 14. Flutter dựng toàn bộ giao diện, chọn/lưu file
qua plugin `file_selector`; Python chạy dưới dạng tiến trình con, giao tiếp bằng JSON-lines
qua stdin/stdout. Không chạy HTTP server, không dùng Tkinter trong giao diện này.

## Mở ứng dụng đã build

Từ thư mục gốc repository:

```bash
bash goi2/mo_flutter.sh
```

`mo_giao_dien.sh` cũng mở bản Flutter. Launcher tự tìm thư mục dự án, dùng `.venv/bin/python`
và binary tại `build/linux/x64/release/bundle/fourier_studio`.

## Source

- `lib/main.dart`: điểm khởi chạy.
- `lib/app.dart`: theme, font và ứng dụng.
- `lib/studio_config.dart`: màu, tên bộ lọc và tham số mặc định.
- `lib/studio_page.dart`: trạng thái giao diện và thao tác người dùng.
- `lib/bridge.dart`: giao tiếp với Python.
- `lib/widgets/spectrum_overlay.dart`: tọa độ ảnh và lớp đánh dấu mask.
- `../frequency_filter/desktop_model.py`: xử lý preview, lưu và xuất dữ liệu.

## Cách sử dụng

1. Bấm **Mở ảnh** hoặc **Chọn ảnh từ máy**. Có thể thử ảnh mẫu mà không nhập đường dẫn.
2. Chọn phương pháp ở bên trái, thay tham số và bấm **Xem trước**.
3. Tab **So sánh** hiển thị ảnh gốc và ảnh sau lọc cùng thang 0–255.
4. Tab **Phổ & Mask** hiển thị phổ log công suất và hàm truyền H.
   Chế độ **Mask thủ công**: click trên phổ, vùng đối xứng tự được thêm; có hoàn tác và xóa mask.
   Preview mask và ảnh đầu ra chỉ cập nhật sau khi bấm **Xem trước**. Vòng xanh đánh dấu lựa chọn đang chỉnh.
5. **Lưu ảnh** cho phép chọn tên/thư mục PNG, TIFF, BMP. Ảnh lưu giữ độ phân giải gốc.
6. Nút **hình thư mục** cạnh Lưu ảnh xuất ảnh, phổ thô, mask và cấu hình JSON vào thư mục chọn.

Cột thiết lập có thể cuộn. Khi ảnh/phương pháp/tham số/mask thay đổi, kết quả cũ có nhãn
chưa cập nhật và nút lưu bị khóa. Đổi padding, backend hoặc chặn/giữ sẽ xóa các vùng mask cũ.

Bộ lọc: FFT/IFFT không lọc, bandpass Ideal/Gaussian/Butterworth, Suppress Stripes,
mask thủ công, notch tự dò, bandpass theo ImageJ. Quy ước tần số và lưu 8-bit giữ nguyên
như tài liệu gói 2. Notch tự dò là heuristic; phần đối chiếu Fiji vẫn chờ dữ liệu gói 3.

## Build lại sau khi sửa code

Từ thư mục gốc repository:

```bash
cd goi2/flutter_app
flutter pub get
flutter build linux --release
```

Công cụ build Linux: clang, cmake, ninja-build, libgtk-3-dev. Python backend chỉ cần NumPy
và Pillow trong `../requirements.txt`, không cần Matplotlib/Tkinter.

```bash
flutter analyze
flutter test
flutter test integration_test/studio_test.dart -d linux
```

Kiểm thử tích hợp chạy cửa sổ Flutter và lõi Python thật; mock kết quả chọn đường dẫn của
hộp thoại để tự động hóa, kiểm tra mở ảnh có dấu, mask, preview, lưu và xuất bộ dữ liệu.
Ảnh chụp giao diện được ghi vào `../docs/gui/flutter_*.png`.

Widget tests kiểm tra trạng thái ban đầu, khóa lưu, bảng tham số ở chiều rộng tối thiểu,
và quy đổi tọa độ mask khi ảnh không vuông/thumbnail làm tròn kích thước. Bộ Python có 20 unit test.

## Phạm vi đóng gói

Bản hiện tại chạy trên Linux trong thư mục dự án này và dùng môi trường Python đi kèm.
Khi chuyển máy cần tạo lại `.venv`, cài requirements, rồi build hoặc chép toàn bộ bundle
với các thư viện Linux tương ứng. Chưa đóng gói Python vào một file cài đặt độc lập.
Font Noto Sans dùng cho nội dung; DejaVu Sans dùng cho tiêu đề nhóm và nhãn nhỏ để hiển thị dấu tiếng Việt rõ hơn.
Giấy phép ở `assets/fonts/LICENSE-NOTO.txt` và `assets/fonts/LICENSE-DEJAVU.txt`.
