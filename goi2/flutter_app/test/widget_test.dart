import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:fourier_studio/app.dart';
import 'package:fourier_studio/widgets/spectrum_overlay.dart';

void main() {
  testWidgets(
    'Desktop opens with clear import action and prevents saving empty output',
    (tester) async {
      tester.view.physicalSize = const Size(1360, 800);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(const FourierStudio());
      expect(find.text('Fourier Studio'), findsOneWidget);
      expect(find.text('Chọn ảnh từ máy'), findsOneWidget);
      final save = tester.widget<FilledButton>(find.byKey(const Key('save')));
      expect(save.onPressed, isNull);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );

  testWidgets(
    'Filter controls render without overflow at minimum desktop width',
    (tester) async {
      tester.view.physicalSize = const Size(1040, 680);
      tester.view.devicePixelRatio = 1;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);
      await tester.pumpWidget(const FourierStudio());
      await tester.tap(find.text('Không lọc · FFT / IFFT'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('Mask thủ công').last);
      await tester.pumpAndSettle();
      expect(find.text('Thao tác'), findsOneWidget);
      expect(find.text('Hoàn tác'), findsOneWidget);
      expect(tester.takeException(), isNull);
      await tester.pumpWidget(const SizedBox());
    },
  );

  test('Mask coordinates account for letterboxing in rectangular images', () {
    expect(
      fittedImageRect(const Size(400, 300), [100, 200]),
      const Rect.fromLTWH(0, 50, 400, 200),
    );
    expect(
      fittedImageRect(const Size(300, 400), [200, 100]),
      const Rect.fromLTWH(50, 0, 200, 400),
    );
  });

  test('Mask uses actual rounded thumbnail aspect ratio for large images', () {
    final rect = fittedImageRect(
      const Size(400, 300),
      [1600, 100],
      previewShape: [1400, 87],
    );
    expect(rect.height, 300);
    expect(rect.width, closeTo(300 * 87 / 1400, 1e-10));
    expect(rect.center, const Offset(200, 150));
    // At the visual center the source bin must remain (row 800, column 50).
    expect(((rect.center.dx - rect.left) / rect.width * 100).round(), 50);
    expect(((rect.center.dy - rect.top) / rect.height * 1600).round(), 800);
  });
}
