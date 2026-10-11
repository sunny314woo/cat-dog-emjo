from io import BytesIO
import hashlib
import uuid
import zipfile
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
            assert 'no-transform' in response.headers['cache-control']
            assert response.headers['x-content-type-options']=='nosniff'
            im=Image.open(BytesIO(response.content)).convert('RGBA')
            assert im.size==(240,240)
            assert im.getchannel('A').getextrema()==(0,255)
            assert client.get(f'/sticker/api/files/{jid}/sticker-3-240.{extension}').status_code==403
        link=client.post(f'/sticker/api/generations/{jid}/share',json={'cell':1,'variant':'gif240'}).json()
        assert link['name']=='sticker-1-240.gif'
        assert link['has_transparency'] is True
        assert (link['width'],link['height'])==(240,240)
        with TestClient(app) as stranger:
            original=stranger.get(link['url'])
            assert original.status_code==200
            assert hashlib.sha256(original.content).hexdigest()==link['sha256']
            archive=stranger.get(link['archive_url'])
            assert archive.status_code==200
            assert archive.headers['content-type']=='application/zip'
            with zipfile.ZipFile(BytesIO(archive.content)) as zipped:
                assert zipped.namelist()==[link['name']]
                assert zipped.read(link['name'])==original.content
            assert stranger.get(link['archive_url'].replace('sticker-1','sticker-3')).status_code in (403,404)
        assert client.get(f'/sticker/api/files/{jid}/sticker-3-240.gif.zip').status_code==403
        assert client.get(f'/sticker/api/files/{jid}/stickers.zip').status_code==403
        for variant,name in [('png512','sticker-1.png'),('png240','sticker-1-240.png'),('webp512','sticker-1.webp')]:
            link=client.post(f'/sticker/api/generations/{jid}/share',json={'cell':1,'variant':variant}).json()
            original=client.get(link['url']).content
            with zipfile.ZipFile(BytesIO(client.get(link['archive_url']).content)) as zipped:
                assert zipped.read(name)==original


def test_wechat_gif_keeps_opaque_white_clothes_and_clear_background(tmp_path):
    from PIL import ImageDraw
    from server.imaging import save_wechat_gif
    im=Image.new('RGBA',(240,240))
    ImageDraw.Draw(im).rectangle((60,60,180,180),fill=(255,255,255,255))
    path=tmp_path/'white-shirt.gif';save_wechat_gif(im,path)
    result=Image.open(path).convert('RGBA')
    assert result.getpixel((120,120))==(255,255,255,255)
    assert result.getpixel((0,0))[3]==0
