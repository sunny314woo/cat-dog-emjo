from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from decimal import Decimal
import hashlib
import hmac
import json
import os
import re
import secrets
import shutil
import time
import uuid
from .catalog import CATALOG, EXPRESSIONS, PRODUCTS, STYLES, build_prompt
from .imaging import prepare_pack, read_upload
from .providers import ProviderError

class RuleError(Exception):
    def __init__(self, message, status=400): super().__init__(message); self.status=status

class Service:
    def __init__(self, settings, store, providers, clock=time.time):
        self.s,self.store,self.providers,self.clock=settings,store,providers,clock
    def digest(self, value): return hmac.new(self.s.secret.encode(),value.encode(),hashlib.sha256).hexdigest()
    def session(self, token=None):
        if token and re.fullmatch(r'[a-f0-9]{64}',token):
            with self.store.transaction() as tx:
                old=tx.get('sessions',self.digest(token))
                if old: return token,old
        token=secrets.token_hex(32)
        row={'id':self.digest(token),'user_id':None,'trial_used':False,'created':self.clock()}
        with self.store.transaction() as tx: tx.put('sessions',row['id'],row)
        return token,row
    def current(self,sid):
        with self.store.transaction() as tx:
            session=tx.get('sessions',sid)
            if not session: raise RuleError('请刷新页面后重试',401)
            user=tx.get('users',session['user_id']) if session['user_id'] else None
            balance=sum(g['available'] for g in tx.all('grants') if user and g['user_id']==user['id'] and not g['revoked'])
            return session,user,balance
    def normalize_email(self,email):
        email=email.strip().casefold()
        if len(email)>254 or not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',email): raise RuleError('请输入有效邮箱')
        return email
    def request_code(self,sid,email):
        email=self.normalize_email(email); key=self.digest(email)
        now=self.clock(); code=self.s.demo_code if self.s.mode=='demo' else f'{secrets.randbelow(1000000):06d}'
        with self.store.transaction() as tx:
            for kind,value in [('email',key),('device',sid)]:
                rate=tx.get('rates',kind+value) or {'id':kind+value,'time':0,'count':0,'hour':now}
                if now-rate['time']<60: raise RuleError('稍等一分钟，再获取验证码',429)
                if now-rate['hour']>3600: rate.update(count=0,hour=now)
                if rate['count']>=10: raise RuleError('验证码请求较多，请稍后再试',429)
                rate.update(time=now,count=rate['count']+1); tx.put('rates',kind+value,rate)
            tx.put('codes',key,{'id':key,'email':email,'hash':self.digest(code+key),'expires':now+600,'tries':0,'used':False})
        self.providers.email(email,'你的 EMJO 登录验证码',f'<p>你的验证码是 <strong>{code}</strong>，10 分钟内有效。</p>',f'otp-{key[:12]}-{int(now)}')
        return {'demo_code':code if self.s.mode=='demo' else None}
    def verify_code(self,sid,email,code,referral=None):
        email=self.normalize_email(email); key=self.digest(email); error=None; now=self.clock()
        with self.store.transaction() as tx:
            row=tx.get('codes',key)
            if not row or row['used'] or row['expires']<now or row['tries']>=5:
                error=RuleError('验证码已失效，请重新获取')
            elif not hmac.compare_digest(row['hash'],self.digest(code+key)):
                row['tries']+=1; tx.put('codes',key,row); error=RuleError('验证码不正确')
            else:
                row['used']=True; tx.put('codes',key,row)
                session=tx.get('sessions',sid)
                user=tx.get('users',key)
                if not user:
                    ref=tx.get('referrals',referral) if referral else None
                    ref_id=ref['user_id'] if ref and ref['user_id']!=key else None
                    user={'id':key,'email':email,'trial_used':False,'paid_once':False,
                          'referrer':ref_id,'referral_code':secrets.token_urlsafe(9),'created':now}
                    tx.put('referrals',user['referral_code'],{'user_id':key})
                user['trial_used']=user['trial_used'] or session['trial_used']
                session['user_id']=key
                tx.put('users',key,user); tx.put('sessions',sid,session)
                for job in tx.all('jobs'):
                    if job['session_id']==sid and not job.get('user_id'):
                        job['user_id']=key;tx.put('jobs',job['id'],job)
        if error: raise error
        return self.me(sid)
    def me(self,sid):
        session,user,balance=self.current(sid)
        return {'email':user['email'] if user else None,'pack_balance':balance,
                'referral_code':user['referral_code'] if user else None,
                'trial_available':not(session['trial_used'] or user and(user['trial_used'] or user['paid_once'])),
                'demo':self.s.mode=='demo'}
    def _owned(self,tx,sid,jid):
        job=tx.get('jobs',jid); session=tx.get('sessions',sid)
        if not job or not session or not((not job.get('user_id') and job['session_id']==sid) or session['user_id'] and job.get('user_id')==session['user_id']):
            raise RuleError('没有找到这份作品',404)
        return job
    def _public_job(self,job):
        return {k:job.get(k) for k in ('id','state','style','created','expires','selected','unlocked','error','demo','calibration','captions','accessories')}
    def job(self,sid,jid):
        with self.store.transaction() as tx:
            job=self._owned(tx,sid,jid)
            data=self._public_job(job)
            if job.get('expires') and job['expires']<=self.clock(): data['state']='EXPIRED'
            data['cells']=EXPRESSIONS
            return data
    def create_job(self,sid,request_id,photos,style,captions=True,accessories=True,consent=False):
        if not re.fullmatch(r'[a-zA-Z0-9-]{16,64}',request_id): raise RuleError('生成请求标识无效')
        if not 1<=len(photos)<=3: raise RuleError('请上传 1–3 张同一主体的照片')
        if any(len(p)>self.s.upload_bytes for p in photos): raise RuleError('每张照片请小于 15MB',413)
        try:
            prompt=build_prompt(style,len(photos),accessories)
            normalized=[read_upload(p,self.s.upload_pixels,self.s.max_edge) for p in photos]
        except Exception as exc: raise RuleError(str(exc)) from exc
        fingerprint=hashlib.sha256(b''.join(normalized)+json.dumps([style,captions,accessories,consent]).encode()).hexdigest()
        request_key=self.digest(sid+request_id)
        jid=uuid.uuid4().hex; now=self.clock(); folder=self.s.data_dir/'jobs'/jid
        with self.store.transaction() as tx:
            existing=tx.get('requests',request_key)
            if existing:
                if existing['fingerprint']!=fingerprint: raise RuleError('该请求已用于另一份作品',409)
                return self._public_job(self._owned(tx,sid,existing['job_id']))
            session=tx.get('sessions',sid); user=tx.get('users',session['user_id']) if session['user_id'] else None
            if any(j['session_id']==sid and j['state'] in ('QUEUED','GENERATING','PROCESSING') for j in tx.all('jobs')):
                raise RuleError('上一份正在制作，先等待它完成吧',409)
            free=not(session['trial_used'] or user and(user['trial_used'] or user['paid_once']))
            grant=None
            day=datetime.fromtimestamp(now,ZoneInfo('Asia/Shanghai')).date().isoformat()
            attempt_key=sid+day
            attempt=tx.get('attempts',attempt_key) or {'count':0}
            if free and attempt['count']>=3:raise RuleError('今天已尝试三次，请明天再来',429)
            if free:
                attempt['count']+=1;tx.put('attempts',attempt_key,attempt)
            if not free:
                grants=[g for g in tx.all('grants') if user and g['user_id']==user['id'] and g['available']>0 and not g['revoked']]
                if not grants: raise RuleError('首次免费体验已用过，可以购买或通过邀请获得新的一套',402)
                grant=sorted(grants,key=lambda g:g['created'])[0]
                grant['available']-=1;tx.put('grants',grant['id'],grant)
            if free and self.s.mode=='live' and os.getenv('EMJO_DAILY_FREE_BUDGET_CNY'):
                if not os.getenv('EMJO_COST_PER_GENERATION_CNY'):
                    raise RuleError('免费制作暂未开放，欢迎稍后回来',503)
                cost=Decimal(os.environ['EMJO_COST_PER_GENERATION_CNY'])
                day=datetime.fromtimestamp(now,ZoneInfo('Asia/Shanghai')).date().isoformat()
                budget=tx.get('budgets',day) or {'id':day,'used':'0'}
                total=Decimal(budget['used'])+cost
                if total>Decimal(os.environ['EMJO_DAILY_FREE_BUDGET_CNY']): raise RuleError('今天的小画室暂时满员，已有作品仍可领取',429)
                budget['used']=str(total);tx.put('budgets',day,budget)
            if free:
                session['trial_used']=True;tx.put('sessions',sid,session)
                if user:user['trial_used']=True;tx.put('users',user['id'],user)
            folder.mkdir(parents=True,exist_ok=True)
            for index,photo in enumerate(normalized): (folder/f'input-{index+1}.jpg').write_bytes(photo)
            job={'id':jid,'session_id':sid,'user_id':user['id'] if user else None,'style':style,
                 'captions':captions,'accessories':accessories,'consent':bool(consent and self.s.calibration_enabled),
                 'consent_version':'calibration-v1-100-30d' if consent and self.s.calibration_enabled else None,
                 'created':now,'state':'QUEUED','photo_count':len(normalized),'prompt':prompt,'prompt_version':'v0.6-adapter',
                 'grant_id':grant['id'] if grant else None,'free':free,'selected':[],
                 'unlocked':not free,'expires':None,'demo':self.s.mode=='demo','calibration':False,'error':None}
            tx.put('jobs',jid,job);tx.put('requests',request_key,{'fingerprint':fingerprint,'job_id':jid})
        return self._public_job(job)
    def claim(self,sid,jid,cells):
        if len(cells)!=2 or len(set(cells))!=2 or any(type(i)!=int or not 1<=i<=9 for i in cells):
            raise RuleError('请选择不同的两张贴纸')
        with self.store.transaction() as tx:
            job=self._owned(tx,sid,jid)
            self._ready(job)
            if not job.get('free'):raise RuleError('免费两张仅适用于首次体验作品',403)
            if job['selected'] and sorted(job['selected'])!=sorted(cells): raise RuleError('两张已经锁定，可以继续下载它们',409)
            job['selected']=sorted(cells);tx.put('jobs',jid,job)
            return self._public_job(job)
    def _ready(self,job):
        if job['state']!='READY': raise RuleError('作品还没有准备好',409)
        if job['expires']<=self.clock(): raise RuleError('作品已过期，请使用之前保存的副本',410)
    def authorize_file(self,sid,jid,name,token=None):
        match=re.fullmatch(r'(preview-[1-9]\.jpg|sticker-[1-9](?:-256\.png|\.png|\.webp)|grid\.png|stickers\.zip)',name)
        if not match: raise RuleError('文件不存在',404)
        with self.store.transaction() as tx:
            job=tx.get('jobs',jid)
            if not job: raise RuleError('文件不存在',404)
            signed=False
            if token:
                try:
                    stamp,signature=token.split('.')
                    signed=int(stamp)>=self.clock() and hmac.compare_digest(signature,self.digest(jid+name+stamp))
                except (ValueError,TypeError): pass
            if not signed:self._owned(tx,sid,jid)
            self._ready(job)
            if name.startswith('preview-') and not signed: pass
            elif not job['unlocked']:
                cell=int(name[8]) if name.startswith('sticker-') else None
                if cell not in job['selected']: raise RuleError('这张还未解锁',403)
            folder=self.s.data_dir/'jobs'/jid
            path=folder/name
            if not path.is_file(): raise RuleError('文件已清理',410)
            return path
    def share_link(self,sid,jid,cell,variant):
        if type(cell)!=int or cell not in range(1,10):raise RuleError('贴纸不存在',404)
        suffix={'png512':'.png','png256':'-256.png','webp512':'.webp'}.get(variant)
        if not suffix:raise RuleError('分享格式无效')
        name=f'sticker-{cell}{suffix}'
        self.authorize_file(sid,jid,name)
        with self.store.transaction() as tx:
            job=self._owned(tx,sid,jid);expires=min(job['expires'],self.clock()+86400)
        token=self.file_token(jid,name,expires)
        return {'url':(self.s.asset_url or self.s.public_url).rstrip('/')+'/api/files/'+jid+'/'+name+'?token='+token,
                'expires':expires,'name':name,'local_only':self.s.mode=='demo'}

    def file_token(self,jid,name,expires):
        stamp=str(int(expires));return stamp+'.'+self.digest(jid+name+stamp)
    def _grant(self,tx,gid,uid,quantity,source):
        if tx.get('grants',gid):return
        tx.put('grants',gid,{'id':gid,'user_id':uid,'available':quantity,'quantity':quantity,'consumed':0,
                            'revoked':False,'source':source,'created':self.clock()})
    def checkout(self,sid,product,jid=None):
        if product not in PRODUCTS:raise RuleError('商品不存在',404)
        session,user,_=self.current(sid)
        if not user:raise RuleError('请先验证邮箱',401)
        if self.s.mode=='demo': raise RuleError('当前是示例体验，不会收款；真实支付待配置',503)
        price=os.getenv('PADDLE_PRICE_'+product+'_ID','')
        if not price or not os.getenv('PADDLE_PRODUCT_ID') or not os.getenv('PADDLE_WEBHOOK_SECRET'):raise RuleError('支付通知配置尚未完成，暂不能付款',503)
        now=self.clock(); oid=uuid.uuid4().hex
        with self.store.transaction() as tx:
            if product=='FIRST_PACK_UNLOCK':
                job=self._owned(tx,sid,jid);self._ready(job)
                if job['unlocked']:raise RuleError('这一套已经解锁',409)
                if user['paid_once']:raise RuleError('首次优惠已使用',409)
                # Keep the existing asset alive during checkout, without reviving expired files.
                job['expires']=max(job['expires'],now+3600);tx.put('jobs',jid,job)
            existing=[o for o in tx.all('orders') if o['user_id']==user['id'] and o['state']=='PENDING']
            same=next((o for o in existing if o['product']==product and o['job_id']==jid and o.get('checkout_mode')=='paddlejs'),None)
            if same:
                oid=same['id']
            else:
                if existing:raise RuleError('已有一笔待完成订单，请先完成或稍后重试',409)
                order={'id':oid,'user_id':user['id'],'job_id':jid,'product':product,'price_id':price,
                       'state':'PENDING','transaction_id':None,'created':now,'checkout_mode':'paddlejs'}
                tx.put('orders',oid,order)
        # Paddle.js creates the transaction. Only signed, API-verified completion grants delivery.
        return {'order_id':oid,'items':[{'priceId':price,'quantity':1}],
                'customData':{'emjo_order_id':oid},'customer':{'email':user['email']}}
    def complete_payment(self,event_id,data):
        """Call only with a signed webhook and freshly fetched Paddle transaction."""
        oid=(data.get('custom_data') or {}).get('emjo_order_id')
        if not oid:return
        with self.store.transaction() as tx:
            if tx.get('events',event_id):return
            order=tx.get('orders',oid)
            if not order:return
            if order['state'] in ('PAID','REFUNDED','REFUND_REQUIRED'):
                tx.put('events',event_id,{'id':event_id});return
            items=data.get('items',[])
            if data.get('status')!='completed' or len(items)!=1 or items[0].get('quantity')!=1:
                raise RuleError('交易内容不匹配',409)
            price=items[0].get('price',{})
            if price.get('id')!=order['price_id'] or price.get('product_id')!=os.getenv('PADDLE_PRODUCT_ID'):
                raise RuleError('支付商品不匹配',409)
            if order['transaction_id'] and order['transaction_id']!=data['id']: raise RuleError('支付交易不匹配',409)
            total=int(data['details']['totals']['total'])
            if total<=0 or not re.fullmatch('[A-Z]{3}',data.get('currency_code','')):raise RuleError('交易金额无效',409)
            order.update(transaction_id=data['id'],state='PAID',amount=total,currency=data['currency_code'],paid_at=self.clock())
            user=tx.get('users',order['user_id'])
            if order['product']=='FIRST_PACK_UNLOCK':
                job=tx.get('jobs',order['job_id'])
                if not job or job['state']!='READY' or job['expires']<=self.clock() or job['unlocked'] or user['paid_once']:
                    order['state']='REFUND_REQUIRED'
                else:
                    job.update(unlocked=True,user_id=user['id'],expires=self.clock()+self.s.paid_ttl_hours*3600)
                    tx.put('jobs',job['id'],job);self._queue_delivery(tx,job)
            else:self._grant(tx,'order-'+oid,user['id'],PRODUCTS[order['product']]['packs'],oid)
            if order['state']=='PAID':
                if not user['paid_once'] and user.get('referrer'):
                    self._grant(tx,'referral-'+user['id'],user['referrer'],1,oid)
                user['paid_once']=True;tx.put('users',user['id'],user)
            tx.put('orders',oid,order);tx.put('events',event_id,{'id':event_id})
    def refund(self,event_id,transaction_id):
        with self.store.transaction() as tx:
            if tx.get('events',event_id):return
            for order in tx.all('orders'):
                if order['transaction_id']!=transaction_id:continue
                order['state']='REFUNDED';tx.put('orders',order['id'],order)
                for grant in tx.all('grants'):
                    if grant['source']==order['id']:
                        grant.update(revoked=True,available=0);tx.put('grants',grant['id'],grant)
                if order.get('job_id'):
                    job=tx.get('jobs',order['job_id'])
                    if job:job['unlocked']=False;tx.put('jobs',job['id'],job)
                for job in tx.all('jobs'):
                    if job.get('grant_id')=='order-'+order['id']:
                        job['unlocked']=False;tx.put('jobs',job['id'],job)
            tx.put('events',event_id,{'id':event_id})
    def _queue_delivery(self,tx,job):
        if job.get('user_id'):
            mid='delivery-'+job['id']
            if not tx.get('mail',mid):tx.put('mail',mid,{'id':mid,'job_id':job['id'],'state':'PENDING','attempts':0,'next':self.clock()})
    def work_once(self):
        now=self.clock(); job=None
        with self.store.transaction() as tx:
            candidates=sorted([j for j in tx.all('jobs') if j['state']=='QUEUED'],key=lambda j:j['created'])
            if candidates:
                job=candidates[0];job.update(state='GENERATING',lease_until=now+360);tx.put('jobs',job['id'],job)
        if not job:return False
        folder=self.s.data_dir/'jobs'/job['id']
        try:
            raw=folder/'provider-output.png'
            if raw.exists():output=raw.read_bytes()
            else:
                photos=[(folder/f'input-{i+1}.jpg').read_bytes() for i in range(job['photo_count'])]
                output=self.providers.generate(job['prompt'],photos)
                temporary=folder/'provider-output.tmp';temporary.write_bytes(output);temporary.replace(raw)
            with self.store.transaction() as tx:
                current=tx.get('jobs',job['id']);current['state']='PROCESSING';tx.put('jobs',job['id'],current)
            prepare_pack(output,folder,job['captions'],os.getenv('EMJO_BACKGROUND_REMOVAL_MODE','alpha_only'),strict_boundaries=self.s.mode!='demo')
            with self.store.transaction() as tx:
                current=tx.get('jobs',job['id'])
                if job['grant_id']:
                    grant=tx.get('grants',job['grant_id'])
                    if grant['revoked']:raise RuleError('该生成权益已退款')
                    grant['consumed']+=1;tx.put('grants',grant['id'],grant)
                current.update(state='READY',expires=self.clock()+3600*(self.s.paid_ttl_hours if job['unlocked'] else self.s.ttl_hours))
                if current['consent'] and self.s.calibration_enabled:
                    counter=tx.get('settings','calibration') or {'count':0}
                    if counter['count']<self.s.calibration_limit:
                        counter['count']+=1;tx.put('settings','calibration',counter)
                        current['calibration']=True
                        tx.put('calibration',job['id'],{'id':job['id'],'expires':self.clock()+self.s.calibration_days*86400,
                            'consent_version':job['consent_version'],'state':'COPY_PENDING'})
                tx.put('jobs',job['id'],current)
                if current['unlocked']:self._queue_delivery(tx,current)
            if current['calibration']:
                destination=self.s.data_dir/'calibration'/job['id']
                shutil.copytree(folder,destination,dirs_exist_ok=True)
                (destination/'metadata.json').write_text(json.dumps({'prompt':job['prompt'],'style':job['style'],
                    'version':job['prompt_version'],'consent_version':job['consent_version']},ensure_ascii=False))
                with self.store.transaction() as tx:
                    case=tx.get('calibration',job['id'])
                    latest=tx.get('jobs',job['id'])
                    if case and latest['consent'] and case['expires']>self.clock():
                        case['state']='READY';tx.put('calibration',job['id'],case)
                    else:shutil.rmtree(destination,ignore_errors=True)
        except Exception as exc:
            with self.store.transaction() as tx:
                current=tx.get('jobs',job['id'])
                # An optional calibration copy error must not undo an otherwise READY delivery.
                if current['state']!='READY':
                    code=exc.code if isinstance(exc,ProviderError) else 'image_processing_failed'
                    message='图片服务配置异常，生成机会已退回。请等待站点修复后再试。' if code in ('image_auth_failed','image_permission_failed') else '这次没能制作完成，生成机会已退回。请稍后再试。'
                    current.update(state='FAILED',error=message,failure_code=code,expires=self.clock()+86400)
                    import logging
                    logging.getLogger('emjo').warning('Generation failed: job=%s code=%s',job['id'],code)
                    tx.put('jobs',job['id'],current)
                    if job['grant_id']:
                        grant=tx.get('grants',job['grant_id'])
                        if not grant['revoked']:grant['available']+=1;tx.put('grants',grant['id'],grant)
                    elif job['free']:
                        session=tx.get('sessions',job['session_id']);session['trial_used']=False;tx.put('sessions',session['id'],session)
                        if current['user_id']:
                            user=tx.get('users',current['user_id']);user['trial_used']=False;tx.put('users',user['id'],user)
        finally:
            for path in folder.glob('input-*.jpg'):path.unlink(missing_ok=True)
        return True
    def maintenance(self):
        now=self.clock(); to_delete=[]
        with self.store.transaction() as tx:
            for job in tx.all('jobs'):
                if job.get('expires') and job['expires']<=now and job['state'] not in ('GENERATING','PROCESSING'):
                    job['state']='EXPIRED';job.pop('prompt',None);tx.put('jobs',job['id'],job)
                    to_delete.append(self.s.data_dir/'jobs'/job['id'])
                # Uncertain upstream outcomes are surfaced for recovery, never blindly reissued.
                if job['state'] in ('GENERATING','PROCESSING') and job.get('lease_until',0)<now:
                    if (self.s.data_dir/'jobs'/job['id']/'provider-output.png').exists():
                        job.update(state='QUEUED',error=None)
                    else:
                        job.update(state='FAILED',error='制作中断，机会已退回。请重新尝试。',expires=now+86400)
                        if job.get('grant_id'):
                            grant=tx.get('grants',job['grant_id'])
                            if grant and not grant['revoked']:
                                grant['available']+=1;tx.put('grants',grant['id'],grant)
                        else:
                            session=tx.get('sessions',job['session_id']);session['trial_used']=False;tx.put('sessions',session['id'],session)
                            if job.get('user_id'):
                                user=tx.get('users',job['user_id']);user['trial_used']=False;tx.put('users',user['id'],user)
                        to_delete.append(self.s.data_dir/'jobs'/job['id'])
                    tx.put('jobs',job['id'],job)
            for case in tx.all('calibration'):
                if case['expires']<=now:
                    to_delete.append(self.s.data_dir/'calibration'/case['id']);tx.delete('calibration',case['id'])
            for mail in tx.all('mail'):
                if mail['state']=='SENDING' and mail.get('lease_until',0)<now:
                    mail.update(state='FAILED',next=now);tx.put('mail',mail['id'],mail)
            for code in tx.all('codes'):
                if code['expires']+86400<=now:tx.delete('codes',code['id'])
        for folder in to_delete:shutil.rmtree(folder,ignore_errors=True)
    def mail_once(self):
        now=self.clock(); mail=None
        with self.store.transaction() as tx:
            candidates=[m for m in tx.all('mail') if m['state'] in ('PENDING','FAILED') and m['attempts']<4 and m['next']<=now]
            if candidates:
                mail=candidates[0];mail.update(state='SENDING',attempts=mail['attempts']+1,lease_until=now+120);tx.put('mail',mail['id'],mail)
                job=tx.get('jobs',mail['job_id']);user=tx.get('users',job['user_id'])
        if not mail:return
        try:
            if not job['unlocked'] or job['expires']<=now:raise RuleError('交付已失效')
            path=self.s.data_dir/'jobs'/job['id']/'stickers.zip'
            token=self.file_token(job['id'],'stickers.zip',job['expires'])
            link=(self.s.asset_url or self.s.public_url).rstrip('/')+'/api/files/'+job['id']+'/stickers.zip?token='+token
            content=path.read_bytes();attachment=content if len(content)<=10*1024*1024 else None
            self.providers.email(user['email'],'你的九种小心情，准备好啦',
                f'<p>你的九张贴纸已经准备好。请保存附件或在有效期内下载。</p><p><a href="{link}">下载完整贴纸包</a></p><p>链接仅在本次24小时交付窗口内有效。</p>',mail['id'],attachment)
            state='SENT'
        except Exception:state='FAILED'
        with self.store.transaction() as tx:
            mail.update(state=state,next=self.clock()+300*mail['attempts']);tx.put('mail',mail['id'],mail)
