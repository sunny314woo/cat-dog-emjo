import uuid

import pytest
from fastapi.testclient import TestClient

from server.main import create_app
from server.providers import Providers, ProviderError
from server.settings import ROOT, Settings
from server.store import DemoStore


@pytest.fixture
def workflow(tmp_path):
    settings=Settings(data_dir=tmp_path)
    providers=Providers(settings)
    app=create_app(settings,DemoStore(),providers,False)
    with TestClient(app) as client:
        client.get('/sticker/api/catalog')
        yield client,app.state.service,providers


def preview(client,key=None):
    return client.post('/sticker/api/style-previews',data={'request_id':key or str(uuid.uuid4())},
                       files={'photos':('original.png',(ROOT/'assets/cat-photo.png').read_bytes(),'image/png')})


def test_original_and_only_selected_style_reach_final_request(workflow,monkeypatch):
    client,service,providers=workflow
    calls=[]
    original=providers.generate
    def capture(prompt,photos):
        calls.append((prompt,photos));return original(prompt,photos)
    monkeypatch.setattr(providers,'generate',capture)
    key=str(uuid.uuid4());first=preview(client,key).json();jid=first['id']
    assert first['state']=='PREVIEW_QUEUED'
    assert preview(client,key).json()['id']==jid
    assert service.work_once()
    folder=service.s.data_dir/'jobs'/jid
    source=(folder/'input-1.jpg').read_bytes()
    result=client.get('/sticker/api/generations/'+jid).json()
    assert result['state']=='STYLE_READY'
    assert len(result['preview_styles'])==4
    assert client.get('/sticker/api/style-previews/'+jid+'/2').status_code==200
    assert client.get('/sticker/api/files/'+jid+'/sticker-1.png').status_code==409
    with TestClient(client.app) as stranger:
        assert stranger.get('/sticker/api/style-previews/'+jid+'/2').status_code==404
    chosen=result['preview_styles'][1]['id']
    reference=(folder/'style-reference-2.jpg').read_bytes()
    path='/sticker/api/generations/'+jid+'/style'
    assert client.post(path,json={'style':chosen}).json()['state']=='QUEUED'
    assert client.post(path,json={'style':chosen}).status_code==200
    assert client.post(path,json={'style':result['preview_styles'][0]['id']}).status_code==409
    assert service.work_once()
    assert len(calls)==1
    assert calls[0][1]==[source,reference]
    assert '最后第2张' in calls[0][0]
    assert not (folder/'input-1.jpg').exists()
    assert client.get('/sticker/api/generations/'+jid).json()['state']=='READY'
    assert not service.work_once()


def test_expired_and_cancelled_preview_release_reservation_once(workflow):
    client,service,_=workflow
    jid=preview(client).json()['id'];service.work_once()
    assert not client.get('/sticker/api/me').json()['trial_available']
    assert client.delete('/sticker/api/style-previews/'+jid).status_code==200
    assert client.delete('/sticker/api/style-previews/'+jid).status_code==200
    assert client.get('/sticker/api/me').json()['trial_available']
    assert not (service.s.data_dir/'jobs'/jid).exists()
    jid=preview(client).json()['id'];service.work_once()
    with service.store.transaction() as tx:expires=tx.get('jobs',jid)['expires']
    service.clock=lambda:expires+1
    service.maintenance();service.maintenance()
    assert client.get('/sticker/api/me').json()['trial_available']
    assert client.get('/sticker/api/style-previews/'+jid+'/1').status_code!=200


def test_paid_final_failure_does_not_charge_twice(workflow,monkeypatch):
    client,service,providers=workflow
    client.post('/sticker/api/auth/code',json={'email':'test@example.com'})
    client.post('/sticker/api/auth/verify',json={'email':'test@example.com','code':'123456'})
    uid=service.digest('test@example.com')
    with service.store.transaction() as tx:
        user=tx.get('users',uid);user['paid_once']=True;tx.put('users',uid,user)
        service._grant(tx,'test-grant',uid,1,'test')
    jid=preview(client).json()['id'];service.work_once()
    assert client.get('/sticker/api/me').json()['pack_pending']==1
    result=client.get('/sticker/api/generations/'+jid).json()
    client.post('/sticker/api/generations/'+jid+'/style',json={'style':result['preview_styles'][0]['id']})
    def fail(*args):raise ProviderError('quota','image_quota_exceeded',{'status':429,'upstream_code':'QuotaExceeded'})
    monkeypatch.setattr(providers,'generate',fail)
    service.work_once();assert not service.work_once()
    me=client.get('/sticker/api/me').json()
    assert (me['pack_balance'],me['pack_used'],me['pack_pending'])==(1,0,0)
    with service.store.transaction() as tx:
        job=tx.get('jobs',jid)
        assert job['failure_stage']=='generation'
        assert job['provider_diagnostics']['upstream_code']=='QuotaExceeded'


def test_preview_recovery_uses_saved_output_without_second_call(workflow,monkeypatch):
    client,service,providers=workflow
    jid=preview(client).json()['id']
    folder=service.s.data_dir/'jobs'/jid
    (folder/'style-output.png').write_bytes((ROOT/'assets/cat-styles.png').read_bytes())
    with service.store.transaction() as tx:
        job=tx.get('jobs',jid);job.update(state='PREVIEW_GENERATING',lease_until=0);tx.put('jobs',jid,job)
    def unexpected(*args):raise AssertionError('must not call the model again')
    monkeypatch.setattr(providers,'generate_styles',unexpected)
    service.maintenance();service.work_once()
    assert client.get('/sticker/api/generations/'+jid).json()['state']=='STYLE_READY'
    assert (folder/'input-1.jpg').exists()


def test_soft_matting_bridge_does_not_merge_solid_subjects():
    from PIL import Image, ImageDraw
    from server.slicing import extract_subjects
    image=Image.new('RGBA',(600,600))
    draw=ImageDraw.Draw(image)
    for y in range(3):
        for x in range(3):draw.rectangle((x*200+40,y*200+40,x*200+160,y*200+160),fill=(80,100,120,255))
    draw.rectangle((160,80,240,100),fill=(80,100,120,145))
    assert len(extract_subjects(image,core_threshold=160))==9
    draw.rectangle((160,80,240,100),fill=(80,100,120,255))
    with pytest.raises(ValueError,match='主体数量'):
        extract_subjects(image,core_threshold=160)
