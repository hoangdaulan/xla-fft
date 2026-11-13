import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from PIL import Image
from frequency_filter.desktop_model import read_image, process, manual_transfer, save_image, export_bundle
from frequency_filter.filters import partner, bandpass
from frequency_filter.pipeline import filter_freq,to_uint8


def settings(mode='identity', **changes):
    s=dict(filter=mode,padding='none',backend='radix2',kind='butterworth',center=10.,width=5.,
      order=4,radius=3.,direction='horizontal',tolerance=5.,protect=0.,exclude=10.,threshold=6.,
      max_pairs=12,mask_mode='reject',large=40.,small=3.)
    s.update(changes);return s


class DesktopModelTests(unittest.TestCase):
    def setUp(self):self.image=np.random.default_rng(14).uniform(0,255,(32,64))

    def test_preview_matches_core(self):
        result=process(self.image,settings('bandpass'))
        reference=filter_freq(self.image,lambda p,q:bandpass((p,q),10,5,'butterworth',4),pad='none')
        np.testing.assert_allclose(result.output,reference,atol=1e-10)
        identity=process(self.image,settings())
        np.testing.assert_allclose(identity.output,self.image,atol=1e-10)
        cached=process(self.image,settings('bandpass'),cached=identity.prepared)
        self.assertIs(cached.prepared,identity.prepared)
        np.testing.assert_allclose(cached.output,result.output)

    def test_click_pair_undo_and_pass(self):
        actions=[(4,7,3),(25,40,2)]
        h=manual_transfer(self.image.shape,actions)
        np.testing.assert_array_equal(h,partner(h))
        self.assertEqual(h[4,7],0);self.assertEqual(h[28,57],0)
        undone=manual_transfer(self.image.shape,actions[:-1])
        self.assertEqual(undone[25,40],1)
        np.testing.assert_array_equal(manual_transfer(self.image.shape,[]),1)
        np.testing.assert_array_equal(manual_transfer(self.image.shape,actions,'pass'),1-h)

    def test_stripes_auto_and_imagej(self):
        x,y=np.mgrid[:64,:64];a=128+20*np.sin(2*np.pi*12*x/64)
        result=process(a,settings('stripes'))
        np.testing.assert_allclose(result.output,128,atol=1e-10)
        auto=process(a,settings('auto'))
        self.assertTrue((12,0) in auto.peaks or (-12,0) in auto.peaks)
        self.assertLess(np.std(auto.output),.1)
        result=process(self.image,settings('imagej'))
        self.assertEqual(result.prepared.padding,'imagej')
        self.assertEqual(result.output.shape,self.image.shape)

    def test_unicode_io_and_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp)/'ảnh thử';directory.mkdir()
            color=np.zeros((32,64,3),dtype=np.uint8);color[:,:,0]=200
            path=directory/'ảnh màu.png';Image.fromarray(color).save(path)
            a,mode=read_image(path);self.assertEqual(mode,'RGB');self.assertEqual(a.shape,(32,64))
            result=process(a,settings())
            for ext in ['png','tif','bmp']:
                target=directory/f'kết quả.{ext}';save_image(target,result)
                with Image.open(target) as im:
                    np.testing.assert_array_equal(np.asarray(im),to_uint8(a))
            with self.assertRaises(ValueError):save_image(directory/'bad.jpg',result)
            export_bundle(directory/'bộ kết quả',result)
            out=directory/'bộ kết quả'
            self.assertEqual(len(list(out.iterdir())),9)
            np.testing.assert_allclose(np.load(out/'power_raw.npy'),abs(result.prepared.spectrum)**2)
            self.assertEqual(json.loads((out/'config.json').read_text())['original_shape'],[32,64])

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):manual_transfer((32,64),[(3,4,-1)])
        with self.assertRaises(ValueError):process(self.image,settings('bandpass',width=0))
        with self.assertRaises(ValueError):process(np.ones((13,17)),settings())
