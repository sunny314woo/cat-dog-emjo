from io import BytesIO
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import zipfile
from PIL import Image, ImageOps, ImageDraw, ImageFont
from .catalog import EXPRESSIONS
from .slicing import extract_subjects, fit_subject

Image.MAX_IMAGE_PIXELS = 40_000_000

def read_upload(content: bytes, max_pixels=40_000_000, edge=2048) -> bytes:
    with Image.open(BytesIO(content)) as image:
        if image.format not in ('JPEG','PNG','WEBP') or image.width*image.height > max_pixels:
            raise ValueError('请使用符合大小限制的 JPG、PNG 或 WebP')
        if getattr(image, 'n_frames', 1) != 1: raise ValueError('请上传静态照片')
        image = ImageOps.exif_transpose(image).convert('RGB')
        image.thumbnail((edge,edge), Image.Resampling.LANCZOS)
        result=BytesIO(); image.save(result, 'JPEG', quality=92)
        return result.getvalue()  # Re-encoding also strips EXIF and location metadata.

def has_transparency(image):
    if image.mode != 'RGBA': return False
    hist = image.getchannel('A').histogram()
    total=image.width*image.height
    return sum(hist[:32]) > total*.025 and sum(hist[160:]) > total*.03

def remove_background(image, folder):
    with tempfile.TemporaryDirectory(prefix='matting-',dir=folder) as temporary:
        source=Path(temporary)/'input.png';target=Path(temporary)/'output.png'
        image.save(source)
        # Do not pass provider credentials to the image-only subprocess.
        env={k:os.environ[k] for k in ('PATH','HOME','LANG','U2NET_HOME') if k in os.environ}
        try:
            subprocess.run([sys.executable,str(Path(__file__).with_name('matting_worker.py')),str(source),str(target)],
                           env=env,timeout=120,check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        except (subprocess.SubprocessError,OSError) as exc:
            raise ValueError('本地抠图未完成，请检查抠图依赖与模型文件') from exc
        with Image.open(target) as output:
            output.load();return output.convert('RGBA')

def prepare_styles(source,folder,demo=False):
    folder.mkdir(parents=True,exist_ok=True)
    with Image.open(BytesIO(source)) as image:
        image.load()
        if not .97<=image.width/image.height<=1.03:raise ValueError('风格预览母图必须为正方形')
        # Preview cells are references, not transparent sticker deliverables.
        for i in range(4):
            x,y=i%2,i//2
            crop=image.crop((round(x*image.width/2),round(y*image.height/2),
                             round((x+1)*image.width/2),round((y+1)*image.height/2)))
            background=Image.new('RGB',crop.size,'white')
            if crop.mode=='RGBA':background.paste(crop,mask=crop.getchannel('A'))
            else:background.paste(crop.convert('RGB'))
            background.save(folder/f'style-reference-{i+1}.jpg',quality=95)
            background.thumbnail((512,512),Image.Resampling.LANCZOS)
            if demo:
                ImageDraw.Draw(background).text((12,12),'DEMO',fill='black')
            background.save(folder/f'style-choice-{i+1}.jpg',quality=88)

def font(size):
    candidates=[os.getenv('EMJO_FONT_PATH',''), '/System/Library/Fonts/PingFang.ttc', '/System/Library/Fonts/STHeiti Medium.ttc',
                '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc']
    for name in candidates:
        if name and Path(name).exists(): return ImageFont.truetype(name,size)
    raise ValueError('请配置支持中文的 EMJO_FONT_PATH，不能输出缺字贴纸')

def validate_grid_boundaries(image):
    """Reject occupied cut lines; this is a guard, not a semantic matting guarantee."""
    alpha=image.getchannel('A')
    for axis in ('x','y'):
        length=image.height if axis=='x' else image.width
        dimension=image.width if axis=='x' else image.height
        for fraction in (1,2):
            cut=round(dimension*fraction/3)
            occupied=sum(any(alpha.getpixel((p,q) if axis=='x' else (q,p))>128
                             for p in range(max(0,cut-1),min(dimension,cut+2)))
                         for q in range(length))
            if occupied>max(3,length*.01):
                raise ValueError('主体跨越九宫格切线，不能直接等分交付；需要重新生成合格留白的母图')

def prepare_pack(source: bytes, folder: Path, captions=True, background_mode='alpha_only', strict_boundaries=True):
    folder.mkdir(parents=True, exist_ok=True)
    with Image.open(BytesIO(source)) as incoming:
        incoming.load()
        image=incoming.convert('RGBA')
    if image.width/image.height < .97 or image.width/image.height > 1.03:
        raise ValueError('母图不是有效的方形九宫格')
    # Reject non-transparent output, or use the explicitly configured matting adapter.
    matted=False
    if not has_transparency(image):
        if background_mode != 'rembg': raise ValueError('输出还没有合格透明背景，需要配置并验证抠图适配器')
        image=remove_background(image,folder)
        matted=True
        if not has_transparency(image): raise ValueError('背景处理未通过透明度检查')
    # Matting can connect separate subjects with a low-confidence alpha fringe.
    subjects=extract_subjects(image,core_threshold=160 if matted else 128)
    image.save(folder/'mother.png')
    grid=Image.new('RGBA',(1536,1536),(0,0,0,0))
    for i, expression in enumerate(EXPRESSIONS):
        col,row=i%3,i//3
        sticker=fit_subject(subjects[i],512,caption_space=captions)
        if captions:
            draw=ImageDraw.Draw(sticker)
            draw.text((256,453),expression['label'],font=font(38),anchor='mm',fill='#594735',stroke_width=5,stroke_fill='white')
        sticker.save(folder/f'sticker-{i+1}.png')
        sticker.resize((256,256),Image.Resampling.LANCZOS).save(folder/f'sticker-{i+1}-256.png')
        sticker.save(folder/f'sticker-{i+1}.webp',format='WEBP',quality=80,method=0)
        grid.alpha_composite(sticker,(col*512,row*512))
        # Protection is baked into the pixels on the server; no HD is sent for locked cells.
        preview=Image.new('RGB',(256,256),'#fff2d9')
        pd=ImageDraw.Draw(preview)
        for x in range(10,256,24):
            for y in range(10,256,24):pd.ellipse((x,y,x+2,y+2),fill='#e9d9bc')
        tiny=sticker.resize((256,256),Image.Resampling.LANCZOS)
        preview.paste(tiny,(0,0),tiny)
        overlay=Image.new('RGBA',(256,256));od=ImageDraw.Draw(overlay)
        for y in (91,171):
            od.text((128,y),'表情预览 · EMJO',font=font(19),anchor='mm',fill=(109,83,63,135),stroke_width=1,stroke_fill=(255,255,255,185))
        preview=Image.alpha_composite(preview.convert('RGBA'),overlay).convert('RGB')
        preview.save(folder/f'preview-{i+1}.jpg',quality=80)
    grid.save(folder/'grid.png')
    with zipfile.ZipFile(folder/'stickers.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for name in [f'sticker-{i+1}.png' for i in range(9)]+['grid.png']:
            archive.write(folder/name,name)
        archive.writestr('README.txt','9 transparent PNG stickers + one grid. Save a local copy before your download expires.\n')
    return {'width':512,'height':512,'cells':9}
