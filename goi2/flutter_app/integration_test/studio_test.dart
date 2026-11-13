import 'dart:io';
import 'dart:ui' as ui;
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:integration_test/integration_test.dart';
import 'package:file_selector_platform_interface/file_selector_platform_interface.dart';
import 'package:fourier_studio/app.dart';
import 'package:fourier_studio/widgets/spectrum_overlay.dart';
import 'package:fourier_studio/bridge.dart';
import 'package:path/path.dart' as p;

class TestFiles extends FileSelectorPlatform {
  String? input, save, directory;
  @override
  Future<XFile?> openFile({
    List<XTypeGroup>? acceptedTypeGroups,
    String? initialDirectory,
    String? confirmButtonText,
  }) async => input == null ? null : XFile(input!);
  @override
  Future<FileSaveLocation?> getSaveLocation({
    List<XTypeGroup>? acceptedTypeGroups,
    SaveDialogOptions options = const SaveDialogOptions(),
  }) async => save == null ? null : FileSaveLocation(save!);
  @override
  Future<String?> getDirectoryPathWithOptions(
    FileDialogOptions options,
  ) async => directory;
}

void main() {
  IntegrationTestWidgetsFlutterBinding.ensureInitialized();
  testWidgets('Real Python pipeline: import, mask, preview, save and export', (
    tester,
  ) async {
    final root = PythonBridge.projectRoot();
    final temp = Directory.systemTemp.createTempSync('fourier-test-');
    final mock = TestFiles();
    final previous = FileSelectorPlatform.instance;
    FileSelectorPlatform.instance = mock;
    addTearDown(() {
      FileSelectorPlatform.instance = previous;
      temp.deleteSync(recursive: true);
    });
    final source = File(p.join(temp.path, 'ảnh thử.png'));
    File(p.join(root, 'results', 'demo', 'noisy.png')).copySync(source.path);
    final out = p.join(temp.path, 'kết quả.png');
    mock.input = source.path;
    mock.save = out;
    mock.directory = temp.path;
    await tester.pumpWidget(const FourierStudio());
    await tester.pumpAndSettle();
    Future<void> waitReady() async {
      for (var i = 0; i < 160; i++) {
        await tester.pump(const Duration(milliseconds: 100));
        final button = tester.widget<FilledButton>(
          find.byKey(const Key('save')),
        );
        if (button.onPressed != null) return;
      }
      fail('Processing timeout');
    }

    Future<void> screenshot(String name) async {
      await tester.pumpAndSettle();
      final boundary = tester.renderObject<RenderRepaintBoundary>(
        find.byKey(const Key('studio_capture')),
      );
      await tester.runAsync(() async {
        final image = await boundary.toImage(pixelRatio: 1.5);
        final data = await image.toByteData(format: ui.ImageByteFormat.png);
        final file = File(p.join(root, 'docs', 'gui', name));
        file.writeAsBytesSync(data!.buffer.asUint8List());
        image.dispose();
      });
    }

    await screenshot('flutter_empty.png');
    await tester.tap(find.byKey(const Key('open')));
    await waitReady();
    expect(find.text('ảnh thử.png'), findsOneWidget);
    await tester.tap(find.text('Gương').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Không padding').last);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Không lọc · FFT / IFFT').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Mask thủ công').last);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('preview')));
    await waitReady();
    final rect = tester.getRect(find.byKey(const Key('mask_canvas')));
    final local = fittedImageRect(rect.size, [128, 128]);
    await tester.tapAt(
      rect.topLeft +
          Offset(
            local.left + 53.5 / 128 * local.width,
            local.top + 47.5 / 128 * local.height,
          ),
    );
    await tester.pump();
    expect(
      tester.widget<FilledButton>(find.byKey(const Key('save'))).onPressed,
      isNull,
    );
    await tester.tap(find.byKey(const Key('preview')));
    await waitReady();
    expect(find.textContaining('1 vùng chọn'), findsOneWidget);
    await screenshot('flutter_mask.png');
    await tester.tap(find.byKey(const Key('save')));
    await waitReady();
    expect(File(out).existsSync(), isTrue);
    await tester.tap(find.byKey(const Key('export')));
    await waitReady();
    expect(File(p.join(temp.path, 'mask.npy')).existsSync(), isTrue);
    expect(
      File(p.join(temp.path, 'config.json')).readAsStringSync(),
      contains('mask_actions'),
    );
    await tester.tap(find.text('So sánh').first);
    await tester.pumpAndSettle();
    await screenshot('flutter_compare.png');
    final savedBytes = File(out).readAsBytesSync();
    final configBefore = File(
      p.join(temp.path, 'config.json'),
    ).readAsStringSync();
    await tester.tap(find.byKey(const Key('export')));
    await tester.pumpAndSettle();
    expect(find.text('Ghi đè kết quả đã có?'), findsOneWidget);
    await tester.tap(find.text('Hủy'));
    await tester.pumpAndSettle();
    expect(
      File(p.join(temp.path, 'config.json')).readAsStringSync(),
      configBefore,
    );
    mock.save = p.withoutExtension(out);
    await tester.tap(find.byKey(const Key('save')));
    await tester.pumpAndSettle();
    expect(find.text('Ghi đè ảnh đã có?'), findsOneWidget);
    await tester.tap(find.text('Hủy'));
    await tester.pumpAndSettle();
    expect(File(out).readAsBytesSync(), savedBytes);
    mock.input = null;
    await tester.tap(find.byKey(const Key('open')));
    await tester.pumpAndSettle();
    expect(find.text('ảnh thử.png'), findsOneWidget);
    expect(
      tester.widget<FilledButton>(find.byKey(const Key('save'))).onPressed,
      isNotNull,
    );
    // Undo invalidates the previous result, so it cannot accidentally be saved.
    await tester.tap(find.text('Hoàn tác'));
    await tester.pump();
    expect(
      tester.widget<FilledButton>(find.byKey(const Key('save'))).onPressed,
      isNull,
    );
    expect(tester.takeException(), isNull);
    await tester.pumpWidget(const SizedBox());
  });
}
