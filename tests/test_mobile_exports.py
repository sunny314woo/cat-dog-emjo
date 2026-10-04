from io import BytesIO
import uuid
from PIL import Image
from fastapi.testclient import TestClient
from server.main import create_app
from server.settings import ROOT, Settings
from server.store import DemoStore


def test_wechat_240_exports_are_transparent_and_keep_claim_permissions(tmp_path):
    app=create_app(Settings(data_dir=tmp_path,public_url='http://testserver/sticker'),DemoStore(),start_worker=False)
    with TestClient(app) as client:
        client.get('/sticker/api/catalog')
        result=client.post('/sticker/api/style-previews',data={'request_id':str(uuid.uuid4())},
                          files={'photos':('photo.png',(ROOT/'assets/cat-photo.png').read_bytes(),'image/png')}).json()
        jid=result['id'];app.state.service.work_once()
        result=client.get('/sticker/api/generations/'+jid).json()
        client.post('/sticker/api/generations/'+jid+'/style',json={'style':result['preview_styles'][0]['id']})
        app.state.service.work_once()
        for extension in ('png','gif'):
            assert client.get(f'/sticker/api/files/{jid}/sticker-1-240.{extension}').status_code==403
        client.post(f'/sticker/api/generations/{jid}/claim',json={'cells':[1,2]})
        for extension in ('png','gif'):
            (tmp_path/'jobs'/jid/f'sticker-1-240.{extension}').unlink()
        for extension in ('png','gif'):
            response=client.get(f'/sticker/api/files/{jid}/sticker-1-240.{extension}')
            assert response.status_code==200
            assert response.headers['content-type'].startswith('image/'+extension)
            im=Image.open(BytesIO(response.content)).convert('RGBA')
            assert im.size==(240,240)
            assert im.getchannel('A').getextrema()==(0,255)
            assert client.get(f'/sticker/api/files/{jid}/sticker-3-240.{extension}').status_code==403
        link=client.post(f'/sticker/api/generations/{jid}/share',json={'cell':1,'variant':'gif240'}).json()
        assert link['name']=='sticker-1-240.gif'
        with TestClient(app) as stranger:
            assert stranger.get(link['url']).status_code==200


def test_wechat_gif_keeps_opaque_white_clothes_and_clear_background(tmp_path):
    from PIL import ImageDraw
    from server.imaging import save_wechat_gif
    im=Image.new('RGBA',(240,240))
    ImageDraw.Draw(im).rectangle((60,60,180,180),fill=(255,255,255,255))
    path=tmp_path/'white-shirt.gif';save_wechat_gif(im,path)
    result=Image.open(path).convert('RGBA')
    assert result.getpixel((120,120))==(255,255,255,255)
    assert result.getpixel((0,0))[3]==0
