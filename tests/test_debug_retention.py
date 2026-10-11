import uuid
import pytest
from fastapi.testclient import TestClient
from server.main import create_app
from server.settings import ROOT, Settings
from server.store import DemoStore


def ready_job(client,service,consent=False):
    catalog=client.get('/sticker/api/catalog').json()
    response=client.post('/sticker/api/generations',
        data={'request_id':str(uuid.uuid4()),'style':catalog['styles'][0]['id'],
              'calibration_consent':str(consent).lower()},
        files={'photos':('photo.png',(ROOT/'assets/cat-photo.png').read_bytes(),'image/png')})
    assert response.status_code==200,response.text
    jid=response.json()['id']
    assert service.work_once()
    job=client.get('/sticker/api/generations/'+jid).json()
    assert job['state']=='READY'
    return job


def test_default_asset_expiry_still_removes_files(tmp_path,monkeypatch):
    monkeypatch.delenv('EMJO_DEBUG_RETAIN_ASSETS',raising=False)
    settings=Settings(mode='demo',data_dir=tmp_path)
    assert not settings.debug_retain_assets
    app=create_app(settings,DemoStore(),start_worker=False)
    service=app.state.service
    with TestClient(app) as client:
        job=ready_job(client,service)
        jid=job['id']
        assert client.post(f'/sticker/api/generations/{jid}/claim',json={'cells':[1,2]}).status_code==200
        folder=tmp_path/'jobs'/jid
        assert folder.is_dir()
        service.clock=lambda:job['expires']+1
        service.maintenance()

        assert not folder.exists()
        assert client.get('/sticker/api/generations/'+jid).json()['state']=='EXPIRED'
        assert client.get(f'/sticker/api/files/{jid}/sticker-1.png').status_code in (409,410)


def test_debug_retention_keeps_downloads_without_granting_entitlements(tmp_path):
    app=create_app(Settings(mode='demo',data_dir=tmp_path,debug_retain_assets=True,
                           public_url='http://testserver/sticker'),
                   DemoStore(),start_worker=False)
    service=app.state.service
    with TestClient(app) as client:
        job=ready_job(client,service)
        jid=job['id']
        assert client.post(f'/sticker/api/generations/{jid}/claim',json={'cells':[1,2]}).status_code==200
        file_url=f'/sticker/api/files/{jid}/sticker-1.png'
        original=client.get(file_url).content
        before=client.get('/sticker/api/me').json()
        with service.store.transaction() as tx:
            deadline=tx.get('jobs',jid)['expires']
        service.clock=lambda:deadline+1
        service.maintenance()

        assert (tmp_path/'jobs'/jid).is_dir()
        assert client.get('/sticker/api/generations/'+jid).json()['state']=='READY'
        response=client.get(file_url)
        assert response.status_code==200
        assert response.content==original
        assert client.get(f'/sticker/api/files/{jid}/sticker-3.png').status_code==403
        assert client.get(f'/sticker/api/files/{jid}/stickers.zip').status_code==403
        assert client.post(f'/sticker/api/generations/{jid}/claim',json={'cells':[1,3]}).status_code==409
        after=client.get('/sticker/api/me').json()
        assert after['trial_available']==before['trial_available']==False
        assert after['pack_balance']==before['pack_balance']==0
        catalog=client.get('/sticker/api/catalog').json()
        another=client.post('/sticker/api/generations',
            data={'request_id':str(uuid.uuid4()),'style':catalog['styles'][0]['id']},
            files={'photos':('photo.png',(ROOT/'assets/cat-photo.png').read_bytes(),'image/png')})
        assert another.status_code==402

        share=client.post(f'/sticker/api/generations/{jid}/share',json={'cell':1,'variant':'png512'})
        assert share.status_code==200
        assert share.json()['expires']>service.clock()
        assert client.post(f'/sticker/api/generations/{jid}/share',json={'cell':3}).status_code==403
        with TestClient(app) as stranger:
            assert stranger.get(file_url).status_code==404
            assert stranger.get(share.json()['url']).status_code==200
            service.clock=lambda:share.json()['expires']+1
            assert stranger.get(share.json()['url']).status_code==404
        assert client.get(file_url).status_code==200
        service.s.debug_retain_assets=False
        service.maintenance()
        assert not (tmp_path/'jobs'/jid).exists()


def test_debug_retention_does_not_keep_codes_or_revoked_calibration(tmp_path):
    app=create_app(Settings(mode='demo',data_dir=tmp_path,debug_retain_assets=True,
                           calibration_enabled=True),DemoStore(),start_worker=False)
    service=app.state.service
    with TestClient(app) as client:
        job=ready_job(client,service,consent=True)
        jid=job['id']
        retained=tmp_path/'jobs'/jid
        calibration=tmp_path/'calibration'/jid
        assert calibration.is_dir()
        assert client.post('/sticker/api/auth/code',json={'email':'retention@example.com'}).status_code==200
        initial=service.clock()
        service.clock=lambda:initial+601
        assert client.post('/sticker/api/auth/verify',
                           json={'email':'retention@example.com','code':'123456'}).status_code==400

        expired_case=tmp_path/'calibration'/'expired-case'
        expired_case.mkdir()
        with service.store.transaction() as tx:
            tx.put('calibration','expired-case',{'id':'expired-case','expires':initial-1})
        service.clock=lambda:initial+2*86400
        service.maintenance()
        with service.store.transaction() as tx:
            assert tx.all('codes')==[]
            assert tx.get('calibration','expired-case') is None
        assert not expired_case.exists()
        assert calibration.is_dir()
        assert retained.is_dir()
        assert client.delete(f'/sticker/api/generations/{jid}/calibration').status_code==200
        assert not calibration.exists()
        assert retained.is_dir()
        assert client.get('/sticker/api/generations/'+jid).json()['state']=='READY'


@pytest.mark.parametrize('cancel',[False,True])
def test_debug_keeps_generated_previews_but_cleans_uploaded_originals(tmp_path,cancel):
    app=create_app(Settings(mode='demo',data_dir=tmp_path,debug_retain_assets=True),DemoStore(),start_worker=False)
    service=app.state.service
    with TestClient(app) as client:
        client.get('/sticker/api/catalog')
        response=client.post('/sticker/api/style-previews',data={'request_id':str(uuid.uuid4())},
                             files={'photos':('photo.png',(ROOT/'assets/cat-photo.png').read_bytes(),'image/png')})
        jid=response.json()['id'];service.work_once()
        folder=tmp_path/'jobs'/jid
        assert list(folder.glob('input-*.jpg'))
        if cancel:
            assert client.delete('/sticker/api/style-previews/'+jid).status_code==200
        else:
            with service.store.transaction() as tx:deadline=tx.get('jobs',jid)['expires']
            service.clock=lambda:deadline+1
            service.maintenance()
        assert not list(folder.glob('input-*.jpg'))
        assert (folder/'style-choice-1.jpg').is_file()
        assert client.get('/sticker/api/style-previews/'+jid+'/1').status_code in (409,410)
        assert client.get('/sticker/api/me').json()['trial_available']
