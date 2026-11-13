# Đối chiếu nhiệm vụ gói 2 · bàn giao code

Ngày rà soát: 13/11/2026. Nguồn yêu cầu: mục “Gói 2. Python (chương 4)” trong
`Phân công XLA_Nhóm 14.docx`. Phạm vi bàn giao là code và bản nháp chương 4;
đánh giá đầy đủ trên dataset và Fiji còn cần phối hợp gói 3/4.

| Yêu cầu được giao | Trạng thái | Bằng chứng / cách kiểm tra |
|---|---|---|
| Tự cài FFT 2D radix-2 | Đã có | `frequency_filter/fft.py`: đảo bit, butterfly, hàng rồi cột; không gọi `numpy.fft` trong module này |
| Tự cài IFFT | Đã có | `ifft2d`: liên hợp → FFT → liên hợp → chia P×Q |
| Đối chiếu với `numpy.fft` | Đạt kiểm thử | `tests/test_core.py`, `results/handoff/verification.json` |
| Padding | Đã có | Zero/gương/lặp biên; mặc định nextpow2(2M), nextpow2(2N); thêm chế độ ImageJ và không padding |
| Dịch tâm phổ | Đã có | `fftshift`, `ifftshift` tự cài bằng roll; kiểm tra cả kích thước chẵn/lẻ |
| Power Spectrum | Đã có | `power_spectrum = abs(F)^2`; PNG log để xem, NPY thô để đo |
| Bộ lọc Bandpass | Đã có | Ideal, Gaussian, Butterworth trong `filters.py`; thêm cấu hình riêng theo ImageJ |
| Suppress Stripes | Đã có | Sọc ngang/dọc, tolerance, bảo vệ vùng tâm; unit test xác nhận đúng hướng |
| Masking thủ công | Đã có | CLI nạp PNG/NPY; Flutter click vùng tròn, chặn/giữ, đối xứng, hoàn tác và xóa |
| Chương trình nạp → phổ → lọc → lưu | Đã có | Flutter Linux + CLI; kiểm thử tích hợp dùng lõi Python thật |
| Unit test khôi phục ảnh | Đạt | `IFFT(FFT(x)) ≈ x`, ảnh thực/phức, nhiều kích thước |
| Unit test Parseval | Đạt | Năng lượng phổ chia P×Q so với năng lượng ảnh |
| Unit test sin biết trước | Đạt | Hai đỉnh ±(5,3) trên ảnh 64×64, biên độ 2048 |
| Code đo benchmark cho gói 4 | Đã có | `benchmark.py`, đo FFT thuận riêng, seed cố định, warmup, median/min; SciPy nếu cài |
| Cải tiến tự dò đỉnh nhiễu | Đã có, kiểm chứng tổng hợp | MAD + cực đại cục bộ + ghép cặp đối xứng; `find_noise_peaks` |
| Số đo tự dò so với tô tay | Đã có trên demo | `results/handoff/manual_vs_auto.csv`; mask tay đúng loại hình tròn của GUI, thêm đối chứng notch cùng họ |
| Giao diện mask tiện lợi (nếu kịp) | Đã có mức cơ bản | Click, bán kính, chặn/giữ, hoàn tác, preview; chưa có cọ tự do |
| Phân tích sâu S(r), S(θ) (nếu kịp) | Chưa làm | Không tính vào phần bắt buộc |
| Chương 4, khoảng 6 trang / 2 slide | Có bản nháp nội dung | `docs/CHUONG_4.md`; chưa dàn trang 6 trang hoặc tạo file slide cuối |

## Phép thử được thực hiện

- Python: 20 unit test; log ở `results/handoff/python_tests.txt`.
- Flutter: 4 test (widget/trạng thái/đổi tọa độ mask), `flutter analyze` và build Linux.
- Tích hợp: 1 test chạy app Flutter và Python thật. Đường dẫn hộp thoại được mock để
  tự động hóa; có kiểm tra mở ảnh có dấu, mask, preview, lưu, xuất, hủy mở, từ chối ghi đè,
  khóa lưu sau khi sửa mask. Đây không phải kiểm thử chọn file bằng tay trên mọi hệ điều hành.
- Regression rà soát này: sửa tọa độ mask trên ảnh lớn không vuông khi thumbnail bị
  làm tròn kích thước; UI dùng tỉ lệ thực của thumbnail để khớp vị trí click.
- Benchmark nhỏ 64/128 chỉ xác nhận script chạy; không thay thực nghiệm hiệu năng của gói 4.

Flutter analyze, 4 test, 1 test tích hợp và build release đã chạy đạt trong lần rà soát này;
bản ghi ở `results/handoff/flutter_review.json`. Kiểm tra source-only và CLI sau sao chép
ở `results/handoff/source_checkout.json`; phép thử này dùng runtime Python đã cài NumPy/Pillow,
không thay cho một lần cài pip trên máy mới.
Báo cáo số liệu Python có thể chạy lại bằng:

```bash
cd goi2
.venv/bin/python tools/verify_handoff.py
```

## Kết quả demo so tự dò và tô tay

Nguồn: hai ảnh PNG `results/demo/clean.png`, `noisy.png` đã lượng tử hóa 8-bit.
Ảnh 128×128, không padding, nhiễu sin (17,11), biên độ 20 trước lượng tử hóa.
Mask tay: click hàng 47/cột 53, radius 3, tự thêm vùng đối xứng.
Notch tự dò: Butterworth radius 3, bậc 4, loại vùng tâm radius 10, ngưỡng 6×MAD.

| Phương pháp | MSE | PSNR (dB) |
|---|---:|---:|
| Ảnh nhiễu | 199.93738 | 25.12186 |
| Mask tay nhị phân như GUI | 0.21570 | 54.79234 |
| Notch Butterworth đặt tay | 0.23242 | 54.46803 |
| Notch Butterworth tự dò | 0.23242 | 54.46803 |

Trong ví dụ đơn giản này, tự dò tìm đúng cặp ±(17,11), cho kết quả bằng notch
Butterworth đặt tay. So với mask tay nhị phân, họ hàm truyền khác nhau nên số đo hơi khác;
không quy kết chênh lệch này cho thuật toán dò đỉnh. Chưa đo thời gian chọn bằng tay của
con người. Không dùng demo trơn để kết luận chất lượng trên ảnh thật hoặc tự dò luôn tốt hơn.

## Điều kiện / phần còn chờ nhóm

1. Gói 3: phiên bản Fiji, macro, raw power, ảnh H và ảnh ra, cùng cấu hình padding,
   tắt Autoscale/Saturate. Chưa có dữ liệu nên chưa kết luận khớp Fiji.
2. Gói 4: dataset sạch/nhiễu, bảng cấu hình, PSNR/SSIM, năng lượng đỉnh, benchmark
   đầy đủ và so với lọc không gian. Code gói 2 đã có API/đầu ra để chạy.
3. Gói 1/nhóm: ghép và rà chương 4, thống nhất công thức/tham số, dàn báo cáo và slide.
4. GUI hiện chỉ có runner Linux. Máy Windows/macOS chưa được kiểm thử; có thể dùng
   Python CLI nhưng không coi là đã bàn giao GUI đa nền tảng.

Kết luận: **đủ phần code bắt buộc để bàn giao gói 2**, có cải tiến tự dò và số đo tổng hợp.
**Chưa phải bộ kết quả thực nghiệm/báo cáo cuối cùng của cả nhóm.**
