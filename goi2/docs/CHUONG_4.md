# Chương 4. Cài đặt Python và cải tiến — bản nháp

Bản này mô tả code hiện có, chưa dàn trang thành 6 trang báo cáo.
Các số liệu dưới đây là kiểm chứng tại máy phát triển, chưa phải thực nghiệm đầy đủ của chương 5.

## 4.1 Kiến trúc hệ thống

Hệ thống nhận ảnh mức xám 8-bit, chuyển sang float64, padding, biến đổi Fourier,
xây dựng hàm truyền H, nhân phổ, biến đổi ngược và cắt về kích thước gốc.
Khi lưu ảnh, kết quả được giới hạn vào [0,255], làm tròn half-up và chuyển thành uint8.
Giá trị float chưa cắt được lưu riêng để thuận tiện phân tích.

Code chia thành `fft.py` (biến đổi), `filters.py` (hàm truyền và dò đỉnh),
`pipeline.py` (padding, FFT, IFFT, crop), `desktop_model.py` (preview/xuất dữ liệu),
`desktop_bridge.py` (kết nối Flutter), `__main__.py` (dòng lệnh/masking).
`benchmark.py` cho phép gói 4 đo riêng thời gian FFT.

## 4.2 Cài đặt FFT radix-2 và IFFT

FFT một chiều dùng Cooley–Tukey radix-2 dạng lặp. Đầu tiên đảo thứ tự bit của
chỉ số đầu vào, sau đó lần lượt xử lý các nhóm 2, 4, 8, …, N phần tử.
Trong mỗi nhóm, nửa đầu E và nửa sau O được kết hợp bằng phép butterfly:

    t[k] = exp(-2πik/L) * O[k]
    output[k] = E[k] + t[k]
    output[k + L/2] = E[k] - t[k]

Trong đó L là độ dài nhóm tại tầng hiện tại. Code dùng NumPy để thực hiện các
phép toán mảng và số phức, không gọi thư viện FFT trong thuật toán radix-2.
Cách xử lý theo khối giúp giảm vòng lặp Python so với đệ quy từng hàng.

FFT hai chiều tận dụng tính tách được: biến đổi theo hàng rồi theo cột.
IFFT được tính bằng liên hợp phức:

    IFFT2(F) = conj(FFT2(conj(F))) / (P*Q)

Độ phức tạp thời gian O(PQ(log₂P + log₂Q)), bộ nhớ làm việc O(PQ).
Độ dài từng chiều phải là lũy thừa 2; đầu vào vi phạm bị từ chối rõ ràng.

## 4.3 Padding, dịch tâm và power spectrum

Mặc định P=nextpow2(2M), Q=nextpow2(2N), ảnh đặt ở góc trái trên khung zero.
Có thêm padding gương, lặp biên, không padding và cấu hình theo ImageJ.
Chế độ theo ImageJ chọn khung vuông lũy thừa 2 tối thiểu không nhỏ hơn 1,5 lần
chiều lớn nhất, đặt ảnh giữa khung và lặp gương có lặp pixel biên.

Dịch tâm bằng phép roll nửa kích thước từng chiều; phép nghịch dùng số dịch âm.
Phổ phức sau dịch tâm vẫn giữ cả biên độ và pha. Power spectrum thô là |F|².
Bản hiển thị dùng log(1+|F|²), sau đó co về 8-bit. Hai bản có mục đích khác nhau:
file thô dùng đối chiếu số liệu, ảnh hiển thị dùng xác định vị trí đỉnh nhiễu.

Padding giảm tương tác mép do tính tuần hoàn, nhưng không bảo đảm loại bỏ hoàn toàn
wraparound đối với mọi bộ lọc có đáp ứng xung dài. Padding zero có thể tạo gián đoạn
ở biên; padding gương cũng thay đổi phổ và có thể gây rò phổ của nhiễu sin.

## 4.4 Bộ lọc và masking

Bandpass cài ba dạng Ideal, Gaussian, Butterworth theo công thức gói 1,
với tâm dải C0 và độ rộng W tính bằng bin trên phổ đã padding.
Tại các điểm có phép chia cho 0, chương trình gán giá trị theo giới hạn toán học.
Bandpass Gonzalez loại DC nên ảnh ra có thể tối khi lưu mà không autoscale.

Notch reject được xây dựng theo từng cặp (uk,vk), (-uk,-vk). Có ba dạng Ideal,
Gaussian và Butterworth. Khoảng cách modulo trên lưới DFT giữ đối xứng ở biên Nyquist.
Phần notch pass dùng hàm truyền 1-H để khôi phục phần đã loại khi cần phân tích.

Suppress Stripes áp dụng hệ số Gaussian theo khoảng cách tới trục phổ.
Sọc ngang biến thiên theo hàng, có năng lượng trên cột giữa phổ; sọc dọc có năng lượng
trên hàng giữa. Bộ lọc giữ DC và cho phép giữ thêm một đĩa trung tâm theo tham số.

Mask thủ công có thể nạp từ PNG/NPY hoặc chọn vùng hình tròn bằng click trên phổ.
Mỗi vùng được ghép với vùng đối xứng theo modulo kích thước phổ. Chế độ chặn dùng
phép min giữa hai nửa; chế độ giữ dùng phép max. Giao diện desktop có hoàn tác vùng cuối và xóa mask; chưa có cọ tự do.
Trước IFFT, chương trình kiểm tra H hữu hạn, nằm trong [0,1], đối xứng và đúng kích thước.

## 4.5 Cải tiến tự dò đỉnh nhiễu

Bộ dò thực hiện:

1. Tính S=log(1+|F|).
2. Bỏ vùng trung tâm bán kính r0.
3. Đặt ngưỡng median(S)+k*MAD(S) trên vùng còn lại.
4. Chọn cực đại cục bộ trong cửa sổ 7×7.
5. Loại mức biên độ thấp hơn 10⁻¹⁰ lần biên độ lớn nhất để tránh nhận sai sai số số học.
6. Ghép cặp đối xứng, xếp theo độ mạnh và giới hạn số cặp.
7. Đặt notch tại các đỉnh thu được.

Đây là heuristic: cấu trúc tuần hoàn thật của ảnh cũng có thể tạo đỉnh lớn.
Ảnh biên rõ, phổ rò hoặc nhiễu thay đổi theo không gian cần chỉnh tham số.
Chưa kết luận phương pháp tự dò tốt hơn đặt tay trên dataset thực.

## 4.6 Kiểm chứng và kết quả demo

Có 20 unit test Python đã chạy thành công (12 lõi, 5 model desktop, 3 bridge),
bao gồm FFT đầu vào thực/phức, kích thước chữ nhật, đối chiếu NumPy, roundtrip, Parseval,
sin biết trước, padding/crop, mask đối xứng/Nyquist, hướng sọc, bộ dò và lưu file.
Flutter có 4 kiểm thử widget/tọa độ, 1 kiểm thử tích hợp với Python thật và build Linux đạt.

Với ảnh ngẫu nhiên chuẩn float64 64×64, seed 14:

| Đại lượng | Giá trị đo |
|---|---:|
| Sai số tuyệt đối FFT lớn nhất so NumPy | 1,53×10⁻¹³ |
| Sai số FFT chia cho max(abs(F_reference)) | 8,94×10⁻¹⁶ |
| Sai số khôi phục lớn nhất | 1,28×10⁻¹⁵ |
| Sai số tương đối Parseval | 0 ở độ chính xác phép đo này |

Sai số Parseval bằng 0 là kết quả phép đo dấu phẩy động cụ thể, không phải
bằng chứng tính toán chính xác tuyệt đối. Số liệu có thể tái lập bằng
`tools/verify_handoff.py`, chi tiết trong `results/handoff/verification.json`.

Demo dùng hai PNG sạch/nhiễu đã lượng tử hóa 8-bit, 128×128, nhiễu sin biên độ 20
trước lượng tử hóa tại (17,11), không padding. Bán kính mask/notch 3, Butterworth bậc 4:

| Trường hợp | MSE | PSNR (dB) |
|---|---:|---:|
| Ảnh nhiễu | 199,93738 | 25,12186 |
| Mask nhị phân đặt tay như GUI | 0,21570 | 54,79234 |
| Notch Butterworth đặt tay | 0,23242 | 54,46803 |
| Notch Butterworth tự dò | 0,23242 | 54,46803 |

Tự dò tìm đúng một cặp đỉnh, nên bằng notch Butterworth đặt tay trong demo này.
Mask tay nhị phân và notch Butterworth có họ hàm truyền khác nhau; chênh lệch giữa
hai hàng đó không chứng minh sự hơn/kém của thuật toán dò đỉnh. Chưa đo thời gian
chọn bằng tay của con người. Không suy rộng kết quả từ ảnh trơn sang dataset thực.

Các ảnh kết quả, cấu hình và CSV ở `results/handoff/`; `demo.py` dùng cùng đầu vào
PNG lượng tử hóa và bán kính 3 để khớp thao tác mặc định trên giao diện.

## 4.7 Phần cần bổ sung trước khi nộp

Gói 4 bổ sung kết quả trên dataset, PSNR/SSIM, năng lượng đỉnh và thời gian dò.
Giao diện chính là Flutter Linux, dùng tiến trình Python riêng để xử lý ảnh.
Khi đổi tham số hoặc mask, nút lưu bị khóa đến khi có preview mới.
Ảnh preview dùng cùng dải [0,255] như file xuất; file lưu giữ kích thước gốc.
Phần xử lý dùng lại lõi FFT và các bộ lọc, không thay đổi quy ước của chương 2.
Điểm khởi chạy: `bash mo_flutter.sh`. Bản Tkinter trước đây chỉ lưu trữ để tham khảo.
Gói 3 cung cấp dữ liệu Fiji cùng phiên bản và cấu hình tắt Autoscale/Saturate.
Chưa xác nhận tương đương ImageJ: float64 và float32 có sai khác, cần kiểm tra cả
padding, DC và chi tiết trục/Nyquist. Mã nguồn tham chiếu:
https://github.com/imagej/ImageJ/blob/master/ij/plugin/filter/FFTFilter.java

## Nội dung đề xuất cho 2 slide

Slide 1 — Cài đặt: luồng ảnh → padding → FFT radix-2 → H·F → IFFT → crop;
ảnh phổ, mask, ảnh ra; bảng sai số FFT, roundtrip và Parseval.

Slide 2 — Cải tiến: sơ đồ dò đỉnh bằng MAD và cực đại cục bộ; ảnh sạch/nhiễu/đặt tay/tự dò;
bảng demo MSE/PSNR; ghi rõ demo tổng hợp và thêm kết quả dataset thực từ gói 4 sau.


## Cập nhật giao diện Flutter

Giao diện chính đã chuyển sang Flutter Linux (source `flutter_app/lib`). Lõi Python giữ
FFT/IFFT radix-2 và các bộ lọc. Flutter khởi chạy `frequency_filter.desktop_bridge` bằng
Process.start, gửi/nhận JSON-lines qua stdin/stdout. Lõi xử lý ảnh ở tiến trình riêng nên
không khóa luồng giao diện. Không có web server hoặc dịch vụ mạng.

Có hộp thoại mở/lưu file, hai tab so sánh và phổ/mask, hoàn tác mask, cảnh báo preview cũ,
xuất bộ dữ liệu. Tọa độ click được quy đổi theo vùng ảnh thực tế sau khi fit vào panel,
loại bỏ vùng đệm ngoài ảnh. Preview được thu nhỏ tối đa 1400 pixel mỗi chiều; ảnh xuất
và metric vẫn dùng ảnh đầy đủ kích thước. Phần đối chiếu Fiji chưa thay đổi trạng thái.

Kiểm thử: 20 Python unit test, 4 Flutter test và 1 kiểm thử tích hợp trên desktop với
lõi Python thật. Kiểm thử tích hợp mock đường dẫn hộp thoại để tự động hóa và kiểm tra
luồng mở ảnh, chọn mask, preview, lưu PNG, xuất bộ dữ liệu, khóa lưu sau hoàn tác.
