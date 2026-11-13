"""Private JSON-lines subprocess used by Flutter; no web server or open port."""
import json
from pathlib import Path
import sys
import tempfile
import numpy as np
from PIL import Image
from .desktop_model import read_image, process, save_image, export_bundle
from .pipeline import power_spectrum, to_uint8

DEFAULTS = dict(filter='identity',padding='symmetric',backend='radix2',kind='gaussian',
 center=20.,width=10.,order=4,radius=3.,direction='horizontal',tolerance=5.,protect=0.,
 exclude=10.,threshold=6.,max_pairs=12,mask_mode='reject',large=40.,small=3.)


class DesktopSession:
    def __init__(self, directory):
        self.directory=Path(directory)
        self.image=None; self.path=None; self.result=None; self.count=0

    def _preview_image(self, array, target):
        im=Image.fromarray(to_uint8(array))
        im.thumbnail((1400,1400),Image.Resampling.LANCZOS)
        im.save(target)
        return str(target)

    def dispatch(self, request):
        command=request['command']
        if command in ('load','demo'):
            path=Path(request['path']) if command=='load' else Path(__file__).resolve().parents[1]/'results/demo/noisy.png'
            image,mode=read_image(path)
            self.image=image;self.path=path;self.result=None;self.count+=1
            target=self.directory/f'input_{self.count}.png'
            return dict(name=path.name,path=str(path),shape=list(image.shape),source_mode=mode,
                        input=self._preview_image(image,target))
        if self.image is None:
            raise ValueError('Hãy mở ảnh trước khi xử lý.')
        if command=='preview':
            settings=dict(DEFAULTS);settings.update(request.get('settings',{}))
            settings['source_path']=str(self.path)
            mode=settings['filter']
            padding='imagej' if mode=='imagej' else settings['padding']
            cached=None
            if self.result is not None:
                p=self.result.prepared
                if p.padding==padding and p.backend==settings['backend']:cached=p
            actions=request.get('actions',[])
            result=process(self.image,settings,actions,cached)
            self.result=result;self.count+=1
            out=self.directory/f'preview_{self.count}';out.mkdir()
            power=np.log1p(power_spectrum(result.prepared.spectrum))
            power=(power-power.min())/max(float(np.ptp(power)),1e-12)*255
            spectrum_path=self._preview_image(power,out/'spectrum.png')
            with Image.open(spectrum_path) as thumbnail:
                preview_shape=[thumbnail.height,thumbnail.width]
            return dict(output=self._preview_image(result.output,out/'output.png'),
              spectrum=spectrum_path,spectrum_preview_shape=preview_shape,
              mask=self._preview_image(result.transfer*255,out/'mask.png'),
              padded_shape=list(result.transfer.shape),peaks=result.peaks,
              seconds=result.seconds,imaginary=result.imaginary,config=result.config)
        if self.result is None:
            raise ValueError('Hãy bấm Xem trước trước khi lưu kết quả.')
        if command=='save':
            save_image(request['path'],self.result)
            return dict(path=request['path'])
        if command=='export':
            export_bundle(request['path'],self.result)
            return dict(path=request['path'])
        raise ValueError('Lệnh không được hỗ trợ.')


def serve(input_stream=sys.stdin,output_stream=sys.stdout):
    with tempfile.TemporaryDirectory(prefix='fourier-studio-') as directory:
        session=DesktopSession(directory)
        for line in input_stream:
            request={}
            try:
                request=json.loads(line)
                if request.get('command')=='shutdown':break
                data=session.dispatch(request)
                response=dict(id=request.get('id'),ok=True,data=data)
            except Exception as exc:
                response=dict(id=request.get('id'),ok=False,error=str(exc))
            output_stream.write(json.dumps(response,ensure_ascii=False,allow_nan=False)+'\n')
            output_stream.flush()


if __name__=='__main__':serve()
