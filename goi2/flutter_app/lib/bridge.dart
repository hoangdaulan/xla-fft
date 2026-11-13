import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:path/path.dart' as p;

class PythonBridge {
  Process? _process;
  Future<void>? _starting;
  int _sequence = 0;
  bool _disposed = false;
  Object? _failure;
  String _stderr = '';
  final _pending = <int, Completer<Map<String, dynamic>>>{};

  static String projectRoot() {
    final configured = Platform.environment['XLA_ROOT'];
    if (configured != null &&
        Directory(p.join(configured, 'frequency_filter')).existsSync()) {
      return configured;
    }
    var directory = Directory.current;
    for (var i = 0; i < 9; i++) {
      if (Directory(p.join(directory.path, 'frequency_filter')).existsSync()) {
        return directory.path;
      }
      directory = directory.parent;
    }
    throw StateError(
      'Không tìm thấy lõi Python. Hãy mở ứng dụng bằng mo_flutter.sh.',
    );
  }

  Future<void> _start() async {
    final root = projectRoot();
    final python =
        Platform.environment['XLA_PYTHON'] ??
        p.join(root, '.venv', 'bin', 'python');
    _process = await Process.start(python, [
      '-u',
      '-m',
      'frequency_filter.desktop_bridge',
    ], workingDirectory: root);
    if (_disposed) {
      _process!.kill();
      return;
    }
    _process!.stdout
        .transform(utf8.decoder)
        .transform(const LineSplitter())
        .listen((line) {
          try {
            final response = jsonDecode(line) as Map<String, dynamic>;
            final completer = _pending.remove(response['id']);
            if (completer == null) return;
            if (response['ok'] == true) {
              completer.complete(
                Map<String, dynamic>.from(response['data'] as Map),
              );
            } else {
              completer.completeError(StateError(response['error'] as String));
            }
          } catch (error) {
            _failAll(StateError('Phản hồi xử lý không hợp lệ: $error'));
          }
        });
    _process!.stderr.transform(utf8.decoder).listen((text) {
      _stderr += text;
      if (_stderr.length > 4000) {
        _stderr = _stderr.substring(_stderr.length - 4000);
      }
    });
    unawaited(
      _process!.exitCode.then((code) {
        _failAll(StateError('Lõi xử lý đã dừng ($code). $_stderr'));
      }),
    );
  }

  void _failAll(Object error) {
    _failure = error;
    for (final value in _pending.values) {
      if (!value.isCompleted) value.completeError(error);
    }
    _pending.clear();
  }

  Future<Map<String, dynamic>> request(
    String command, [
    Map<String, dynamic> arguments = const {},
  ]) async {
    if (_disposed) throw StateError('Ứng dụng đã đóng.');
    _starting ??= _start();
    await _starting;
    if (_disposed) throw StateError('Ứng dụng đã đóng.');
    if (_failure != null) throw _failure!;
    final id = ++_sequence;
    final completer = Completer<Map<String, dynamic>>();
    _pending[id] = completer;
    _process!.stdin.writeln(
      jsonEncode({'id': id, 'command': command, ...arguments}),
    );
    return completer.future;
  }

  void dispose() {
    _disposed = true;
    _failAll(StateError('Ứng dụng đã đóng.'));
    final process = _process;
    if (process != null) {
      unawaited(() async {
        try {
          await process.stdin.close();
          await process.exitCode.timeout(const Duration(seconds: 2));
        } catch (_) {
          process.kill();
        }
      }());
    }
  }
}
