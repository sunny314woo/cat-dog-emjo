"""Each payment/credit spends at most once and remains tied to its selected work."""
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from server.main import create_app
from server.providers import Providers
from server.service import RuleError
from server.settings import Settings
from server.store import DemoStore


@pytest.fixture
def account(tmp_path,monkeypatch):
    settings=Settings(data_dir=tmp_path,debug_retain_assets=True)
    app=create_app(settings,DemoStore(),Providers(settings),False)
    with TestClient(app) as client:
        catalog=client.get('/sticker/api/catalog').json()
        assert catalog['order_workflow']=='work_bound_packs_v1'
        client.post('/sticker/api/auth/code',json={'email':'works@example.com'})
        client.post('/sticker/api/auth/verify',json={'email':'works@example.com','code':'123456'})
        service=app.state.service
        sid=service.digest(client.cookies.get('emjo_session'))
        uid=service.current(sid)[1]['id']
        for key,value in {'PADDLE_PRODUCT_ID':'pro_test','PADDLE_WEBHOOK_SECRET':'test-hook',
                          'PADDLE_API_KEY':'test-key','PADDLE_PRICE_PACK_1_ID':'pri_one',
                          'PADDLE_PRICE_PACK_3_ID':'pri_three','PADDLE_PRICE_PACK_5_ID':'pri_five',
                          'PADDLE_PRICE_FIRST_PACK_UNLOCK_ID':'pri_first'}.items():
            monkeypatch.setenv(key,value)
        yield service,client,sid,uid


def ready(service,sid,uid,jid,free=False):
    folder=service.s.data_dir/'jobs'/jid
    folder.mkdir(parents=True)
    (folder/'stickers.zip').write_bytes(b'the-exact-original-nine')
    with service.store.transaction() as tx:
        tx.put('jobs',jid,{'id':jid,'session_id':sid,'user_id':uid,'state':'READY',
                          'free':free,'unlocked':False,'selected':[],'grant_id':None,
                          'created':service.clock(),'expires':service.clock()+86400})


def pay(service,sid,product='PACK_3',jid=None,event='paid'):
    service.s.mode='live'
    checkout=service.checkout(sid,product,jid)
    data={'id':'txn_'+checkout['order_id'],'status':'completed','custom_data':checkout['customData'],
          'items':[{'quantity':1,'price':{'id':checkout['items'][0]['priceId'],'product_id':'pro_test'}}],
          'details':{'totals':{'total':'1999'}},'currency_code':'USD'}
    service.complete_payment(event,data)
    return checkout['order_id'],data


def test_existing_ready_work_uses_one_credit_and_queues_its_zip(account):
    service,client,sid,uid=account
    ready(service,sid,uid,'existing')
    oid,_=pay(service,sid)
    original=(service.s.data_dir/'jobs/existing/stickers.zip').read_bytes()
    response=client.post('/sticker/api/generations/existing/unlock')
    assert response.status_code==200,response.text
    assert response.json()['unlocked']
    assert service.me(sid)['pack_balance']==2
    assert service.me(sid)['pack_used']==1
    assert (service.s.data_dir/'jobs/existing/stickers.zip').read_bytes()==original
    # A legacy credit-only purchase acquires the actual work relation after a credit is used.
    history=service.account_history(sid)
    assert history['orders'][0]['generation_id'] is None
    assert history['orders'][0]['generation_ids']==['existing']
    assert history['orders'][0]['entitlement']=={'quantity':3,'used':1,'remaining':2,'pending':0,'revoked':False}
    assert history['orders'][0]['deliveries']==[{'generation_id':'existing','state':'PENDING','attempts':0}]
    assert history['orders'][0]['delivery_state']=='PENDING'
    assert history['jobs'][0]['related_order_ids']==[oid]
    assert history['jobs'][0]['grant_source_order_id']==oid
    assert len(service.store.data['mail'])==1


def test_balance_unlock_concurrency_is_idempotent(account):
    service,_,sid,uid=account
    ready(service,sid,uid,'existing')
    pay(service,sid)
    with ThreadPoolExecutor(max_workers=6) as workers:
        results=list(workers.map(lambda _:service.unlock(sid,'existing'),range(12)))
    assert all(result['unlocked'] for result in results)
    assert service.me(sid)['pack_balance']==2
    assert service.me(sid)['pack_used']==1
    assert len(service.store.data['mail'])==1


@pytest.mark.parametrize('product,quantity',[('PACK_1',1),('PACK_3',3),('PACK_5',5)])
def test_bound_purchase_unlocks_exact_work_and_preserves_other_credits(account,product,quantity):
    service,_,sid,uid=account
    ready(service,sid,uid,'selected')
    ready(service,sid,uid,'another')
    oid,data=pay(service,sid,product,'selected')
    service.complete_payment('duplicate-event',data)
    assert service.job(sid,'selected')['unlocked']
    assert not service.job(sid,'another')['unlocked']
    assert service.me(sid)['pack_balance']==quantity-1
    assert service.me(sid)['pack_used']==1
    order=next(o for o in service.account_history(sid)['orders'] if o['id']==oid)
    assert order['fulfillment']=='WORK_UNLOCKED' and order['packs_used_for_work']==1
    assert order['generation_ids']==['selected']
    assert len(service.store.data['mail'])==1


def test_two_paid_packages_bound_to_same_work_spend_only_one_credit(account):
    service,_,sid,uid=account
    ready(service,sid,uid,'selected')
    one,_=pay(service,sid,'PACK_1','selected')
    three,_=pay(service,sid,'PACK_3','selected','second-paid')
    assert service.me(sid)['pack_balance']==3
    assert service.me(sid)['pack_used']==1
    with service.store.transaction() as tx:
        assert tx.get('orders',three)['fulfillment']=='ALREADY_UNLOCKED'
        assert tx.get('orders',three)['packs_used_for_work']==0
    # Refunding the unused top-up must leave the original work unlocked.
    service.refund('refund-topup','txn_'+three)
    assert service.job(sid,'selected')['unlocked']
    assert service.me(sid)['pack_balance']==0
    service.refund('refund-original','txn_'+one)
    assert not service.job(sid,'selected')['unlocked']


def test_refund_of_old_unlock_does_not_revoke_replacement_entitlement(account):
    service,_,sid,uid=account
    ready(service,sid,uid,'selected',True)
    first,_=pay(service,sid,'FIRST_PACK_UNLOCK','selected')
    service.refund('first-refund','txn_'+first)
    replacement,_=pay(service,sid,'PACK_1','selected','replacement-paid')
    service.refund('first-refund-again','txn_'+first)
    assert service.job(sid,'selected')['unlocked']
    service.refund('replacement-refund','txn_'+replacement)
    assert not service.job(sid,'selected')['unlocked']


def test_bound_checkout_rejects_foreign_missing_and_unready_work(account):
    service,_,sid,uid=account
    service.s.mode='live'
    ready(service,sid,'another-user','foreign')
    with pytest.raises(RuleError,match='没有找到'):service.checkout(sid,'PACK_3','foreign')
    with pytest.raises(RuleError,match='没有找到'):service.checkout(sid,'PACK_3','missing')
    ready(service,sid,uid,'unready')
    with service.store.transaction() as tx:
        job=tx.get('jobs','unready');job['state']='GENERATING';tx.put('jobs','unready',job)
    with pytest.raises(RuleError,match='没有准备好'):service.checkout(sid,'PACK_3','unready')
    assert not service.store.data.get('orders')


def test_missing_zip_or_zero_balance_never_spends(account):
    service,_,sid,uid=account
    ready(service,sid,uid,'selected')
    with pytest.raises(RuleError) as missing_balance:service.unlock(sid,'selected')
    assert missing_balance.value.status==402
    pay(service,sid)
    (service.s.data_dir/'jobs/selected/stickers.zip').unlink()
    with pytest.raises(RuleError,match='不可交付'):service.unlock(sid,'selected')
    assert service.me(sid)['pack_balance']==3


def test_first_discount_does_not_block_regular_work_purchase(account):
    service,_,sid,uid=account
    ready(service,sid,uid,'first',True)
    ready(service,sid,uid,'second')
    pay(service,sid,'FIRST_PACK_UNLOCK','first')
    options=service.job(sid,'second')['unlock_options']
    assert not options['first_offer_available'] and options['can_purchase_pack']
    pay(service,sid,'PACK_1','second','normal-paid')
    assert all(service.job(sid,jid)['unlocked'] for jid in ('first','second'))


def test_second_transaction_for_same_order_is_reviewed_without_duplicate_grants(account):
    service,_,sid,_=account
    oid,data=pay(service,sid)
    data=dict(data,id='txn_accidental_second_charge')
    service.complete_payment('second-charge',data)
    assert service.me(sid)['pack_balance']==3
    order=next(o for o in service.account_history(sid)['orders'] if o['id']==oid)
    assert order['payment_review_required']
    assert order['payment_issues']==['duplicate_order_transaction']
    with service.store.transaction() as tx:
        assert tx.get('review','second-charge')['reason']=='duplicate_order_transaction'
        assert tx.get('review','second-charge')['order_id']==oid


def test_bound_work_unavailable_on_completion_requires_review(account):
    service,_,sid,uid=account
    ready(service,sid,uid,'selected')
    service.s.mode='live'
    checkout=service.checkout(sid,'PACK_3','selected')
    (service.s.data_dir/'jobs/selected/stickers.zip').unlink()
    data={'id':'txn_missing_asset','status':'completed','custom_data':checkout['customData'],
          'items':[{'quantity':1,'price':{'id':'pri_three','product_id':'pro_test'}}],
          'details':{'totals':{'total':'1999'}},'currency_code':'USD'}
    service.complete_payment('paid-after-asset-loss',data)
    with service.store.transaction() as tx:
        assert tx.get('orders',checkout['order_id'])['state']=='REFUND_REQUIRED'
    assert service.me(sid)['pack_balance']==0
    assert not service.job(sid,'selected')['unlocked']


def test_refund_arriving_before_bound_completion_never_unlocks(account):
    service,_,sid,uid=account
    ready(service,sid,uid,'selected')
    service.s.mode='live'
    checkout=service.checkout(sid,'PACK_3','selected')
    txn='txn_'+checkout['order_id']
    service.refund('early-refund',txn)
    data={'id':txn,'status':'completed','custom_data':checkout['customData'],
          'items':[{'quantity':1,'price':{'id':'pri_three','product_id':'pro_test'}}],
          'details':{'totals':{'total':'1999'}},'currency_code':'USD'}
    service.complete_payment('late-completion',data)
    assert not service.job(sid,'selected')['unlocked']
    assert service.me(sid)['pack_balance']==0
    assert not service.store.data.get('mail')


def test_last_credit_cannot_unlock_two_different_works(account):
    service,_,sid,uid=account
    for jid in ('one','two'):ready(service,sid,uid,jid)
    pay(service,sid,'PACK_1')
    def unlock(jid):
        try:return service.unlock(sid,jid)['unlocked']
        except RuleError as exc:
            assert exc.status==402
            return False
    with ThreadPoolExecutor(max_workers=2) as workers:
        results=list(workers.map(unlock,('one','two')))
    assert sorted(results)==[False,True]
    assert service.me(sid)['pack_balance']==0
    assert service.me(sid)['pack_used']==1


def test_reunlock_preserves_old_order_relation_and_uses_new_email_key(account):
    service,_,sid,uid=account
    ready(service,sid,uid,'selected')
    old,_=pay(service,sid,'PACK_1')
    service.unlock(sid,'selected')
    sent=[]
    service.providers.email=lambda *args:sent.append(args) or 'mail-'+str(len(sent))
    service.mail_once()
    service.refund('refund-old','txn_'+old)
    new,_=pay(service,sid,'PACK_1',event='new-payment')
    service.unlock(sid,'selected')
    service.mail_once();service.mail_once()
    assert len(sent)==2 and sent[0][-2]!=sent[1][-2]
    history=service.account_history(sid)
    assert set(history['jobs'][0]['related_order_ids'])=={old,new}
    assert all(o['generation_ids']==['selected'] for o in history['orders'])
