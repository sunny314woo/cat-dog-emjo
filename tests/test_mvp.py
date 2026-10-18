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
from server.service import RuleError

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
    archive=zipfile.ZipFile(io.BytesIO(client.get(base+f'/files/{jid}/stickers.zip').content));assert len([n for n in archive.namelist() if n.endswith('.png')])==28
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
    history=client.get(base+'/account/history')
    assert history.status_code==200
    assert any(item['id']==jid for item in history.json()['jobs'])
    client.post(base+'/auth/logout',json={})
    assert client.get(base+'/generations/'+jid).status_code==404
    assert client.get(base+'/account/history').status_code==401

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


def test_signed_webhook_acknowledges_without_waiting_for_paddle(setup,monkeypatch):
    import hashlib,hmac,json,time
    client,service,_=setup
    service.s.mode='live';monkeypatch.setenv('PADDLE_WEBHOOK_SECRET','notification-secret')
    calls=[]
    service.providers.paddle=lambda *args:calls.append(args)
    event={'event_id':'evt_completed','event_type':'transaction.completed','data':{'id':'txn_checkout'}}
    raw=json.dumps(event).encode();stamp=str(int(time.time()))
    signature=hmac.new(b'notification-secret',stamp.encode()+b':'+raw,hashlib.sha256).hexdigest()
    url='/sticker/api/webhooks/paddle'
    assert client.post(url,content=raw).status_code==401
    with service.store.transaction() as tx:assert not tx.all('payment_notifications')
    for _ in range(2):
        assert client.post(url,content=raw,headers={'Paddle-Signature':f'ts={stamp};h1={signature}'}).status_code==200
    assert not calls
    with service.store.transaction() as tx:
        rows=tx.all('payment_notifications');assert len(rows)==1 and rows[0]['state']=='PENDING'
        assert 'data' not in rows[0]


def test_payment_and_mail_workers_continue_during_generation(tmp_path):
    import threading
    app=create_app(Settings(data_dir=tmp_path),DemoStore(),start_worker=True)
    service=app.state.service
    generating=threading.Event();release=threading.Event();payments=threading.Event();mail=threading.Event()
    def slow_generation():
        generating.set();release.wait(5)
    service.work_once=slow_generation
    service.maintenance=lambda:None
    service.payment_once=payments.set
    service.mail_once=mail.set
    with TestClient(app):
        try:
            assert generating.wait(1)
            assert payments.wait(1) and mail.wait(1)
        finally:release.set()


def test_payment_notification_recovers_after_restart_and_provider_failure(setup,monkeypatch):
    from server.service import Service
    from server.providers import ProviderError
    _,service,_=setup
    monkeypatch.setenv('PADDLE_PRODUCT_ID','pro_test')
    sid,user=signed_in(service,'recover@example.com')
    actual=payment_order(service,user['id'],'recover')
    clock=[service.clock()];service.clock=lambda:clock[0]
    event={'event_id':'evt_recover','event_type':'transaction.completed','data':{'id':actual['id']}}
    service.enqueue_payment(event)
    service.providers.paddle=lambda *args:(_ for _ in ()).throw(ProviderError('unavailable'))
    assert service.payment_once()
    assert service.me(sid)['pack_balance']==0
    with service.store.transaction() as tx:
        row=tx.get('payment_notifications',event['event_id']);assert row['state']=='FAILED'
        clock[0]=row['next']
    recovered=Service(service.s,DemoStore(service.store.path),service.providers,clock=lambda:clock[0])
    recovered.providers.paddle=lambda *args:actual
    assert recovered.payment_once()
    assert recovered.me(sid)['pack_balance']==3
    recovered.enqueue_payment(event)
    assert not recovered.payment_once()
    recovered.enqueue_payment(dict(event,event_id='evt_second_delivery'))
    recovered.payment_once();assert recovered.me(sid)['pack_balance']==3


def test_interrupted_payment_notification_and_refund_before_completion(setup,monkeypatch):
    _,service,_=setup
    monkeypatch.setenv('PADDLE_PRODUCT_ID','pro_test')
    sid,user=signed_in(service,'early-refund@example.com')
    actual=payment_order(service,user['id'],'early')
    service.enqueue_payment({'event_id':'evt_refund','event_type':'adjustment.updated',
        'data':{'action':'refund','status':'approved','type':'full','transaction_id':actual['id']}})
    assert service.payment_once()
    service.enqueue_payment({'event_id':'evt_complete','event_type':'transaction.completed','data':{'id':actual['id']}})
    with service.store.transaction() as tx:
        row=tx.get('payment_notifications','evt_complete');row.update(state='PROCESSING',lease_until=service.clock()-1)
        tx.put('payment_notifications',row['id'],row)
    service.providers.paddle=lambda *args:actual
    assert service.payment_once()
    assert service.me(sid)['pack_balance']==0
    with service.store.transaction() as tx:assert tx.get('orders','early')['state']=='REFUNDED'


def test_wrong_product_notification_is_held_for_review(setup,monkeypatch):
    _,service,_=setup
    monkeypatch.setenv('PADDLE_PRODUCT_ID','pro_test')
    sid,user=signed_in(service,'mismatch@example.com')
    actual=payment_order(service,user['id'],'mismatch');actual['items'][0]['price']['id']='pri_wrong'
    service.enqueue_payment({'event_id':'evt_wrong','event_type':'transaction.completed','data':{'id':actual['id']}})
    service.providers.paddle=lambda *args:actual
    service.payment_once();assert service.me(sid)['pack_balance']==0
    with service.store.transaction() as tx:
        assert tx.get('orders','mismatch')['state']=='PENDING'
        assert tx.get('payment_notifications','evt_wrong')['state']=='REVIEW'
        assert tx.get('review','evt_wrong')
        order=tx.get('orders','mismatch');order['checkout_mode']='paddlejs';tx.put('orders','mismatch',order)
    service.s.mode='live'
    monkeypatch.setenv('PADDLE_PRICE_PACK_3_ID','pri_test')
    monkeypatch.setenv('PADDLE_WEBHOOK_SECRET','test-secret')
    with pytest.raises(RuleError,match='请勿重复付款'):
        service.checkout(sid,'PACK_3',order_id='mismatch')


def test_unlock_mail_retries_identical_payload_and_records_provider_id(setup,monkeypatch):
    from server.providers import ProviderError
    client,service,catalog=setup
    monkeypatch.setenv('PADDLE_PRODUCT_ID','pro_test')
    jid=create(client,catalog).json()['id'];service.work_once()
    client.post('/sticker/api/auth/code',json={'email':'delivery@example.com'})
    client.post('/sticker/api/auth/verify',json={'email':'delivery@example.com','code':'123456'})
    sid=service.digest(client.cookies.get('emjo_session'));user=service.current(sid)[1]
    service.complete_payment('evt_delivery',payment_order(service,user['id'],'delivery','FIRST_PACK_UNLOCK',jid))
    service.s.debug_retain_assets=True;clock=[service.clock()];service.clock=lambda:clock[0];calls=[]
    def send(*args):
        calls.append(args)
        if len(calls)==1:raise ProviderError('temporary mail failure')
        return 'resend-delivery-id'
    service.providers.email=send
    service.mail_once()
    first=client.get('/sticker/api/orders/delivery').json()
    assert first['state']=='PAID' and first['delivery_state']=='FAILED'
    with service.store.transaction() as tx:clock[0]=tx.get('mail','delivery-'+jid)['next']
    service.mail_once();service.mail_once()
    assert len(calls)==2 and calls[0]==calls[1]
    assert calls[1][0]=='delivery@example.com'
    assert calls[1][-1]==(service.s.data_dir/'jobs'/jid/'stickers.zip').read_bytes()
    with service.store.transaction() as tx:
        mail=tx.get('mail','delivery-'+jid);assert mail['state']=='SENT' and mail['provider_id']=='resend-delivery-id'
    assert client.get('/sticker/api/orders/delivery').json()['delivery_state']=='SENT'
    with TestClient(client.app) as stranger:assert stranger.get('/sticker/api/orders/delivery').status_code==404


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
    client.post('/sticker/api/auth/code',json={'email':'budget@example.com'})
    client.post('/sticker/api/auth/verify',json={'email':'budget@example.com','code':'123456'})
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


def test_existing_account_trial_does_not_grant_second_anonymous_free_claim(setup):
    client,service,catalog=setup
    sid,user=signed_in(service,'repeat@example.com')
    with service.store.transaction() as tx:
        account=tx.get('users',user['id']);account['trial_used']=True;tx.put('users',user['id'],account)
        tx.put('jobs','old-trial',{'id':'old-trial','session_id':sid,'user_id':user['id'],
            'state':'READY','free':True,'unlocked':False,'selected':[1,2],'created':1})
    # Model the customer's second device: an anonymous job is associated during OTP login.
    _,session=service.session();other_sid=session['id']
    anonymous=service.create_job(other_sid,str(uuid.uuid4()),[(ROOT/'assets/cat-photo.png').read_bytes()],catalog['styles'][0]['id'])
    service.clock=lambda:__import__('time').time()+61
    service.request_code(other_sid,'repeat@example.com')
    service.verify_code(other_sid,'repeat@example.com','123456')
    merged=service.job(other_sid,anonymous['id'])
    assert merged['free'] is False
    assert merged['unlocked'] is False
    assert service.account_history(other_sid)['jobs'][0]['id']==anonymous['id']
    with service.store.transaction() as tx:
        row=tx.get('jobs',anonymous['id']);row['state']='READY';tx.put('jobs',row['id'],row)
    with pytest.raises(RuleError) as error:
        service.claim(other_sid,anonymous['id'],[1,2])
    assert error.value.status==403


def test_existing_pack_is_reserved_when_anonymous_job_is_claimed_during_generation(setup):
    _,service,catalog=setup
    _,user=signed_in(service,'pack-owner@example.com')
    with service.store.transaction() as tx:
        account=tx.get('users',user['id']);account['trial_used']=True;tx.put('users',user['id'],account)
        tx.put('grants','existing-pack',{'id':'existing-pack','user_id':user['id'],'available':1,
            'quantity':1,'consumed':0,'revoked':False,'source':'test','created':1})
    _,session=service.session();sid=session['id']
    job=service.create_job(sid,str(uuid.uuid4()),[(ROOT/'assets/cat-photo.png').read_bytes()],catalog['styles'][0]['id'])
    service.clock=lambda:__import__('time').time()+61
    service.request_code(sid,'pack-owner@example.com')
    def attach_during_provider(*args):
        service.verify_code(sid,'pack-owner@example.com','123456')
        return (ROOT/'assets/cat-grid.png').read_bytes()
    service.providers.generate=attach_during_provider
    service.work_once()
    with service.store.transaction() as tx:
        grant=tx.get('grants','existing-pack');row=tx.get('jobs',job['id'])
    assert (grant['available'],grant['consumed'])==(0,1)
    assert row['grant_id']=='existing-pack' and row['free'] is False and row['unlocked'] is True


def test_pack_purchased_after_login_can_resume_anonymous_style_preview(setup):
    _,service,catalog=setup
    _,user=signed_in(service,'style-pack-owner@example.com')
    with service.store.transaction() as tx:
        account=tx.get('users',user['id']);account['trial_used']=True;tx.put('users',user['id'],account)
    _,session=service.session();sid=session['id']
    preview=service.create_job(sid,str(uuid.uuid4()),[(ROOT/'assets/cat-photo.png').read_bytes()],
                               None,preview=True)
    service.clock=lambda:__import__('time').time()+61
    service.request_code(sid,'style-pack-owner@example.com')
    service.verify_code(sid,'style-pack-owner@example.com','123456')
    with service.store.transaction() as tx:
        row=tx.get('jobs',preview['id']);row['state']='STYLE_READY';tx.put('jobs',row['id'],row)
        tx.put('grants','later-pack',{'id':'later-pack','user_id':user['id'],'available':1,
            'quantity':1,'consumed':0,'revoked':False,'source':'test','created':2})
    selected=service.choose_style(sid,preview['id'],catalog['styles'][0]['id'])
    assert selected['state']=='QUEUED' and selected['unlocked'] is True
    with service.store.transaction() as tx:
        assert tx.get('grants','later-pack')['available']==0


def test_pending_unlock_orders_stay_bound_per_work_and_are_resumable(setup,monkeypatch):
    _,service,_=setup
    sid,user=signed_in(service,'orders@example.com')
    service.s.mode='live'
    monkeypatch.setenv('PADDLE_PRICE_FIRST_PACK_UNLOCK_ID','pri_first')
    monkeypatch.setenv('PADDLE_PRICE_PACK_1_ID','pri_one')
    monkeypatch.setenv('PADDLE_PRODUCT_ID','pro_test')
    monkeypatch.setenv('PADDLE_WEBHOOK_SECRET','test-secret')
    for jid in ('work-old','work-new'):
        folder=service.s.data_dir/'jobs'/jid;folder.mkdir(parents=True)
        (folder/'stickers.zip').write_bytes(b'zip')
        with service.store.transaction() as tx:
            tx.put('jobs',jid,{'id':jid,'session_id':sid,'user_id':user['id'],'state':'READY',
                'free':True,'unlocked':False,'selected':[],'expires':service.clock()+86400,'created':service.clock()})
    now=[100000]
    service.clock=lambda:now[0]
    old=service.checkout(sid,'FIRST_PACK_UNLOCK','work-old')
    pack=service.checkout(sid,'PACK_1')
    assert pack['order_id']!=old['order_id']
    with pytest.raises(RuleError) as early:
        service.checkout(sid,'FIRST_PACK_UNLOCK','work-new')
    assert early.value.status==409
    now[0]+=86401
    with pytest.raises(RuleError) as late:
        service.checkout(sid,'FIRST_PACK_UNLOCK','work-new')
    assert late.value.status==409
    assert service.checkout(sid,'FIRST_PACK_UNLOCK','work-old',old['order_id'])==old
    with service.store.transaction() as tx:
        assert tx.get('orders',old['order_id'])['job_id']=='work-old'
        assert tx.get('orders',pack['order_id'])['product']=='PACK_1'
    history=service.account_history(sid)
    assert {o['id'] for o in history['orders']}=={old['order_id'],pack['order_id']}


def test_api_cors_only_allows_product_origin(tmp_path):
    settings=Settings(data_dir=tmp_path,public_url='https://wisteriasoftware.uk/sticker')
    app=create_app(settings,DemoStore(tmp_path/'state.json'),Providers(settings),False)
    with TestClient(app,base_url='https://api.wisteriasoftware.uk') as client:
        r=client.options('/sticker/api/checkout',headers={'Origin':'https://wisteriasoftware.uk','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'})
        assert r.status_code==200
        assert r.headers['access-control-allow-origin']=='https://wisteriasoftware.uk'
        assert r.headers['access-control-allow-credentials']=='true'
        assert client.post('/sticker/api/auth/logout',headers={'Origin':'https://evil.example'}).status_code==403


def test_live_image_auth_failure_returns_trial_and_keeps_safe_diagnostic(setup):
    from server.providers import ProviderError
    client,service,catalog=setup
    jid=create(client,catalog).json()['id']
    seen=[]
    def fail(prompt,photos):
        seen.extend(photos)
        raise ProviderError('private provider explanation','image_auth_failed')
    service.providers.generate=fail
    service.work_once()
    assert len(seen)==1 and seen[0]!=b''
    result=client.get('/sticker/api/generations/'+jid).json()
    assert result['state']=='FAILED'
    assert '配置异常' in result['error']
    assert 'private' not in result['error']
    assert client.get('/sticker/api/me').json()['trial_available']
    with service.store.transaction() as tx:assert tx.get('jobs',jid)['failure_code']=='image_auth_failed'


def test_email_account_usage_survives_new_device_and_failed_generation(setup):
    _,service,catalog=setup
    sid,user=signed_in(service,'credits@example.com')
    with service.store.transaction() as tx:
        service._grant(tx,'five-pack',user['id'],5,'order-five')
        grant=tx.get('grants','five-pack');grant.update(available=3,consumed=1);tx.put('grants','five-pack',grant)
    me=service.me(sid)
    assert (me['pack_total'],me['pack_used'],me['pack_pending'],me['pack_balance'])==(5,1,1,3)
    service.clock=lambda:__import__('time').time()+61
    other_sid,_=signed_in(service,'CREDITS@example.com')
    assert service.me(other_sid)['pack_balance']==3
    with service.store.transaction() as tx:
        grant=tx.get('grants','five-pack');grant['available']+=1;tx.put('grants','five-pack',grant)
    me=service.me(other_sid)
    assert (me['pack_used'],me['pack_pending'],me['pack_balance'])==(1,0,4)


def full_discount(data):
    data['discount_id']='dsc_full'
    data['details']['totals']={'subtotal':'1000','tax':'0','discount':'1000','total':'0',
        'grand_total':'0','balance':'0','currency_code':'USD'}
    return data


def test_full_discount_unlocks_original_job_and_queues_one_delivery(setup,monkeypatch):
    client,service,catalog=setup
    monkeypatch.setenv('PADDLE_PRODUCT_ID','pro_test')
    jid=create(client,catalog).json()['id'];service.work_once()
    client.post('/sticker/api/auth/code',json={'email':'coupon@example.com'})
    client.post('/sticker/api/auth/verify',json={'email':'coupon@example.com','code':'123456'})
    sid=service.digest(client.cookies.get('emjo_session'));user=service.current(sid)[1]
    data=full_discount(payment_order(service,user['id'],'coupon','FIRST_PACK_UNLOCK',jid))
    service.providers.paddle=lambda *args:data
    service.enqueue_payment({'event_id':'evt_coupon','event_type':'transaction.completed','data':{'id':data['id']}})
    assert service.payment_once()
    service.complete_payment('evt_duplicate_coupon',data)
    assert service.job(sid,jid)['unlocked']
    assert service.me(sid)['pack_balance']==0
    with service.store.transaction() as tx:
        assert tx.get('orders','coupon')['state']=='PAID'
        assert tx.get('orders','coupon')['amount']==0
        assert len(tx.all('mail'))==1
        assert len(tx.all('jobs'))==1
    service.mail_once()
    assert client.get('/sticker/api/orders/coupon').json()['delivery_state']=='SENT'


@pytest.mark.parametrize('change',[
    {'discount_id':None}, {'totals':{'discount':'999'}}, {'totals':{'balance':'1000'}},
    {'totals':{'total':'-1'}}, {'totals':{'total':'0.0'}}, {'totals':{'currency_code':'EUR'}},
    {'totals':{'subtotal':'0','discount':'0'}},
])
def test_unexplained_or_invalid_zero_totals_stay_locked(setup,monkeypatch,change):
    _,service,_=setup
    monkeypatch.setenv('PADDLE_PRODUCT_ID','pro_test')
    sid,user=signed_in(service,'invalid-zero@example.com')
    actual=full_discount(payment_order(service,user['id'],'invalid_zero'))
    if 'discount_id' in change:actual['discount_id']=change['discount_id']
    actual['details']['totals'].update(change.get('totals',{}))
    service.providers.paddle=lambda *args:actual
    service.enqueue_payment({'event_id':'evt_zero','event_type':'transaction.completed','data':{'id':actual['id']}})
    assert service.payment_once()
    assert service.me(sid)['pack_balance']==0
    assert service.account_history(sid)['orders'][0]['payment_state']=='REVIEW'
    with service.store.transaction() as tx:
        assert tx.get('orders','invalid_zero')['state']=='PENDING'
        assert tx.get('payment_notifications','evt_zero')['failure_code']=='invalid_amount'
        assert not tx.all('mail')


def test_live_generation_requires_email_and_same_account_cannot_repeat_trial(setup,monkeypatch):
    client,service,catalog=setup
    service.s.mode='live'
    response=create(client,catalog)
    assert response.status_code==401
    with service.store.transaction() as tx:assert not tx.all('jobs')
    # Log in using the demo OTP adapter, then exercise live admission without calling a provider.
    service.s.mode='demo'
    sid,user=signed_in(service,'one-trial@example.com')
    service.s.mode='live';monkeypatch.delenv('EMJO_DAILY_FREE_BUDGET_CNY',raising=False)
    args=(str(uuid.uuid4()),[(ROOT/'assets/cat-photo.png').read_bytes()],catalog['styles'][0]['id'])
    job=service.create_job(sid,*args)
    with service.store.transaction() as tx:
        j=tx.get('jobs',job['id']);j['state']='READY';tx.put('jobs',j['id'],j)
    now=service.clock();service.clock=lambda:now+61
    service.s.mode='demo';second_sid,_=signed_in(service,'ONE-TRIAL@example.com')
    service.s.mode='live'
    with pytest.raises(RuleError) as exc:service.create_job(second_sid,*args)
    assert exc.value.status==402
    with service.store.transaction() as tx:assert len(tx.all('jobs'))==1
