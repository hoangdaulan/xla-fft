import io
import json
import tempfile
from pathlib import Path
import unittest
import numpy as np
from PIL import Image
from frequency_filter.desktop_bridge import DesktopSession, serve


class DesktopBridgeTests(unittest.TestCase):
    def test_open_preview_save_export_full_resolution(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'ảnh gốc.png'
            a=np.random.default_rng(4).integers(0,256,(73,115),dtype=np.uint8)
            Image.fromarray(a).save(source)
            session=DesktopSession(root)
            loaded=session.dispatch({'command':'load','path':str(source)})
            self.assertEqual(loaded['shape'],[73,115])
            result=session.dispatch({'command':'preview','settings':{'filter':'identity'}})
            np.testing.assert_allclose(session.result.output,a,atol=1e-9)
            saved=root/'kết quả.png';session.dispatch({'command':'save','path':str(saved)})
            with Image.open(saved) as im:np.testing.assert_array_equal(im,a)
            session.dispatch({'command':'export','path':str(root/'export')})
            self.assertTrue((root/'export/config.json').exists())
            self.assertTrue(Path(result['spectrum']).exists())
            with Image.open(result['spectrum']) as spectrum:
                self.assertEqual(result['spectrum_preview_shape'],[spectrum.height,spectrum.width])
            cached=session.result.prepared
            session.dispatch({'command':'preview','settings':{'filter':'mask'},'actions':[[40,30,3]]})
            self.assertIs(session.result.prepared,cached)
            self.assertEqual(session.result.transfer[40,30],0)

    def test_protocol_errors_and_recovery(self):
        lines=[{'id':1,'command':'preview'}, {'id':2,'command':'demo'},
               {'id':3,'command':'preview','settings':{'filter':'bandpass','width':0}},
               {'id':4,'command':'preview','settings':{'filter':'identity','padding':'none'}},
               {'id':5,'command':'shutdown'}]
        output=io.StringIO()
        serve(io.StringIO('\n'.join(json.dumps(x) for x in lines)+'\n'),output)
        messages=[json.loads(x) for x in output.getvalue().splitlines()]
        self.assertEqual([r['id'] for r in messages],[1,2,3,4])
        self.assertEqual([r['ok'] for r in messages],[False,True,False,True])

    def test_preview_thumbnail_does_not_change_saved_resolution(self):
        with tempfile.TemporaryDirectory() as temp:
            session=DesktopSession(temp)
            target=Path(temp)/'thumb.png'
            session._preview_image(np.ones((1600,100)),target)
            with Image.open(target) as im:
                self.assertEqual(im.height,1400)
                self.assertLessEqual(abs(im.width-im.height/16),1)
