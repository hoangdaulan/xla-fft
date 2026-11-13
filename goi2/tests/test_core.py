import unittest
import numpy as np
from frequency_filter.fft import fft1d, fft2d, ifft2d, fftshift, ifftshift
from frequency_filter.filters import bandpass, notch_reject, suppress_stripes, symmetric_mask, partner, find_noise_peaks, imagej_bandpass
from frequency_filter.pipeline import prepare, reconstruct, filter_freq, to_uint8


class FourierTests(unittest.TestCase):
    def test_fft_reference_and_roundtrip(self):
        rng = np.random.default_rng(14)
        for shape in [(1,1),(1,8),(8,1),(8,16),(64,64)]:
            x = rng.normal(size=shape)+1j*rng.normal(size=shape)
            f = fft2d(x)
            np.testing.assert_allclose(f,np.fft.fft2(x),atol=1e-10,rtol=1e-10)
            np.testing.assert_allclose(ifft2d(f),x,atol=1e-10,rtol=1e-10)
        np.testing.assert_allclose(fft1d(np.arange(16)),np.fft.fft(np.arange(16)),atol=1e-10)

    def test_invalid_radix(self):
        for x in [np.zeros((3,8)), np.zeros((0,8)), np.zeros(8)]:
            with self.assertRaises(ValueError): fft2d(x)

    def test_parseval(self):
        x = np.random.default_rng(2).normal(size=(32,64))
        self.assertAlmostEqual(float(np.sum(abs(fft2d(x))**2)/x.size/np.sum(x*x)),1,places=12)

    def test_known_sine(self):
        x,y=np.mgrid[:64,:64]
        f=fft2d(np.sin(2*np.pi*(5*x/64+3*y/64)))
        self.assertAlmostEqual(abs(f[5,3]),2048,places=9)
        self.assertAlmostEqual(abs(f[-5,-3]),2048,places=9)
        f[5,3]=f[-5,-3]=0
        self.assertLess(np.max(abs(f)),1e-9)

    def test_shift_odd_even(self):
        for shape in [(4,8),(5,7)]:
            a=np.arange(np.prod(shape)).reshape(shape)
            np.testing.assert_array_equal(fftshift(a),np.fft.fftshift(a))
            np.testing.assert_array_equal(ifftshift(fftshift(a)),a)

    def test_pipeline_identity_all_padding(self):
        a=np.random.default_rng(3).uniform(0,255,size=(13,19))
        for padding in ['zero','symmetric','edge','imagej']:
            p=prepare(a,padding)
            b, residual=reconstruct(p)
            np.testing.assert_allclose(b,a,atol=1e-10)
            self.assertLess(residual,1e-10)
        np.testing.assert_allclose(filter_freq(a,lambda p,q:np.ones((p,q))),a,atol=1e-10)
        p=prepare(a,'none','numpy')
        np.testing.assert_allclose(reconstruct(p)[0],a,atol=1e-10)
        self.assertEqual(prepare(np.ones((13,18)),'imagej').offset,(10,7))

    def test_masks_and_nyquist_symmetry(self):
        shape=(32,64)
        for kind in ['ideal','gaussian','butterworth']:
            for h in [bandpass(shape,10,4,kind),notch_reject(shape,[(15,31)],2,kind=kind)]:
                np.testing.assert_allclose(h,partner(h),atol=1e-12)
                self.assertTrue(np.isfinite(h).all())
                self.assertTrue(((h>=0)&(h<=1)).all())
        h=np.ones(shape);h[3,5]=0
        p=prepare(np.ones(shape),'none')
        with self.assertRaises(ValueError): reconstruct(p,h)
        h=symmetric_mask(h)
        np.testing.assert_array_equal(h,partner(h))
        reconstruct(p,h)

    def test_bandpass_values(self):
        for kind in ['ideal','gaussian','butterworth']:
            h=bandpass((64,64),10,4,kind)
            self.assertEqual(h[32,32],0)
            self.assertEqual(h[32,42],1)

    def test_stripe_orientation(self):
        n=64;x,y=np.mgrid[:n,:n]
        for direction,coordinate in [('horizontal',x),('vertical',y)]:
            a=128+20*np.sin(2*np.pi*8*coordinate/n)
            p=prepare(a,'none')
            b,_=reconstruct(p,suppress_stripes((n,n),direction))
            np.testing.assert_allclose(b,128,atol=1e-10)
            other='vertical' if direction=='horizontal' else 'horizontal'
            c,_=reconstruct(p,suppress_stripes((n,n),other))
            self.assertGreater(np.std(c),10)

    def test_peak_detection_and_auto_improvement(self):
        n=128;x,y=np.mgrid[:n,:n]
        clean=128+25*np.cos(2*np.pi*x/n)+20*np.cos(4*np.pi*y/n)
        noisy=clean+20*np.sin(2*np.pi*(17*x/n+11*y/n))
        p=prepare(noisy,'none')
        peaks=find_noise_peaks(p.spectrum)
        self.assertTrue((17,11) in peaks or (-17,-11) in peaks)
        self.assertEqual(len(peaks),1)
        result,_=reconstruct(p,notch_reject((n,n),peaks,2))
        self.assertLess(np.mean((result-clean)**2),0.01*np.mean((noisy-clean)**2))

    def test_imagej_filter_and_rounding(self):
        h=imagej_bandpass((64,64))
        self.assertEqual(h[32,32],1)
        d=5
        self.assertAlmostEqual(h[32,32+d],(1-np.exp(-d*d*(80/64)**2))*np.exp(-d*d*(6/64)**2))
        np.testing.assert_array_equal(to_uint8(np.array([-1,0.5,1.5,255.9])),[0,1,2,255])

    def test_invalid_filters(self):
        for fn in [lambda: bandpass((8,8),width=0), lambda: notch_reject((8,8),[],radius=-1),
                   lambda: suppress_stripes((8,8),tolerance=100),
                   lambda: prepare(np.array([[np.nan]])),lambda: symmetric_mask(np.ones((8,8))*2)]:
            with self.assertRaises(ValueError): fn()


if __name__=='__main__': unittest.main()
