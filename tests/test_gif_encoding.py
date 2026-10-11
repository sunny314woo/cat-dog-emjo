import pytest
from PIL import Image, ImageDraw
from server.imaging import save_wechat_gif


@pytest.mark.parametrize('accent', [None, (210, 60, 70, 255)])
def test_gif_reserves_valid_transparent_palette_entry(tmp_path, accent):
    image=Image.new('RGBA',(240,240))
    draw=ImageDraw.Draw(image)
    draw.rectangle((60,60,180,180),fill=(255,255,255,255))
    if accent:
        draw.rectangle((70,70,90,90),fill=accent)
    path=tmp_path/'sticker.gif'
    save_wechat_gif(image,path)

    content=path.read_bytes()
    assert content[:6]==b'GIF89a'
    packed=content[10]
    assert packed&0x80
    color_count=2**((packed&0x07)+1)
    assert color_count==256
    extension=13+3*color_count
    assert content[extension:extension+3]==b'\x21\xf9\x04'
    assert content[extension+3]&0x01
    transparent_index=content[extension+6]
    assert transparent_index==content[11]==255
    assert transparent_index<color_count

    with Image.open(path) as output:
        assert output.n_frames==1
        assert len(output.getpalette())==768
        assert output.info['transparency']==output.info['background']==255
        result=output.convert('RGBA')
    assert result.getpixel((0,0))[3]==0
    assert result.getpixel((120,120))==(255,255,255,255)
    if accent:
        assert result.getpixel((80,80))==accent


def test_gif_alpha_threshold_preserves_opaque_white(tmp_path):
    image=Image.new('RGBA',(240,240))
    image.putpixel((20,20),(255,255,255,127))
    image.putpixel((21,20),(255,255,255,128))
    image.putpixel((22,20),(255,255,255,255))
    path=tmp_path/'alpha.gif'
    save_wechat_gif(image,path)

    with Image.open(path) as output:
        result=output.convert('RGBA')
    assert result.getpixel((20,20))[3]==0
    assert result.getpixel((21,20))==(255,255,255,255)
    assert result.getpixel((22,20))==(255,255,255,255)
