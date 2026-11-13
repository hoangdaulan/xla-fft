import 'package:flutter/material.dart';

const ink = Color(0xFF202239);
const muted = Color(0xFF777D91);
const violet = Color(0xFF7054E8);
const canvasColor = Color(0xFFF5F6FA);
const lineColor = Color(0xFFE8EAF2);
const filterNames = <String, String>{
  'identity': 'Không lọc · FFT / IFFT',
  'bandpass': 'Bandpass',
  'stripes': 'Suppress Stripes',
  'mask': 'Mask thủ công',
  'auto': 'Notch tự dò',
  'imagej': 'Bandpass ImageJ',
};
const paddingNames = <String, String>{
  'symmetric': 'Gương',
  'zero': 'Chèn số 0',
  'edge': 'Lặp biên',
  'none': 'Không padding',
  'imagej': 'Gương theo ImageJ',
};
const defaults = <String, dynamic>{
  'filter': 'identity',
  'padding': 'symmetric',
  'backend': 'radix2',
  'kind': 'gaussian',
  'center': 20.0,
  'width': 10.0,
  'order': 4,
  'radius': 3.0,
  'direction': 'horizontal',
  'tolerance': 5.0,
  'protect': 0.0,
  'exclude': 10.0,
  'threshold': 6.0,
  'max_pairs': 12,
  'mask_mode': 'reject',
  'large': 40.0,
  'small': 3.0,
};
