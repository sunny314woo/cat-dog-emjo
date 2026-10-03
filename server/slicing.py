"""Separate alpha-connected subjects before fitting them into delivery cells.

Grid position identifies expression order, never defines the crop rectangle.
Touching/ambiguous main subjects fail closed instead of being cut apart.
"""
from PIL import Image, ImageFilter, ImageChops

def extract_subjects(image, columns=3, rows=3):
    image=image.convert('RGBA');w,h=image.size
    alpha=image.getchannel('A')
    # Half-scale core masks avoid treating individual antialiased hairs as subjects.
    mw=max(1,w//2);mh=max(1,h//2)
    values=alpha.resize((mw,mh),Image.Resampling.BOX).tobytes()
    unseen=bytearray(v>128 for v in values);components=[]
    for start in range(mw*mh):
        if not unseen[start]:continue
        unseen[start]=0;stack=[start];points=[];sx=sy=0
        while stack:
            k=stack.pop();points.append(k);x=k%mw;y=k//mw;sx+=x;sy+=y
            neighbors=[]
            if x:neighbors.append(k-1)
            if x<mw-1:neighbors.append(k+1)
            if y:neighbors.append(k-mw)
            if y<mh-1:neighbors.append(k+mw)
            for n in neighbors:
                if unseen[n]:unseen[n]=0;stack.append(n)
        components.append({'points':points,'center':(sx/len(points),sy/len(points))})
    minimum=mw*mh/(columns*rows)*.08
    main=[c for c in components if len(c['points'])>minimum]
    if len(main)!=columns*rows:
        raise ValueError('主体数量或轮廓不明确，拒绝切断相连的主体；需重新生成留白母图')
    slots={}
    for c in main:
        x,y=c['center'];slot=min(rows-1,int(y/mh*rows))*columns+min(columns-1,int(x/mw*columns))
        if slot in slots:raise ValueError('主体排布不明确，不能自动归属格子')
        slots[slot]=c
    masks=[bytearray(mw*mh) for _ in range(columns*rows)]
    for component in components:
        if len(component['points'])<3:continue
        x,y=component['center']
        slot=min(slots,key=lambda k:(x-slots[k]['center'][0])**2+(y-slots[k]['center'][1])**2)
        for k in component['points']:masks[slot][k]=255
    core=[Image.frombytes('L',(mw,mh),bytes(m)).resize((w,h),Image.Resampling.NEAREST) for m in masks]
    result=[]
    for slot,mask in enumerate(core):
        # Recover the soft alpha fringe without bringing a neighboring subject back.
        mask=mask.filter(ImageFilter.MaxFilter(7))
        for j,other in enumerate(core):
            if j!=slot:mask=ImageChops.subtract(mask,other)
        subject=image.copy();subject.putalpha(ImageChops.multiply(alpha,mask))
        bounds=subject.getbbox()
        if not bounds:raise ValueError('空白主体')
        result.append(subject.crop(bounds))
    return result

def fit_subject(subject,size=512,caption_space=False):
    canvas=Image.new('RGBA',(size,size))
    available_height=round(size*.80) if caption_space else round(size*.86)
    subject=subject.copy();subject.thumbnail((round(size*.86),available_height),Image.Resampling.LANCZOS)
    top=(round(size*.86)-subject.height)//2 if caption_space else (size-subject.height)//2
    canvas.alpha_composite(subject,((size-subject.width)//2,top))
    return canvas
