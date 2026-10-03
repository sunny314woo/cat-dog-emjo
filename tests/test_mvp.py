import io
import uuid
import zipfile
from pathlib import Path
import pytest
from PIL import Image
from fastapi.testclient import TestClient
from server.settings import Settings, ROOT
from server.store import DemoStore
from server.providers import Providers
from server.main import create_app
from server.catalog import build_prompt, STYLES

@pytest.fixture
def setup(tmp_path):
    settings=Settings(data_dir=tmp_path,calibration_enabled=True)
    app=create_app(settings,DemoStore(tmp_path/'state.json'),Providers(settings),False)
    with TestClient(app) as client:
        catalog=client.get('/sticker/api/catalog').json()
        yield client,app.state.service,catalog

def create(client,catalog,key=None):
    return client.post('/sticker/api/generations',data={'request_id':key or str(uuid.uuid4()),'style':catalog['styles'][0]['id'],'calibration_consent':'true'},files=[('photos',('photo.png',(ROOT/'assets/cat-photo.png').read_bytes(),'image/png'))])

def test_claim_security_transparency_and_ttl(setup):
    client,service,catalog=setup
    key=str(uuid.uuid4());r=create(client,catalog,key);assert r.status_code==200,r.text
    jid=r.json()['id'];assert create(client,catalog,key).json()['id']==jid
    assert service.work_once()
    base='/sticker/api';result=client.get(base+'/generations/'+jid).json();assert result['state']=='READY',result
    assert client.get(base+f'/files/{jid}/stickers.zip').status_code==403
    p=client.get(base+f'/files/{jid}/preview-1.jpg');assert Image.open(io.BytesIO(p.content)).mode=='RGB'
    assert client.post(base+f'/generations/{jid}/claim',json={'cells':[1,2]}).status_code==200
    assert client.post(base+f'/generations/{jid}/claim',json={'cells':[1,3]}).status_code==409
    image=Image.open(io.BytesIO(client.get(base+f'/files/{jid}/sticker-1.png').content));assert image.mode=='RGBA';assert image.getchannel('A').getextrema()==(0,255)
    assert client.get(base+f'/files/{jid}/sticker-3.png').status_code==403
    assert create(client,catalog).status_code==402
    assert client.post(base+'/demo/unlock/'+jid,json={}).status_code==200
    archive=zipfile.ZipFile(io.BytesIO(client.get(base+f'/files/{jid}/stickers.zip').content));assert len([n for n in archive.namelist() if n.endswith('.png')])==10
    with TestClient(client.app) as stranger:assert stranger.get(base+f'/files/{jid}/sticker-1.png').status_code==404
    assert (service.s.data_dir/'calibration'/jid).exists()
    assert not list((service.s.data_dir/'jobs'/jid).glob('input-*.jpg'))
    service.clock=lambda:result['expires']+1;service.maintenance()
    assert not (service.s.data_dir/'jobs'/jid).exists()
    assert (service.s.data_dir/'calibration'/jid).exists()
    assert client.delete(base+f'/generations/{jid}/calibration').status_code==200
    assert not (service.s.data_dir/'calibration'/jid).exists()

def test_otp_email_uniqueness_and_logout(setup):
    client,service,catalog=setup;base='/sticker/api'
    jid=create(client,catalog).json()['id']
    assert client.post(base+'/auth/code',json={'email':'Owner@Example.com'}).status_code==200
    for _ in range(5):assert client.post(base+'/auth/verify',json={'email':'owner@example.com','code':'000000'}).status_code==400
    assert client.post(base+'/auth/verify',json={'email':'owner@example.com','code':'123456'}).status_code==400
    service.clock=lambda:__import__('time').time()+61
    assert client.post(base+'/auth/code',json={'email':'owner@example.com'}).status_code==200
    assert client.post(base+'/auth/verify',json={'email':'OWNER@example.com','code':'123456'}).json()['email']=='owner@example.com'
    client.post(base+'/auth/logout',json={})
    assert client.get(base+'/generations/'+jid).status_code==404

def test_public_allowlist_and_prompt(setup):
    client,service,catalog=setup
    r=client.get('/app.js?name=server/settings.py');assert 'use strict' in r.text;assert 'dataclass' not in r.text
    assert client.get('/server/settings.py').status_code==404
    assert client.get('/doubao/').status_code==404
    assert len(STYLES)==13
    for s in catalog['styles']:
        p=build_prompt(s['id'],3,True);assert '冲鸭' not in p;assert '第一张' in p
    with pytest.raises(ValueError):build_prompt(catalog['styles'][0]['id'],4,True)


def test_cutline_guard_rejects_legacy_crossing_art():
    from server.imaging import validate_grid_boundaries
    with Image.open(ROOT/'assets/cat-grid.png') as source:
        with pytest.raises(ValueError, match='切线'):validate_grid_boundaries(source.convert('RGBA'))
    from PIL import ImageDraw
    clean=Image.new('RGBA',(600,600))
    draw=ImageDraw.Draw(clean)
    for row in range(3):
        for col in range(3):draw.ellipse((col*200+30,row*200+30,col*200+170,row*200+170),fill='orange')
    validate_grid_boundaries(clean)

def signed_in(service,email,referral=None):
    _,session=service.session()
    service.request_code(session['id'],email)
    service.verify_code(session['id'],email,'123456',referral)
    return session['id'],service.current(session['id'])[1]

def payment_order(service,uid,oid,product='PACK_3',jid=None):
    with service.store.transaction() as tx:
        tx.put('orders',oid,{'id':oid,'user_id':uid,'job_id':jid,'product':product,
            'price_id':'pri_test','state':'PENDING','transaction_id':'txn_'+oid,'created':service.clock()})
    return {'id':'txn_'+oid,'status':'completed','custom_data':{'emjo_order_id':oid},
        'items':[{'quantity':1,'price':{'id':'pri_test','product_id':'pro_test'}}],
        'details':{'totals':{'total':'1999'}},'currency_code':'USD'}

def test_payment_referral_idempotency_refund_and_failure(setup,monkeypatch):
    _,service,catalog=setup
    monkeypatch.setenv('PADDLE_PRODUCT_ID','pro_test')
    inviter_sid,inviter=signed_in(service,'inviter@example.com')
    buyer_sid,buyer=signed_in(service,'buyer@example.com',inviter['referral_code'])
    data=payment_order(service,buyer['id'],'order1')
    service.complete_payment('event1',data)
    service.complete_payment('event1',data)
    service.complete_payment('event2',data)
    assert service.me(buyer_sid)['pack_balance']==3
    assert service.me(inviter_sid)['pack_balance']==1
    # Failed provider work refunds exactly the reserved credit, without spending it twice.
    job=service.create_job(buyer_sid,str(uuid.uuid4()),[(ROOT/'assets/dog-photo.jpg').read_bytes()],catalog['styles'][0]['id'])
    assert service.me(buyer_sid)['pack_balance']==2
    def fail(*args):raise RuntimeError('simulated provider failure')
    monkeypatch.setattr(service.providers,'generate',fail)
    service.work_once();service.work_once()
    assert service.me(buyer_sid)['pack_balance']==3
    assert service.job(buyer_sid,job['id'])['state']=='FAILED'
    service.refund('refund1','txn_order1');service.refund('refund2','txn_order1')
    assert service.me(buyer_sid)['pack_balance']==0
    assert service.me(inviter_sid)['pack_balance']==0
    service.complete_payment('late-event',data)
    assert service.me(buyer_sid)['pack_balance']==0
    # A second paid order from the same invitee never creates another referral reward.
    service.complete_payment('event3',payment_order(service,buyer['id'],'order2','PACK_1'))
    assert service.me(buyer_sid)['pack_balance']==1
    assert service.me(inviter_sid)['pack_balance']==0

def test_first_unlock_reuses_result_without_extra_pack(setup,monkeypatch):
    client,service,catalog=setup
    monkeypatch.setenv('PADDLE_PRODUCT_ID','pro_test')
    jid=create(client,catalog).json()['id'];service.work_once()
    client.post('/sticker/api/auth/code',json={'email':'unlock@example.com'})
    client.post('/sticker/api/auth/verify',json={'email':'unlock@example.com','code':'123456'})
    sid=service.digest(client.cookies.get('emjo_session'));user=service.current(sid)[1]
    data=payment_order(service,user['id'],'unlock','FIRST_PACK_UNLOCK',jid)
    service.complete_payment('unlock-event',data)
    service.complete_payment('unlock-duplicate',data)
    assert service.job(sid,jid)['unlocked']
    assert service.me(sid)['pack_balance']==0
    with service.store.transaction() as tx:
        assert len(tx.all('jobs'))==1
        assert len(tx.all('mail'))==1
    service.refund('refund-unlock','txn_unlock')
    assert client.get(f'/sticker/api/files/{jid}/stickers.zip').status_code==403


def test_refunded_paid_pack_cannot_claim_free_stickers(setup,monkeypatch):
    _,service,catalog=setup
    from server.service import RuleError
    monkeypatch.setenv('PADDLE_PRODUCT_ID','pro_test')
    sid,user=signed_in(service,'paid@example.com')
    service.complete_payment('paid-event',payment_order(service,user['id'],'paid','PACK_1'))
    job=service.create_job(sid,str(uuid.uuid4()),[(ROOT/'assets/cat-photo.png').read_bytes()],catalog['styles'][0]['id'])
    service.work_once();assert service.job(sid,job['id'])['state']=='READY'
    service.refund('paid-refund','txn_paid')
    with pytest.raises(RuleError,match='首次体验'):service.claim(sid,job['id'],[1,2])
    with pytest.raises(RuleError):service.authorize_file(sid,job['id'],'sticker-1.png')

def test_subject_extraction_keeps_tail_across_logical_cutline():
    from PIL import ImageDraw
    from server.slicing import extract_subjects,fit_subject
    canvas=Image.new('RGBA',(600,600));draw=ImageDraw.Draw(canvas)
    for row in range(3):
        for col in range(3):draw.rectangle((col*200+40,row*200+40,col*200+120,row*200+120),fill=(230,100,50,255))
    # First subject's tail extends beyond x=200; it must remain with that subject.
    draw.rectangle((110,80,220,95),fill=(20,180,90,255))
    subjects=extract_subjects(canvas)
    assert subjects[0].width>=180
    assert (20,180,90,255) in subjects[0].getdata()
    assert (20,180,90,255) not in subjects[1].getdata()
    for subject in subjects:
        delivery=fit_subject(subject)
        assert delivery.size==(512,512)
        box=delivery.getbbox();assert box[0]>0 and box[1]>0 and box[2]<512 and box[3]<512


def test_touching_subjects_fail_instead_of_cutting():
    from PIL import ImageDraw
    from server.slicing import extract_subjects
    canvas=Image.new('RGBA',(600,600));draw=ImageDraw.Draw(canvas)
    for row in range(3):
        for col in range(3):draw.rectangle((col*200+40,row*200+40,col*200+120,row*200+120),fill='orange')
    draw.rectangle((110,80,250,95),fill='orange')
    with pytest.raises(ValueError,match='轮廓'):extract_subjects(canvas)

def test_share_links_are_cell_scoped_expiring_and_keep_alpha(setup):
    client,service,catalog=setup
    base='/sticker/api';jid=create(client,catalog).json()['id'];service.work_once()
    assert client.post(base+f'/generations/{jid}/share',json={'cell':3}).status_code==403
    client.post(base+f'/generations/{jid}/claim',json={'cells':[1,2]})
    sid=service.digest(client.cookies.get('emjo_session'))
    for variant,size in [('png512',512),('png256',256),('webp512',512)]:
        data=service.share_link(sid,jid,1,variant)
        from urllib.parse import urlparse,parse_qs
        token=parse_qs(urlparse(data['url']).query)['token'][0]
        with TestClient(client.app) as guest:
            url=base+f"/files/{jid}/{data['name']}?token={token}"
            response=guest.get(url);assert response.status_code==200
            im=Image.open(io.BytesIO(response.content));assert im.size==(size,size)
            assert im.convert('RGBA').getchannel('A').getextrema()[0]==0
            assert guest.get(base+f'/files/{jid}/sticker-3.png?token='+token).status_code==404
    service.clock=lambda:data['expires']+1
    assert client.get(url).status_code in (404,410)


def test_live_free_budget_is_optional(setup,monkeypatch):
    client,service,catalog=setup
    service.s.mode='live'
    monkeypatch.delenv('EMJO_DAILY_FREE_BUDGET_CNY',raising=False)
    monkeypatch.delenv('EMJO_COST_PER_GENERATION_CNY',raising=False)
    response=create(client,catalog)
    assert response.status_code==200,response.text
    with service.store.transaction() as tx:
        assert tx.all('budgets')==[]


def test_paddlejs_checkout_reuses_order_and_does_not_need_write_api(setup,monkeypatch):
    _,service,_=setup
    sid,user=signed_in(service,'pay@example.com')
    service.s.mode='live'
    monkeypatch.setenv('PADDLE_PRICE_PACK_3_ID','pri_three')
    monkeypatch.setenv('PADDLE_PRODUCT_ID','pro_test')
    monkeypatch.setenv('PADDLE_WEBHOOK_SECRET','test-secret')
    service.providers.paddle=lambda *args:pytest.fail('Opening checkout must not call a write API')
    first=service.checkout(sid,'PACK_3')
    assert first['items']==[{'priceId':'pri_three','quantity':1}]
    assert first['customer']['email']=='pay@example.com'
    assert first==service.checkout(sid,'PACK_3')
    with service.store.transaction() as tx:
        assert len(tx.all('orders'))==1
        assert tx.get('orders',first['order_id'])['state']=='PENDING'
    assert service.me(sid)['pack_balance']==0


def test_api_cors_only_allows_product_origin(tmp_path):
    settings=Settings(data_dir=tmp_path,public_url='https://wisteriasoftware.uk/sticker')
    app=create_app(settings,DemoStore(tmp_path/'state.json'),Providers(settings),False)
    with TestClient(app,base_url='https://api.wisteriasoftware.uk') as client:
        r=client.options('/sticker/api/checkout',headers={'Origin':'https://wisteriasoftware.uk','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'})
        assert r.status_code==200
        assert r.headers['access-control-allow-origin']=='https://wisteriasoftware.uk'
        assert r.headers['access-control-allow-credentials']=='true'
        assert client.post('/sticker/api/auth/logout',headers={'Origin':'https://evil.example'}).status_code==403
