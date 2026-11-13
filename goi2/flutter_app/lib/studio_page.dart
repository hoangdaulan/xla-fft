import 'dart:io';
import 'dart:math' as math;
import 'package:file_selector/file_selector.dart';
import 'package:flutter/material.dart';
import 'package:path/path.dart' as p;
import 'bridge.dart';

import 'studio_config.dart';
import 'widgets/spectrum_overlay.dart';

class StudioPage extends StatefulWidget {
  const StudioPage({super.key});
  @override
  State<StudioPage> createState() => _StudioPageState();
}

class _StudioPageState extends State<StudioPage> {
  final bridge = PythonBridge();
  Map<String, dynamic> settings = {...defaults};
  Map<String, dynamic>? source, result;
  List<List<num>> actions = [];
  final fields = <String, TextEditingController>{};
  bool busy = false, dirty = true, spectrumTab = false;
  String status = 'Sẵn sàng · Mở một ảnh để bắt đầu';
  int revision = 0;

  bool get canSave => result != null && !dirty && !busy;
  String get mode => settings['filter'] as String;
  bool get spectrumValid =>
      result != null &&
      result!['config']['padding'] ==
          (mode == 'imagej' ? 'imagej' : settings['padding']) &&
      result!['config']['backend'] == settings['backend'];

  @override
  void initState() {
    super.initState();
    for (final entry in defaults.entries) {
      if (entry.value is num) {
        fields[entry.key] = TextEditingController(
          text: numberText(entry.value),
        );
      }
    }
  }

  String numberText(dynamic value) =>
      value is num && value == value.roundToDouble()
      ? value.toInt().toString()
      : '$value';
  @override
  void dispose() {
    bridge.dispose();
    for (final controller in fields.values) {
      controller.dispose();
    }
    super.dispose();
  }

  void change(String key, dynamic value) {
    setState(() {
      settings[key] = value;
      revision++;
      dirty = true;
      if (['padding', 'backend', 'mask_mode'].contains(key)) actions = [];
      if (key == 'filter' && ['mask', 'auto'].contains(value)) {
        spectrumTab = true;
      }
      status = 'Đã đổi thiết lập · Bấm Xem trước để cập nhật';
    });
  }

  void notify(String text, {bool error = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(text),
        backgroundColor: error ? const Color(0xFFB74252) : ink,
        behavior: SnackBarBehavior.floating,
        width: math.min(640, MediaQuery.sizeOf(context).width - 40),
      ),
    );
  }

  Future<void> load({bool demo = false}) async {
    if (busy) return;
    try {
      String? path;
      if (!demo) {
        final file = await openFile(
          acceptedTypeGroups: const [
            XTypeGroup(
              label: 'Ảnh',
              extensions: ['png', 'jpg', 'jpeg', 'bmp', 'tif', 'tiff'],
            ),
          ],
        );
        if (file == null || !mounted) return;
        path = file.path;
      }
      setState(() {
        busy = true;
        status = 'Đang mở ảnh…';
      });
      final data = await bridge.request(
        demo ? 'demo' : 'load',
        demo ? {} : {'path': path},
      );
      if (!mounted) return;
      setState(() {
        source = data;
        result = null;
        actions = [];
        dirty = true;
        revision++;
        busy = false;
        spectrumTab = false;
        status = data['source_mode'] == 'L'
            ? 'Đã mở ảnh mức xám'
            : 'Đã chuyển ảnh sang mức xám 8-bit';
      });
      await preview();
    } catch (error) {
      if (!mounted) return;
      setState(() {
        busy = false;
        status = 'Chưa mở được ảnh';
      });
      notify('$error', error: true);
    }
  }

  List<String> get activeNumbers => switch (mode) {
    'bandpass' => [
      'center',
      'width',
      if (settings['kind'] == 'butterworth') 'order',
    ],
    'stripes' => ['tolerance', 'protect'],
    'mask' => ['radius'],
    'auto' => [
      'radius',
      if (settings['kind'] == 'butterworth') 'order',
      'exclude',
      'threshold',
      'max_pairs',
    ],
    'imagej' => ['large', 'small'],
    _ => [],
  };

  Map<String, dynamic> validatedSettings() {
    final values = Map<String, dynamic>.from(settings);
    for (final key in activeNumbers) {
      final number = num.tryParse(fields[key]!.text);
      if (number == null || !number.isFinite) {
        throw FormatException('Vui lòng nhập số hợp lệ cho ${labels[key]}.');
      }
      if (['order', 'max_pairs'].contains(key) && number != number.round()) {
        throw FormatException('${labels[key]} phải là số nguyên.');
      }
      values[key] = ['order', 'max_pairs'].contains(key)
          ? number.toInt()
          : number.toDouble();
    }
    return values;
  }

  Future<void> preview() async {
    if (busy || source == null) return;
    final stamp = revision;
    try {
      final values = validatedSettings();
      setState(() {
        busy = true;
        status = 'Đang xử lý ảnh…';
      });
      final data = await bridge.request('preview', {
        'settings': values,
        'actions': actions,
      });
      if (!mounted) return;
      setState(() {
        busy = false;
        if (stamp == revision) {
          result = data;
          dirty = false;
          status =
              'Đã cập nhật · ${(data['seconds'] as num).toStringAsFixed(3)} giây';
        } else {
          status = 'Thiết lập đã đổi · Hãy chạy Xem trước lại';
        }
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        busy = false;
        dirty = true;
        status = 'Kiểm tra lại tham số';
      });
      notify('$error', error: true);
    }
  }

  void clickMask(Offset position, Size size) {
    if (busy || mode != 'mask' || !spectrumValid) return;
    final shape = result!['padded_shape'] as List;
    final rect = fittedImageRect(
      size,
      shape,
      previewShape: result!['spectrum_preview_shape'] as List?,
    );
    if (!rect.contains(position)) return;
    final radius = num.tryParse(fields['radius']!.text);
    if (radius == null || !radius.isFinite || radius <= 0) {
      notify('Bán kính mask phải lớn hơn 0.', error: true);
      return;
    }
    final row =
        ((position.dy - rect.top) / rect.height * shape[0]).floor().clamp(
              0,
              shape[0] - 1,
            )
            as int;
    final col =
        ((position.dx - rect.left) / rect.width * shape[1]).floor().clamp(
              0,
              shape[1] - 1,
            )
            as int;
    setState(() {
      actions = [
        ...actions,
        [row, col, radius],
      ];
      dirty = true;
      revision++;
      status = 'Đã chọn ${actions.length} vùng và cặp đối xứng · Bấm Xem trước';
    });
  }

  void undo({bool clear = false}) {
    if (busy || actions.isEmpty) return;
    setState(() {
      actions = clear ? [] : actions.sublist(0, actions.length - 1);
      dirty = true;
      revision++;
      status = 'Mask đã đổi · Bấm Xem trước';
    });
  }

  Future<void> save({bool bundle = false}) async {
    if (!canSave) return;
    try {
      String? target;
      if (bundle) {
        target = await getDirectoryPath(confirmButtonText: 'Xuất tại đây');
        if (target == null || !mounted) return;
        const names = [
          'filtered.png',
          'input.png',
          'spectrum.png',
          'mask.png',
          'mask.npy',
          'filtered_float.npy',
          'power_raw.npy',
          'spectrum_complex.npy',
          'config.json',
        ];
        if (names.any((name) => File(p.join(target!, name)).existsSync())) {
          final agree = await showDialog<bool>(
            context: context,
            builder: (context) => AlertDialog(
              title: const Text('Ghi đè kết quả đã có?'),
              content: const Text(
                'Một số file trong thư mục này trùng tên với bộ kết quả. Bạn có muốn thay thế?',
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context, false),
                  child: const Text('Hủy'),
                ),
                FilledButton(
                  onPressed: () => Navigator.pop(context, true),
                  child: const Text('Ghi đè'),
                ),
              ],
            ),
          );
          if (agree != true) return;
        }
      } else {
        final location = await getSaveLocation(
          suggestedName:
              '${p.basenameWithoutExtension(source!['name'] as String)}_filtered.png',
          acceptedTypeGroups: const [
            XTypeGroup(label: 'PNG', extensions: ['png']),
            XTypeGroup(label: 'TIFF', extensions: ['tif', 'tiff']),
            XTypeGroup(label: 'BMP', extensions: ['bmp']),
          ],
        );
        if (location == null || !mounted) return;
        target = location.path;
        if (p.extension(target).isEmpty) {
          target = '$target.png';
          if (File(target).existsSync()) {
            final agree = await showDialog<bool>(
              context: context,
              builder: (context) => AlertDialog(
                title: const Text('Ghi đè ảnh đã có?'),
                content: Text('Ảnh $target đã tồn tại. Bạn có muốn thay thế?'),
                actions: [
                  TextButton(
                    onPressed: () => Navigator.pop(context, false),
                    child: const Text('Hủy'),
                  ),
                  FilledButton(
                    onPressed: () => Navigator.pop(context, true),
                    child: const Text('Ghi đè'),
                  ),
                ],
              ),
            );
            if (agree != true) return;
          }
        }
      }
      if (!mounted) return;
      setState(() {
        busy = true;
        status = 'Đang lưu kết quả…';
      });
      await bridge.request(bundle ? 'export' : 'save', {'path': target});
      if (!mounted) return;
      setState(() {
        busy = false;
        status = 'Đã lưu: $target';
      });
      notify(
        bundle
            ? 'Đã xuất ảnh, phổ, mask và cấu hình.'
            : 'Đã lưu ảnh đúng độ phân giải gốc.',
      );
    } catch (error) {
      if (!mounted) return;
      setState(() {
        busy = false;
        status = 'Chưa lưu được kết quả';
      });
      notify('$error', error: true);
    }
  }

  static const labels = {
    'center': 'Tâm dải',
    'width': 'Độ rộng dải',
    'order': 'Bậc Butterworth',
    'radius': 'Bán kính vùng lọc',
    'tolerance': 'Tolerance',
    'protect': 'Bảo vệ vùng tâm',
    'exclude': 'Bỏ qua vùng tâm',
    'threshold': 'Ngưỡng dò đỉnh',
    'max_pairs': 'Số cặp đỉnh tối đa',
    'large': 'Cấu trúc lớn',
    'small': 'Cấu trúc nhỏ',
  };

  Widget drop(
    String key,
    String label,
    Map<String, String> choices, {
    bool enabled = true,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 16),
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 8),
        DropdownButtonFormField<String>(
          initialValue: settings[key] as String,
          key: ValueKey('$key-${settings[key]}'),
          isExpanded: true,
          style: const TextStyle(
            fontFamily: 'NotoSans',
            fontSize: 12,
            color: ink,
          ),
          icon: const Icon(
            Icons.keyboard_arrow_down_rounded,
            size: 18,
            color: muted,
          ),
          items: choices.entries
              .map(
                (e) => DropdownMenuItem(
                  value: e.key,
                  child: Text(e.value, overflow: TextOverflow.ellipsis),
                ),
              )
              .toList(),
          onChanged: busy || !enabled ? null : (v) => change(key, v),
        ),
      ],
    ),
  );

  Widget numberField(String key) {
    final suffix = key == 'tolerance'
        ? '%'
        : ['order', 'max_pairs', 'threshold'].contains(key)
        ? ''
        : mode == 'imagej'
        ? 'px'
        : 'bin';
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            labels[key]!,
            style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
          ),
          const SizedBox(height: 8),
          TextField(
            controller: fields[key],
            enabled: !busy,
            style: const TextStyle(fontSize: 13),
            keyboardType: const TextInputType.numberWithOptions(decimal: true),
            decoration: InputDecoration(
              suffixText: suffix,
              suffixStyle: const TextStyle(fontSize: 11, color: muted),
            ),
            onChanged: (text) {
              setState(() {
                dirty = true;
                revision++;
                status = 'Đã đổi tham số · Bấm Xem trước';
              });
            },
            onSubmitted: (_) => preview(),
          ),
        ],
      ),
    );
  }

  Widget eyebrow(String text) => Padding(
    padding: const EdgeInsets.only(bottom: 15),
    child: Text(
      text,
      style: const TextStyle(
        fontFamily: 'SectionSans',
        color: Color(0xFF687089),
        fontSize: 11,
        fontWeight: FontWeight.w700,
        letterSpacing: 0.25,
      ),
    ),
  );

  Widget sidebar() => Container(
    width: 286,
    decoration: const BoxDecoration(
      color: Colors.white,
      border: Border(right: BorderSide(color: lineColor)),
    ),
    child: Column(
      children: [
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(22),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                eyebrow('NGUỒN ẢNH'),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: canvasColor,
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 36,
                        height: 36,
                        decoration: BoxDecoration(
                          color: violet.withValues(alpha: .1),
                          borderRadius: BorderRadius.circular(9),
                        ),
                        child: const Icon(
                          Icons.image_outlined,
                          color: violet,
                          size: 19,
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              source?['name'] as String? ?? 'Chưa có ảnh',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: const TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const SizedBox(height: 3),
                            Text(
                              source == null
                                  ? 'PNG, JPG, BMP, TIFF'
                                  : '${(source!['shape'] as List)[1]} × ${(source!['shape'] as List)[0]} · Xám 8-bit',
                              style: const TextStyle(
                                fontSize: 10,
                                color: muted,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 26),
                eyebrow('THIẾT LẬP BỘ LỌC'),
                drop('filter', 'Phương pháp', filterNames),
                if (['bandpass', 'auto'].contains(mode))
                  drop('kind', 'Dạng bộ lọc', {
                    'ideal': 'Ideal',
                    'gaussian': 'Gaussian',
                    'butterworth': 'Butterworth',
                  }),
                if (mode == 'stripes')
                  drop('direction', 'Hướng sọc trên ảnh', {
                    'horizontal': 'Sọc ngang',
                    'vertical': 'Sọc dọc',
                  }),
                if (mode == 'mask')
                  drop('mask_mode', 'Thao tác', {
                    'reject': 'Chặn vùng chọn',
                    'pass': 'Giữ vùng chọn',
                  }),
                for (final key in activeNumbers) numberField(key),
                if (mode == 'mask')
                  Row(
                    children: [
                      Expanded(
                        child: OutlinedButton.icon(
                          onPressed: busy || actions.isEmpty
                              ? null
                              : () => undo(),
                          icon: const Icon(Icons.undo_rounded, size: 16),
                          label: const Text(
                            'Hoàn tác',
                            style: TextStyle(fontSize: 11),
                          ),
                        ),
                      ),
                      const SizedBox(width: 8),
                      IconButton.outlined(
                        tooltip: 'Xóa toàn bộ mask',
                        onPressed: busy || actions.isEmpty
                            ? null
                            : () => undo(clear: true),
                        icon: const Icon(Icons.delete_outline, size: 18),
                      ),
                    ],
                  ),
                const Padding(
                  padding: EdgeInsets.symmetric(vertical: 20),
                  child: Divider(height: 1),
                ),
                eyebrow('BIẾN ĐỔI FOURIER'),
                if (mode == 'imagej')
                  const Padding(
                    padding: EdgeInsets.only(bottom: 16),
                    child: Text(
                      'Tự dùng padding gương theo ImageJ.',
                      style: TextStyle(fontSize: 12, color: muted),
                    ),
                  )
                else
                  drop('padding', 'Xử lý biên ảnh', paddingNames),
                drop('backend', 'Thuật toán FFT', {
                  'radix2': 'Radix-2 · tự cài đặt',
                  'numpy': 'NumPy · tham chiếu',
                }),
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF3F0FE),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Text(
                    switch (mode) {
                      'mask' =>
                        'Click trên phổ để chọn vùng. Cặp đối xứng được thêm tự động. Bấm Xem trước để áp dụng.',
                      'auto' =>
                        'Đỉnh mạnh có thể thuộc nội dung ảnh. Kiểm tra vị trí dò trước khi lưu.',
                      'bandpass' =>
                        'Bandpass bỏ DC nên ảnh có thể tối. Ảnh được giữ nguyên thang sáng 0–255.',
                      'imagej' =>
                        'Công thức theo ImageJ. Chưa kiểm chứng số liệu trực tiếp với Fiji.',
                      'stripes' =>
                        'Chọn hướng của sọc nhìn thấy trên ảnh gốc, không phải hướng đỉnh trên phổ.',
                      _ =>
                        'FFT và IFFT không lọc giúp kiểm tra ảnh khôi phục có khớp ảnh đầu vào.',
                    },
                    style: const TextStyle(
                      fontSize: 11,
                      height: 1.65,
                      color: Color(0xFF695897),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
        Container(
          padding: const EdgeInsets.all(20),
          decoration: const BoxDecoration(
            border: Border(top: BorderSide(color: lineColor)),
          ),
          child: SizedBox(
            width: double.infinity,
            child: FilledButton.icon(
              key: const Key('preview'),
              onPressed: busy || source == null ? null : preview,
              icon: busy
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        color: Colors.white,
                      ),
                    )
                  : const Icon(Icons.play_arrow_rounded, size: 20),
              label: Text(
                busy ? 'Đang xử lý…' : 'Xem trước',
                style: const TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
        ),
      ],
    ),
  );

  Widget topbar(bool compact) => Container(
    height: 87,
    padding: const EdgeInsets.symmetric(horizontal: 26),
    decoration: const BoxDecoration(
      color: Colors.white,
      border: Border(bottom: BorderSide(color: lineColor)),
    ),
    child: Row(
      children: [
        Container(
          width: 42,
          height: 42,
          decoration: BoxDecoration(
            color: violet,
            borderRadius: BorderRadius.circular(13),
          ),
          child: const Icon(Icons.waves_rounded, color: Colors.white, size: 27),
        ),
        const SizedBox(width: 13),
        Column(
          mainAxisAlignment: MainAxisAlignment.center,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Fourier Studio',
              style: TextStyle(
                fontSize: 20,
                fontWeight: FontWeight.w700,
                letterSpacing: -.6,
              ),
            ),
            if (!compact)
              const Text(
                'Lọc ảnh mức xám trong miền tần số',
                style: TextStyle(fontSize: 11, color: muted),
              ),
          ],
        ),
        const SizedBox(width: 16),
        if (!compact) badge('NHÓM 14', const Color(0xFFF1EFFA), violet),
        const Spacer(),
        OutlinedButton.icon(
          key: const Key('open'),
          onPressed: busy ? null : () => load(),
          icon: const Icon(Icons.add_photo_alternate_outlined, size: 18),
          label: const Text('Mở ảnh', style: TextStyle(fontSize: 12)),
        ),
        const SizedBox(width: 10),
        IconButton.outlined(
          key: const Key('export'),
          tooltip: 'Xuất bộ kết quả: ảnh, phổ, mask và cấu hình',
          onPressed: canSave ? () => save(bundle: true) : null,
          icon: const Icon(Icons.folder_zip_outlined, size: 19),
        ),
        const SizedBox(width: 10),
        FilledButton.icon(
          key: const Key('save'),
          onPressed: canSave ? () => save() : null,
          icon: const Icon(Icons.file_download_outlined, size: 18),
          label: const Text(
            'Lưu ảnh',
            style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700),
          ),
        ),
      ],
    ),
  );

  Widget badge(String text, Color bg, Color fg) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 9, vertical: 5),
    decoration: BoxDecoration(
      color: bg,
      borderRadius: BorderRadius.circular(7),
    ),
    child: Text(
      text,
      style: TextStyle(
        fontFamily: 'SectionSans',
        fontSize: 10,
        color: fg,
        fontWeight: FontWeight.w700,
      ),
    ),
  );

  Widget emptyState() => Center(
    child: Container(
      constraints: const BoxConstraints(maxWidth: 550),
      padding: const EdgeInsets.all(38),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 92,
            height: 92,
            decoration: BoxDecoration(
              color: violet.withValues(alpha: .08),
              borderRadius: BorderRadius.circular(28),
            ),
            child: const Icon(Icons.blur_on_rounded, size: 52, color: violet),
          ),
          const SizedBox(height: 25),
          const Text(
            'Khám phá ảnh trong miền tần số',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 25,
              fontWeight: FontWeight.w700,
              letterSpacing: -.8,
            ),
          ),
          const SizedBox(height: 14),
          const Text(
            'Mở một ảnh từ máy để xem phổ Fourier,\nlọc nhiễu và so sánh kết quả ngay tại đây.',
            textAlign: TextAlign.center,
            style: TextStyle(fontSize: 13, color: muted, height: 1.8),
          ),
          const SizedBox(height: 28),
          FilledButton.icon(
            onPressed: busy ? null : () => load(),
            icon: const Icon(Icons.add_rounded, size: 20),
            label: const Text('Chọn ảnh từ máy'),
          ),
          const SizedBox(height: 14),
          TextButton(
            onPressed: busy ? null : () => load(demo: true),
            child: const Text(
              'Hoặc thử với ảnh mẫu',
              style: TextStyle(fontSize: 12),
            ),
          ),
        ],
      ),
    ),
  );

  Widget imagePanel(
    String title,
    String subtitle,
    String? path, {
    bool maskClick = false,
    bool overlay = false,
    bool stale = false,
    String? tag,
  }) => Container(
    decoration: BoxDecoration(
      color: Colors.white,
      border: Border.all(color: lineColor),
      borderRadius: BorderRadius.circular(16),
    ),
    clipBehavior: Clip.antiAlias,
    child: Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 15),
          child: Row(
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    subtitle,
                    style: const TextStyle(fontSize: 10, color: muted),
                  ),
                ],
              ),
              const Spacer(),
              if (stale)
                badge(
                  'Chưa cập nhật',
                  const Color(0xFFFFF4DC),
                  const Color(0xFFA37918),
                )
              else if (tag != null)
                badge(tag, const Color(0xFFF0F1F7), muted),
            ],
          ),
        ),
        Expanded(
          child: Container(
            color: const Color(0xFF151825),
            child: LayoutBuilder(
              builder: (context, constraints) {
                final size = constraints.biggest;
                return MouseRegion(
                  cursor: maskClick
                      ? SystemMouseCursors.precise
                      : SystemMouseCursors.basic,
                  child: GestureDetector(
                    key: maskClick ? const Key('mask_canvas') : null,
                    onTapDown: maskClick
                        ? (details) => clickMask(details.localPosition, size)
                        : null,
                    child: Stack(
                      fit: StackFit.expand,
                      children: [
                        if (path != null)
                          Image.file(
                            File(path),
                            fit: BoxFit.contain,
                            gaplessPlayback: false,
                            errorBuilder: (context, error, stack) =>
                                const Center(
                                  child: Text(
                                    'Không đọc được ảnh preview',
                                    style: TextStyle(color: Colors.white70),
                                  ),
                                ),
                          )
                        else
                          const Center(
                            child: Column(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Icon(
                                  Icons.image_outlined,
                                  color: Color(0xFF51586E),
                                  size: 35,
                                ),
                                SizedBox(height: 10),
                                Text(
                                  'Bấm Xem trước để cập nhật',
                                  style: TextStyle(
                                    color: Color(0xFF9096AD),
                                    fontSize: 12,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        if (overlay && spectrumValid)
                          IgnorePointer(
                            child: CustomPaint(
                              painter: MaskOverlay(
                                shape: result!['padded_shape'] as List,
                                previewShape:
                                    result!['spectrum_preview_shape'] as List?,
                                actions: mode == 'mask' ? actions : [],
                                peaks: mode == 'auto' && !dirty
                                    ? result!['peaks'] as List
                                    : [],
                              ),
                            ),
                          ),
                        if (busy)
                          const ColoredBox(
                            color: Color(0x33151825),
                            child: Center(
                              child: CircularProgressIndicator(
                                color: Colors.white,
                                strokeWidth: 2,
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
        ),
      ],
    ),
  );

  Widget workspace(bool compact) {
    if (source == null) return emptyState();
    return Padding(
      padding: EdgeInsets.all(compact ? 18 : 26),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    spectrumTab ? 'Phổ & vùng lọc' : 'So sánh kết quả',
                    style: const TextStyle(
                      fontSize: 21,
                      fontWeight: FontWeight.w700,
                      letterSpacing: -.6,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    spectrumTab
                        ? 'Quan sát năng lượng tần số và vùng được giữ lại.'
                        : 'Ảnh gốc và kết quả dùng cùng thang sáng 0–255.',
                    style: const TextStyle(fontSize: 11, color: muted),
                  ),
                ],
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.all(4),
                decoration: BoxDecoration(
                  color: const Color(0xFFECEEF5),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Row(
                  children: [
                    tabButton('So sánh', Icons.compare_outlined, false),
                    tabButton('Phổ & Mask', Icons.blur_on_rounded, true),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 22),
          Expanded(
            child: Row(
              children: [
                Expanded(
                  child: spectrumTab
                      ? imagePanel(
                          'Phổ Fourier',
                          mode == 'mask'
                              ? 'Click để thêm vùng chặn đối xứng'
                              : 'Log power · phổ của ảnh đầu vào',
                          spectrumValid
                              ? (result?['spectrum'] as String?)
                              : null,
                          maskClick: mode == 'mask' && !busy,
                          overlay: true,
                          tag: 'FFT SHIFT',
                        )
                      : imagePanel(
                          'Ảnh gốc',
                          'Ảnh đầu vào đã chuyển mức xám',
                          source!['input'] as String,
                          tag: 'INPUT',
                        ),
                ),
                const SizedBox(width: 18),
                Expanded(
                  child: spectrumTab
                      ? imagePanel(
                          'Mask / hàm truyền H',
                          'Đen: chặn · Trắng: giữ',
                          spectrumValid ? (result?['mask'] as String?) : null,
                          stale: dirty,
                          tag: '0 → 1',
                        )
                      : imagePanel(
                          'Ảnh sau lọc',
                          filterNames[mode]!,
                          result?['output'] as String?,
                          stale: dirty,
                          tag: 'OUTPUT',
                        ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 18),
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 15),
            decoration: BoxDecoration(
              color: Colors.white,
              border: Border.all(color: lineColor),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Row(
              children: [
                Icon(
                  spectrumTab
                      ? Icons.touch_app_outlined
                      : Icons.info_outline_rounded,
                  size: 18,
                  color: violet,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    spectrumTab && mode == 'mask'
                        ? '${actions.length} vùng chọn · Vùng đối xứng tự động · Bấm Xem trước để áp dụng'
                        : result == null
                        ? 'Đang chuẩn bị ảnh…'
                        : dirty
                        ? 'Thiết lập đã đổi. Cập nhật preview trước khi lưu.'
                        : '${((result!["seconds"] as num) * 1000).toStringAsFixed(0)} ms xử lý · ${(result!["padded_shape"] as List)[1]} × ${(result!["padded_shape"] as List)[0]} bin${mode == 'auto' ? ' · ${(result!["peaks"] as List).length} cặp đỉnh' : ''}',
                    style: const TextStyle(fontSize: 11, color: muted),
                  ),
                ),
                if (!dirty && result != null)
                  badge(
                    'ĐÃ CẬP NHẬT',
                    const Color(0xFFEAF7F0),
                    const Color(0xFF27815B),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget tabButton(String label, IconData icon, bool value) => InkWell(
    onTap: () => setState(() => spectrumTab = value),
    borderRadius: BorderRadius.circular(7),
    child: Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 9),
      decoration: BoxDecoration(
        color: spectrumTab == value ? Colors.white : Colors.transparent,
        borderRadius: BorderRadius.circular(7),
      ),
      child: Row(
        children: [
          Icon(icon, size: 15, color: spectrumTab == value ? violet : muted),
          const SizedBox(width: 6),
          Text(
            label,
            style: TextStyle(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: spectrumTab == value ? ink : muted,
            ),
          ),
        ],
      ),
    ),
  );

  @override
  Widget build(BuildContext context) => Scaffold(
    body: LayoutBuilder(
      builder: (context, constraints) {
        final compact = constraints.maxWidth < 1200;
        return Column(
          children: [
            topbar(compact),
            Expanded(
              child: Row(
                children: [
                  sidebar(),
                  Expanded(child: workspace(compact)),
                ],
              ),
            ),
            Container(
              height: 34,
              padding: const EdgeInsets.symmetric(horizontal: 22),
              decoration: const BoxDecoration(
                color: Colors.white,
                border: Border(top: BorderSide(color: lineColor)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 6,
                    height: 6,
                    decoration: BoxDecoration(
                      color: busy ? violet : const Color(0xFF35A476),
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: 9),
                  Expanded(
                    child: Text(
                      status,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 10, color: muted),
                    ),
                  ),
                  const Text(
                    'FOURIER STUDIO  /  XỬ LÝ ẢNH',
                    style: TextStyle(
                      fontFamily: 'SectionSans',
                      fontSize: 10,
                      color: muted,
                      letterSpacing: 0.25,
                    ),
                  ),
                ],
              ),
            ),
          ],
        );
      },
    ),
  );
}
