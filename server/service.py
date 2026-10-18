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
import zipfile
from .catalog import CATALOG, EXPRESSIONS, PRODUCTS, STYLES, PACK_PROMPT_VERSION, build_prompt, build_style_prompt
from .imaging import prepare_pack, prepare_styles, read_upload, save_wechat_gif
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
                account_used_trial=bool(user.get('trial_used') or user.get('paid_once'))
                user['trial_used']=user['trial_used'] or session['trial_used']
                session['user_id']=key
                tx.put('users',key,user); tx.put('sessions',sid,session)
                for job in tx.all('jobs'):
                    if job['session_id']==sid and not job.get('user_id'):
                        job['user_id']=key
                        if account_used_trial and job.get('free') and job['state'] in (
                            'READY','QUEUED','GENERATING','PROCESSING',
                            'PREVIEW_QUEUED','PREVIEW_GENERATING','STYLE_READY'):
                            job['free']=False
                            grants=sorted([g for g in tx.all('grants') if g['user_id']==key and
                                           g['available']>0 and not g['revoked']],key=lambda g:g['created'])
                            if grants:
                                grant=grants[0];grant['available']-=1
                                if job['state']=='READY':
                                    grant['consumed']+=1
                                    job['expires']=max(job.get('expires') or 0,now+self.s.paid_ttl_hours*3600)
                                tx.put('grants',grant['id'],grant);job.update(grant_id=grant['id'],unlocked=True)
                                if job['state']=='READY':self._queue_delivery(tx,job)
                        tx.put('jobs',job['id'],job)
        if error: raise error
        return self.me(sid)
    def me(self,sid):
        session,user,balance=self.current(sid)
        with self.store.transaction() as tx:
            grants=[g for g in tx.all('grants') if user and g['user_id']==user['id'] and not g['revoked']]
        balance=sum(g['available'] for g in grants)
        total=sum(g['quantity'] for g in grants)
        used=sum(g['consumed'] for g in grants)
        return {'pack_total':total,'pack_used':used,'pack_pending':max(0,total-used-balance),'email':user['email'] if user else None,'pack_balance':balance,
                'referral_code':user['referral_code'] if user else None,
                'trial_available':not(session['trial_used'] or user and(user['trial_used'] or user['paid_once'])),
                'demo':self.s.mode=='demo'}
    def _owned(self,tx,sid,jid):
        job=tx.get('jobs',jid); session=tx.get('sessions',sid)
        if not job or not session or not((not job.get('user_id') and job['session_id']==sid) or session['user_id'] and job.get('user_id')==session['user_id']):
            raise RuleError('没有找到这份作品',404)
        return job
    def _public_job(self,job):
        data={k:job.get(k) for k in ('id','state','style','created','expires','selected','unlocked','free','error','demo','calibration','captions','accessories','workflow','preview_styles')}
        data['debug_retained']=self.s.debug_retain_assets
        if self.s.debug_retain_assets and job['state']=='READY':data['expires']=None
        return data
    def _expired(self,job):
        return bool(job.get('expires') and job['expires']<=self.clock() and not(self.s.debug_retain_assets and job['state']=='READY'))
    def job(self,sid,jid):
        with self.store.transaction() as tx:
            job=self._owned(tx,sid,jid)
            data=self._public_job(job)
            if self._expired(job): data['state']='EXPIRED'
            data['cells']=EXPRESSIONS
            return data
    def create_job(self,sid,request_id,photos,style,captions=True,accessories=True,consent=False,preview=False):
        if self.s.mode=='live' and not self.current(sid)[1]:
            raise RuleError('请先验证邮箱，再开始制作；每个邮箱账户限一次免费体验',401)
        if not re.fullmatch(r'[a-zA-Z0-9-]{16,64}',request_id): raise RuleError('生成请求标识无效')
        if not 1<=len(photos)<=3: raise RuleError('请上传 1–3 张同一主体的照片')
        if any(len(p)>self.s.upload_bytes for p in photos): raise RuleError('每张照片请小于 15MB',413)
        try:
            style_ids=[s['id'] for s in CATALOG['styles'] if s['active']]
            prompt=build_style_prompt(style_ids,len(photos)) if preview else build_prompt(style,len(photos),accessories)
            normalized=[read_upload(p,self.s.upload_pixels,self.s.max_edge) for p in photos]
        except Exception as exc: raise RuleError(str(exc)) from exc
        fingerprint=hashlib.sha256(b''.join(normalized)+json.dumps([style,captions,accessories,consent,preview]).encode()).hexdigest()
        request_key=self.digest(sid+request_id)
        jid=uuid.uuid4().hex; now=self.clock(); folder=self.s.data_dir/'jobs'/jid
        with self.store.transaction() as tx:
            existing=tx.get('requests',request_key)
            if existing:
                if existing['fingerprint']!=fingerprint: raise RuleError('该请求已用于另一份作品',409)
                return self._public_job(self._owned(tx,sid,existing['job_id']))
            session=tx.get('sessions',sid); user=tx.get('users',session['user_id']) if session['user_id'] else None
            if self.s.mode=='live' and not user:raise RuleError('请先验证邮箱，再开始制作',401)
            if any((j['session_id']==sid or user and j.get('user_id')==user['id']) and j['state'] in ('QUEUED','GENERATING','PROCESSING','PREVIEW_QUEUED','PREVIEW_GENERATING','STYLE_READY') for j in tx.all('jobs')):
                raise RuleError('上一份正在制作，先等待它完成吧',409)
            free=not(session['trial_used'] or user and(user['trial_used'] or user['paid_once']))
            grant=None
            day=datetime.fromtimestamp(now,ZoneInfo('Asia/Shanghai')).date().isoformat()
            attempt_key=(user['id'] if user else sid)+day
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
                 'created':now,'state':'PREVIEW_QUEUED' if preview else 'QUEUED','photo_count':len(normalized),'prompt':prompt,'prompt_version':'v0.7-two-stage' if preview else PACK_PROMPT_VERSION,
                 'model_id':os.getenv('VOLCENGINE_MODEL_ID'),'image_size':os.getenv('VOLCENGINE_FINAL_SIZE'),
                 'grant_id':grant['id'] if grant else None,'free':free,'selected':[],
                 'unlocked':not free,'expires':now+86400 if preview else None,'demo':self.s.mode=='demo','calibration':False,'error':None}
            if preview:
                job.update(workflow='personalized_styles_v1',style=None,
                           final_prompt_version=PACK_PROMPT_VERSION,
                           preview_styles=[{'id':s,'name':STYLES[s]['name'],'index':i+1} for i,s in enumerate(style_ids)],
                           final_prompts={s:build_prompt(s,len(photos),accessories,style_reference=True) for s in style_ids})
            tx.put('jobs',jid,job);tx.put('requests',request_key,{'fingerprint':fingerprint,'job_id':jid})
        return self._public_job(job)

    def choose_style(self,sid,jid,style):
        with self.store.transaction() as tx:
            session=tx.get('sessions',sid)
            if self.s.mode=='live' and not (session and session.get('user_id')):
                raise RuleError('请先验证邮箱，再继续制作',401)
            job=self._owned(tx,sid,jid)
            if job.get('workflow')!='personalized_styles_v1':raise RuleError('该作品没有个性化风格预览',409)
            if job.get('style'):
                if job['style']!=style:raise RuleError('本次制作的风格已锁定',409)
                if job['state'] in ('QUEUED','GENERATING','PROCESSING','READY'):return self._public_job(job)
            if job['state']!='STYLE_READY':raise RuleError('请先完成风格预览',409)
            if job['expires']<=self.clock():raise RuleError('风格预览已过期，请重新上传',410)
            if style not in job['final_prompts']:raise RuleError('请选择本次生成的风格')
            if not job.get('free') and not job.get('grant_id'):
                session=tx.get('sessions',sid)
                owner=tx.get('users',session['user_id']) if session and session.get('user_id') else None
                grants=sorted([g for g in tx.all('grants') if owner and g['user_id']==owner['id'] and
                               g['available']>0 and not g['revoked']],key=lambda g:g['created'])
                if not grants:raise RuleError('这份作品已关联到邮箱，但该邮箱的免费体验已用过。请先购买制作次数再继续生成。',402)
                grant=grants[0];grant['available']-=1;tx.put('grants',grant['id'],grant)
                job.update(grant_id=grant['id'],unlocked=True)
            index=next(s['index'] for s in job['preview_styles'] if s['id']==style)
            job.update(style=style,style_index=index,prompt=job['final_prompts'][style],state='QUEUED',expires=None)
            # Existing previews keep the exact prompt/version saved when they were created.
            job['prompt_version']=job.get('final_prompt_version',job['prompt_version'])
            tx.put('jobs',jid,job)
            return self._public_job(job)

    def _release_reservation(self,tx,job):
        if job.get('reservation_released'):return
        if job.get('grant_id'):
            grant=tx.get('grants',job['grant_id'])
            if grant and not grant['revoked']:grant['available']+=1;tx.put('grants',grant['id'],grant)
        elif job.get('free'):
            session=tx.get('sessions',job['session_id']);session['trial_used']=False;tx.put('sessions',session['id'],session)
            if job.get('user_id'):
                user=tx.get('users',job['user_id']);user['trial_used']=False;tx.put('users',user['id'],user)
        job['reservation_released']=True

    def cancel_preview(self,sid,jid):
        with self.store.transaction() as tx:
            job=self._owned(tx,sid,jid)
            if job.get('workflow')!='personalized_styles_v1':raise RuleError('不是风格预览任务',409)
            if job['state']=='CANCELLED':return {'ok':True}
            if job['state']!='STYLE_READY':raise RuleError('制作中不能更换照片，请等待当前步骤完成',409)
            self._release_reservation(tx,job)
            job.update(state='CANCELLED',expires=self.clock());tx.put('jobs',jid,job)
        folder=self.s.data_dir/'jobs'/jid
        if self.s.debug_retain_assets:
            for path in folder.glob('input-*.jpg'):path.unlink(missing_ok=True)
        else:shutil.rmtree(folder,ignore_errors=True)
        return {'ok':True}

    def preview_file(self,sid,jid,index):
        if index not in range(1,5):raise RuleError('风格不存在',404)
        with self.store.transaction() as tx:
            job=self._owned(tx,sid,jid)
            if job.get('workflow')!='personalized_styles_v1' or job['state'] not in ('STYLE_READY','QUEUED','GENERATING','PROCESSING','READY'):
                raise RuleError('风格预览尚未准备好',409)
            if self._expired(job):raise RuleError('风格预览已过期',410)
        path=self.s.data_dir/'jobs'/jid/f'style-choice-{index}.jpg'
        if not path.is_file():raise RuleError('风格预览已清理',410)
        return path
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
        if self._expired(job): raise RuleError('作品已过期，请使用之前保存的副本',410)
    def authorize_file(self,sid,jid,name,token=None):
        archive=name.endswith('.zip') and name!='stickers.zip'
        asset_name=name[:-4] if archive else name
        match=re.fullmatch(r'(preview-[1-9]\.jpg|sticker-[1-9](?:-256\.png|-240\.(?:png|gif)|\.png|\.webp)|grid\.png|stickers\.zip)',asset_name)
        if archive and not asset_name.startswith('sticker-'):raise RuleError('文件不存在',404)
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
            if asset_name.startswith('preview-') and not signed: pass
            elif not job['unlocked']:
                cell=int(asset_name[8]) if asset_name.startswith('sticker-') else None
                if cell not in job['selected']: raise RuleError('这张还未解锁',403)
            folder=self.s.data_dir/'jobs'/jid
            path=folder/asset_name
            needs_export=not path.is_file()
            if asset_name.endswith('-240.gif') and path.is_file():
                from PIL import Image
                with Image.open(path) as image:needs_export=image.info.get('background')!=255
            if needs_export and re.fullmatch(r'sticker-[1-9]-240\.(png|gif)',asset_name):
                from PIL import Image
                original=folder/f'{asset_name[:9]}.png'
                if original.is_file():
                    with Image.open(original) as image:
                        scaled=image.convert('RGBA').resize((240,240),Image.Resampling.LANCZOS)
                    temporary=folder/f'.export-{uuid.uuid4().hex}'
                    try:
                        if asset_name.endswith('.gif'):save_wechat_gif(scaled,temporary)
                        else:scaled.save(temporary,format='PNG')
                        os.replace(temporary,path)
                    finally:
                        temporary.unlink(missing_ok=True)
            if not path.is_file(): raise RuleError('文件已清理',410)
            if archive:
                target=folder/name
                if not target.is_file() or target.stat().st_mtime_ns<path.stat().st_mtime_ns:
                    temporary=folder/f'.export-{uuid.uuid4().hex}'
                    try:
                        with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as output:output.write(path,asset_name)
                        os.replace(temporary,target)
                    finally:temporary.unlink(missing_ok=True)
                path=target
            return path
    def share_link(self,sid,jid,cell,variant):
        if type(cell)!=int or cell not in range(1,10):raise RuleError('贴纸不存在',404)
        suffix={'png512':'.png','png256':'-256.png','png240':'-240.png','gif240':'-240.gif','webp512':'.webp'}.get(variant)
        if not suffix:raise RuleError('分享格式无效')
        name=f'sticker-{cell}{suffix}'
        path=self.authorize_file(sid,jid,name)
        with self.store.transaction() as tx:
            job=self._owned(tx,sid,jid);expires=self.clock()+86400
            if not self.s.debug_retain_assets:expires=min(job['expires'],expires)
        token=self.file_token(jid,name,expires)
        base=(self.s.asset_url or self.s.public_url).rstrip('/')+'/api/files/'+jid+'/'
        archive_name=name+'.zip'
        from PIL import Image
        with Image.open(path) as image:
            alpha=image.convert('RGBA').getchannel('A')
            transparent=alpha.getextrema()[0]<255
            width,height=image.size
        return {'url':base+name+'?token='+token,
                'archive_url':base+archive_name+'?token='+self.file_token(jid,archive_name,expires),
                'expires':expires,'name':name,'local_only':self.s.mode=='demo',
                'width':width,'height':height,'has_transparency':transparent,
                'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}

    def file_token(self,jid,name,expires):
        stamp=str(int(expires));return stamp+'.'+self.digest(jid+name+stamp)
    def _grant(self,tx,gid,uid,quantity,source):
        if tx.get('grants',gid):return
        tx.put('grants',gid,{'id':gid,'user_id':uid,'available':quantity,'quantity':quantity,'consumed':0,
                            'revoked':False,'source':source,'created':self.clock()})
    def checkout(self,sid,product,jid=None,order_id=None):
        if product not in PRODUCTS:raise RuleError('商品不存在',404)
        _,user,_=self.current(sid)
        if not user:raise RuleError('请先验证邮箱',401)
        if self.s.mode=='demo': raise RuleError('当前是示例体验，不会收款；真实支付待配置',503)
        price=os.getenv('PADDLE_PRICE_'+product+'_ID','')
        if not price or not os.getenv('PADDLE_PRODUCT_ID') or not os.getenv('PADDLE_WEBHOOK_SECRET'):raise RuleError('支付通知配置尚未完成，暂不能付款',503)
        now=self.clock(); oid=uuid.uuid4().hex
        with self.store.transaction() as tx:
            current_session=tx.get('sessions',sid)
            user=tx.get('users',current_session['user_id']) if current_session and current_session.get('user_id') else None
            if not user:raise RuleError('请先验证邮箱',401)
            if product=='FIRST_PACK_UNLOCK':
                job=self._owned(tx,sid,jid);self._ready(job)
                if not (self.s.data_dir/'jobs'/jid/'stickers.zip').is_file():raise RuleError('作品文件暂时不可交付，请联系站点管理员',409)
                if job['unlocked']:raise RuleError('这一套已经解锁',409)
                if user['paid_once']:raise RuleError('首次优惠已使用',409)
                # Keep the existing asset alive during checkout, without reviving expired files.
                job['expires']=max(job['expires'],now+3600);tx.put('jobs',jid,job)
            existing=[o for o in tx.all('orders') if o['user_id']==user['id'] and o['state']=='PENDING']
            same=next((o for o in existing if o['id']==order_id and o['product']==product and
                       o.get('job_id')==jid and o.get('checkout_mode')=='paddlejs'),None) if order_id else None
            if order_id and not same:raise RuleError('这笔订单已完成，请刷新订单记录后重试',409)
            if same:
                oid=same['id']
            else:
                same=next((o for o in existing if o['product']==product and o.get('job_id')==jid and
                           o.get('checkout_mode')=='paddlejs'),None)
                if same:
                    oid=same['id']
                elif product=='FIRST_PACK_UNLOCK' and any(o['product']=='FIRST_PACK_UNLOCK' and
                        o.get('checkout_mode')=='paddlejs' for o in existing):
                    raise RuleError('已有一笔首次解锁订单尚未完成。请到设置里的“我的订单”继续原作品，避免重复扣款。',409)
                else:
                    order={'id':oid,'user_id':user['id'],'job_id':jid,'product':product,'price_id':price,
                           'state':'PENDING','transaction_id':None,'created':now,'checkout_mode':'paddlejs'}
                    tx.put('orders',oid,order)
            if self.order_payment_state(tx,tx.get('orders',oid)):
                raise RuleError('这笔订单正在核验付款，请勿重复付款；请刷新订单状态',409)
        # Paddle.js creates the transaction. Only signed, API-verified completion grants delivery.
        return {'order_id':oid,'items':[{'priceId':price,'quantity':1}],
                'customData':{'emjo_order_id':oid},'customer':{'email':user['email']}}

    def account_history(self,sid):
        _,user,_=self.current(sid)
        if not user:raise RuleError('请先验证邮箱',401)
        with self.store.transaction() as tx:
            jobs=sorted([j for j in tx.all('jobs') if j.get('user_id')==user['id']],
                        key=lambda j:j['created'],reverse=True)
            orders=sorted([o for o in tx.all('orders') if o['user_id']==user['id']],
                          key=lambda o:o['created'],reverse=True)
            history_jobs=[]
            for job in jobs[:30]:
                mail=tx.get('mail','delivery-'+job['id'])
                history_jobs.append({'id':job['id'],'state':'EXPIRED' if self._expired(job) else job['state'],
                    'created':job['created'],'style':job.get('style'),'selected':job.get('selected',[]),
                    'unlocked':bool(job.get('unlocked')),'free':bool(job.get('free')),
                    'demo':bool(job.get('demo')),'delivery_state':mail.get('state') if mail else None})
            history_orders=[{'id':o['id'],'product':o['product'],'state':o['state'],
                'payment_state':self.order_payment_state(tx,o),
                'generation_id':o.get('job_id'),'created':o['created'],
                'delivery_state':(tx.get('mail','delivery-'+o['job_id']) or {}).get('state') if o.get('job_id') else None}
                for o in orders[:30]]
        return {'jobs':history_jobs,'orders':history_orders}
    def order_payment_state(self,tx,order):
        if order['state']!='PENDING':return None
        notifications=[n for n in tx.all('payment_notifications') if n.get('order_id')==order['id']]
        if any(n['state']=='REVIEW' for n in notifications):return 'REVIEW'
        if any(n['state'] in ('PENDING','PROCESSING','FAILED') for n in notifications):return 'CONFIRMING'
        return None
    def enqueue_payment(self,event):
        if not isinstance(event,dict):raise RuleError('Invalid event')
        eid=event.get('event_id');kind=event.get('event_type');data=event.get('data',{})
        if not isinstance(eid,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,100}',eid) or not isinstance(data,dict):
            raise RuleError('Invalid event')
        if kind=='transaction.completed':transaction_id=data.get('id');refund_type=None
        elif kind=='adjustment.updated' and data.get('action')=='refund' and data.get('status')=='approved':
            transaction_id=data.get('transaction_id');refund_type=data.get('type')
            if refund_type not in ('full','partial'):raise RuleError('Invalid refund')
        else:return
        if not isinstance(transaction_id,str) or not re.fullmatch(r'txn_[a-zA-Z0-9_]{1,80}',transaction_id):
            raise RuleError('Invalid transaction')
        now=self.clock()
        # Store only identifiers needed for recovery, never customer/payment payloads.
        with self.store.transaction() as tx:
            if tx.get('payment_notifications',eid) or tx.get('events',eid):return
            tx.put('payment_notifications',eid,{'id':eid,'kind':kind,'transaction_id':transaction_id,
                'refund_type':refund_type,'state':'PENDING','attempts':0,'created':now,'next':now})
    def payment_once(self):
        now=self.clock();notification=None
        with self.store.transaction() as tx:
            candidates=sorted([n for n in tx.all('payment_notifications') if
                (n['state'] in ('PENDING','FAILED') and n['next']<=now) or
                (n['state']=='PROCESSING' and n.get('lease_until',0)<=now)],key=lambda n:n['created'])
            if candidates:
                notification=candidates[0]
                notification.update(state='PROCESSING',attempts=notification['attempts']+1,lease_until=now+120)
                tx.put('payment_notifications',notification['id'],notification)
        if not notification:return False
        state='DONE';reason=None
        try:
            if notification['kind']=='transaction.completed':
                actual=self.providers.paddle('GET','/transactions/'+notification['transaction_id'])
                if actual.get('id')!=notification['transaction_id']:raise RuleError('交易不匹配',409)
                notification['order_id']=(actual.get('custom_data') or {}).get('emjo_order_id')
                self.complete_payment(notification['id'],actual)
            elif notification['refund_type']=='full':
                self.refund(notification['id'],notification['transaction_id'])
            else:
                with self.store.transaction() as tx:
                    tx.put('review',notification['id'],{'id':notification['id'],
                        'transaction_id':notification['transaction_id'],'reason':'partial_refund'})
        except RuleError as exc:
            state,reason='REVIEW','invalid_amount' if str(exc)=='交易金额无效' else 'transaction_mismatch'
        except Exception:
            state,reason='FAILED','provider_unavailable'
        with self.store.transaction() as tx:
            notification.update(state=state,next=self.clock()+min(3600,30*2**min(notification['attempts']-1,7)))
            if reason:notification['failure_code']=reason
            if state=='REVIEW':tx.put('review',notification['id'],{'id':notification['id'],
                'transaction_id':notification['transaction_id'],'reason':reason})
            tx.put('payment_notifications',notification['id'],notification)
        return True
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
            totals=data.get('details',{}).get('totals',{})
            if not re.fullmatch(r'[0-9]+',str(totals.get('total',''))) or not re.fullmatch('[A-Z]{3}',data.get('currency_code','')):
                raise RuleError('交易金额无效',409)
            total=int(totals['total'])
            if total==0:
                # Paddle legitimately completes fully discounted orders without a charge.
                # Accept only a verified full discount, never an unexplained zero total.
                fields=('subtotal','tax','discount','grand_total','balance')
                if not all(re.fullmatch(r'[0-9]+',str(totals.get(k,''))) for k in fields):
                    raise RuleError('交易金额无效',409)
                if not (data.get('discount_id') and int(totals['subtotal'])>0 and
                        int(totals['discount'])==int(totals['subtotal'])+int(totals['tax']) and
                        int(totals['grand_total'])==0 and int(totals['balance'])==0 and
                        totals.get('currency_code')==data['currency_code']):
                    raise RuleError('交易金额无效',409)
            order.update(transaction_id=data['id'],state='PAID',amount=total,currency=data['currency_code'],paid_at=self.clock())
            user=tx.get('users',order['user_id'])
            if tx.get('payment_refunds',data['id']):
                order['state']='REFUNDED';tx.put('orders',oid,order);tx.put('events',event_id,{'id':event_id});return
            if order['product']=='FIRST_PACK_UNLOCK':
                job=tx.get('jobs',order['job_id'])
                if not job or job['state']!='READY' or self._expired(job) or job['unlocked'] or user['paid_once'] or not (self.s.data_dir/'jobs'/job['id']/'stickers.zip').is_file():
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
            tx.put('payment_refunds',transaction_id,{'id':transaction_id,'event_id':event_id})
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
            candidates=sorted([j for j in tx.all('jobs') if j['state'] in ('QUEUED','PREVIEW_QUEUED')],key=lambda j:j['created'])
            if candidates:
                job=candidates[0];job.update(state='PREVIEW_GENERATING' if job['state']=='PREVIEW_QUEUED' else 'GENERATING',lease_until=now+360);tx.put('jobs',job['id'],job)
        if not job:return False
        folder=self.s.data_dir/'jobs'/job['id']
        is_preview=job['state']=='PREVIEW_GENERATING'
        stage='style_generation' if is_preview else 'generation'
        try:
            raw=folder/('style-output.png' if is_preview else 'provider-output.png')
            if raw.exists():output=raw.read_bytes()
            else:
                photos=[(folder/f'input-{i+1}.jpg').read_bytes() for i in range(job['photo_count'])]
                if not is_preview and job.get('workflow')=='personalized_styles_v1':
                    photos.append((folder/f"style-reference-{job['style_index']}.jpg").read_bytes())
                output=(self.providers.generate_styles if is_preview else self.providers.generate)(job['prompt'],photos)
                temporary=raw.with_suffix('.tmp');temporary.write_bytes(output);temporary.replace(raw)
            if is_preview:
                stage='style_processing'
                prepare_styles(output,folder,demo=self.s.mode=='demo')
                with self.store.transaction() as tx:
                    current=tx.get('jobs',job['id']);current.update(state='STYLE_READY',error=None)
                    tx.put('jobs',job['id'],current)
                return True
            with self.store.transaction() as tx:
                current=tx.get('jobs',job['id']);current['state']='PROCESSING';tx.put('jobs',job['id'],current)
            stage='processing'
            prepare_pack(output,folder,job['captions'],os.getenv('EMJO_BACKGROUND_REMOVAL_MODE') or 'alpha_only',strict_boundaries=self.s.mode!='demo')
            with self.store.transaction() as tx:
                current=tx.get('jobs',job['id'])
                if current.get('grant_id'):
                    grant=tx.get('grants',current['grant_id'])
                    if grant['revoked']:raise RuleError('该生成权益已退款')
                    grant['consumed']+=1;tx.put('grants',grant['id'],grant)
                current.update(state='READY',expires=self.clock()+3600*(self.s.paid_ttl_hours if current['unlocked'] else self.s.ttl_hours))
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
                    code=exc.code if isinstance(exc,ProviderError) else 'image_processing_failed' if stage.endswith('processing') else 'image_generation_failed'
                    message='图片服务配置异常，生成机会已退回。请等待站点修复后再试。' if code in ('image_auth_failed','image_permission_failed') else '这次没能制作完成，生成机会已退回。请稍后再试。'
                    if code in ('image_rate_limited','image_quota_exceeded','image_spending_limit','image_capacity_failed'):
                        message=str(exc)+'。生成机会已退回，请勿连续重试。'
                    elif code=='image_processing_failed':
                        message='图片已生成，但透明处理或主体完整性检查未通过，生成机会已退回。'
                    diagnostics=exc.diagnostics if isinstance(exc,ProviderError) else {}
                    current.update(state='FAILED',error=message,failure_code=code,failure_stage=stage,
                                   provider_diagnostics=diagnostics,expires=self.clock()+86400)
                    import logging
                    logging.getLogger('emjo').warning('Generation failed: job=%s stage=%s code=%s diagnostics=%s',job['id'],stage,code,json.dumps(diagnostics))
                    self._release_reservation(tx,current)
                    tx.put('jobs',job['id'],current)
        finally:
            with self.store.transaction() as tx:latest=tx.get('jobs',job['id'])
            if latest['state']!='STYLE_READY':
                for path in folder.glob('input-*.jpg'):path.unlink(missing_ok=True)
        return True
    def maintenance(self):
        now=self.clock(); to_delete=[];uploads_to_delete=[]
        with self.store.transaction() as tx:
            for job in tx.all('jobs'):
                if self._expired(job) and job['state'] not in ('GENERATING','PROCESSING','PREVIEW_GENERATING'):
                    if job['state'] in ('STYLE_READY','PREVIEW_QUEUED'):self._release_reservation(tx,job)
                    job['state']='EXPIRED';job.pop('prompt',None);job.pop('final_prompts',None);tx.put('jobs',job['id'],job)
                    folder=self.s.data_dir/'jobs'/job['id']
                    if self.s.debug_retain_assets:uploads_to_delete.extend(folder.glob('input-*.jpg'))
                    else:to_delete.append(folder)
                # Uncertain upstream outcomes are surfaced for recovery, never blindly reissued.
                if job['state'] in ('GENERATING','PROCESSING','PREVIEW_GENERATING') and job.get('lease_until',0)<now:
                    preview=job['state']=='PREVIEW_GENERATING'
                    raw=self.s.data_dir/'jobs'/job['id']/('style-output.png' if preview else 'provider-output.png')
                    if raw.exists():
                        job.update(state='PREVIEW_QUEUED' if preview else 'QUEUED',error=None)
                    else:
                        job.update(state='FAILED',error='制作中断，机会已退回。请重新尝试。',expires=now+86400)
                        self._release_reservation(tx,job)
                        if not self.s.debug_retain_assets:to_delete.append(self.s.data_dir/'jobs'/job['id'])
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
        for path in uploads_to_delete:path.unlink(missing_ok=True)
    def mail_once(self):
        now=self.clock(); mail=None
        with self.store.transaction() as tx:
            candidates=[m for m in tx.all('mail') if m['state'] in ('PENDING','FAILED') and m['attempts']<4 and m['next']<=now]
            if candidates:
                mail=candidates[0]
                job=tx.get('jobs',mail['job_id']);user=tx.get('users',job['user_id']) if job else None
                if job and 'link_expires' not in mail:
                    mail['link_expires']=now+86400 if self.s.debug_retain_assets else job['expires']
                mail.update(state='SENDING',attempts=mail['attempts']+1,lease_until=now+120);tx.put('mail',mail['id'],mail)
        if not mail:return
        try:
            if not job or not user or not job['unlocked'] or self._expired(job):raise RuleError('交付已失效')
            path=self.s.data_dir/'jobs'/job['id']/'stickers.zip'
            token=self.file_token(job['id'],'stickers.zip',mail['link_expires'])
            link=(self.s.asset_url or self.s.public_url).rstrip('/')+'/api/files/'+job['id']+'/stickers.zip?token='+token
            content=path.read_bytes();attachment=content if len(content)<=10*1024*1024 else None
            provider_id=self.providers.email(user['email'],'你的九种小心情，准备好啦',
                f'<p>你的九张贴纸已经准备好。请解压附件，保存透明原文件。</p><p>内含同一套九张：PNG 512／256／240、静态透明 GIF 240、WebP 512，以及整套拼图。</p><p><a href="{link}">下载完整贴纸包</a></p><p>链接仅在本次24小时交付窗口内有效，请及时保存。</p>',mail['id'],attachment)
            mail['provider_id']=provider_id;state='SENT'
        except Exception:state='FAILED'
        with self.store.transaction() as tx:
            mail.update(state=state,next=self.clock()+300*mail['attempts']);tx.put('mail',mail['id'],mail)
