import 'dart:math' as math;
import 'package:flutter/material.dart';

Rect fittedImageRect(Size size, List shape, {List? previewShape}) {
  final displayed = previewShape ?? shape;
  final scale = math.min(
    size.width / (displayed[1] as num),
    size.height / (displayed[0] as num),
  );
  final width = (displayed[1] as num) * scale,
      height = (displayed[0] as num) * scale;
  return Rect.fromLTWH(
    (size.width - width) / 2,
    (size.height - height) / 2,
    width,
    height,
  );
}

class MaskOverlay extends CustomPainter {
  final List shape, peaks;
  final List? previewShape;
  final List<List<num>> actions;
  MaskOverlay({
    required this.shape,
    required this.actions,
    required this.peaks,
    this.previewShape,
  });
  @override
  void paint(Canvas canvas, Size size) {
    final rect = fittedImageRect(size, shape, previewShape: previewShape);
    final rows = (shape[0] as num).toInt(), cols = (shape[1] as num).toInt();
    Offset point(num row, num col) => Offset(
      rect.left + (col + .5) / cols * rect.width,
      rect.top + (row + .5) / rows * rect.height,
    );
    final outline = Paint()
      ..color = const Color(0xFF42E0CE)
      ..style = PaintingStyle.stroke
      ..strokeWidth = 1.5;
    for (final action in actions) {
      for (final pair in [
        [action[0], action[1]],
        [
          (2 * (rows ~/ 2) - action[0]) % rows,
          (2 * (cols ~/ 2) - action[1]) % cols,
        ],
      ]) {
        final center = point(pair[0], pair[1]);
        canvas.drawOval(
          Rect.fromCenter(
            center: center,
            width: 2 * action[2] / cols * rect.width,
            height: 2 * action[2] / rows * rect.height,
          ),
          outline,
        );
        canvas.drawCircle(center, 2, Paint()..color = const Color(0xFF42E0CE));
      }
    }
    final highlight = Paint()
      ..color = const Color(0xFFFFC86A)
      ..strokeWidth = 1.8;
    for (final peak in peaks) {
      for (final sign in [-1, 1]) {
        final center = point(
          (rows ~/ 2 + sign * (peak[0] as num)) % rows,
          (cols ~/ 2 + sign * (peak[1] as num)) % cols,
        );
        canvas.drawLine(
          center - const Offset(5, 0),
          center + const Offset(5, 0),
          highlight,
        );
        canvas.drawLine(
          center - const Offset(0, 5),
          center + const Offset(0, 5),
          highlight,
        );
      }
    }
  }

  @override
  bool shouldRepaint(covariant MaskOverlay oldDelegate) => true;
}
