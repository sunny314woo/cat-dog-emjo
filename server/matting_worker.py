"""Isolated CPU matting. Exits after one image to release ONNX memory."""
import os
import sys
from pathlib import Path


def main():
    for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMBA_NUM_THREADS'):
        os.environ[key]='1'
    os.nice(10)
    from PIL import Image
    from rembg import new_session, remove
    from matting import repair_foreground_alpha
    session=new_session('u2netp',providers=['CPUExecutionProvider'])
    with Image.open(sys.argv[1]) as source:
        source.load()
        if source.width*source.height>5_000_000:raise ValueError('Image too large')
        result=remove(source.convert('RGB'),session=session,alpha_matting=False)
        result=repair_foreground_alpha(result,source)
        result.save(Path(sys.argv[2]),format='PNG')


if __name__=='__main__':main()
