from contextlib import asynccontextmanager
from pathlib import Path
import asyncio
import json
import os
import re
from urllib.parse import urlparse
from fastapi import FastAPI, Request, Response, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
from .settings import ROOT, Settings
from .store import DemoStore, MySQLStore
from .providers import Providers, ProviderError, verify_signature
from .service import Service, RuleError
from .catalog import CATALOG, PRODUCTS

class EmailInput(BaseModel): email: str = Field(max_length=254)
class VerifyInput(EmailInput):
    code: str = Field(max_length=6)
    referral: str | None = Field(default=None,max_length=40)
class ClaimInput(BaseModel): cells: list[int]
class StyleInput(BaseModel): style: str = Field(max_length=80)
class ShareInput(BaseModel):
    cell: int
    variant: str = "png512"
class CheckoutInput(BaseModel):
    product: str
    generation_id: str | None = None
class FeedbackInput(BaseModel):
    category: str = Field(max_length=80)
    description: str = Field(default='',max_length=1000)

def create_app(settings=None, store=None, providers=None, start_worker=True):
    settings=settings or Settings();settings.validate()
    store=store or (DemoStore(settings.data_dir/'demo-state.json') if settings.mode=='demo' else MySQLStore())
    service=Service(settings,store,providers or Providers(settings))
    async def worker():
        while True:
            try:
                await run_in_threadpool(service.maintenance)
                await run_in_threadpool(service.work_once)
                await run_in_threadpool(service.mail_once)
            except Exception:
                # Never log private upload data, emails, provider credentials or OTPs.
                import logging;logging.getLogger('emjo').error('Background operation failed; retained state for recovery')
            await asyncio.sleep(1)
    @asynccontextmanager
    async def lifespan(app):
        task=asyncio.create_task(worker()) if start_worker else None
        yield
        if task:
            task.cancel()
            try:await task
            except asyncio.CancelledError:pass
    app=FastAPI(title='EMJO isolated API',lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
    app.add_middleware(CORSMiddleware,allow_origins=[urlparse(settings.public_url).scheme+'://'+urlparse(settings.public_url).netloc],allow_credentials=True,allow_methods=['GET','POST','DELETE'],allow_headers=['Content-Type'])
    app.state.service=service
    @app.exception_handler(RuleError)
    async def rule_handler(request,exc):return JSONResponse({'error':str(exc)},status_code=exc.status)
    @app.exception_handler(ProviderError)
    async def provider_handler(request,exc):return JSONResponse({'error':str(exc)},status_code=503)
    @app.middleware('http')
    async def safeguards(request,call_next):
        if request.method in ('POST','PUT','DELETE','PATCH'):
            origin=request.headers.get('origin')
            if origin and origin != urlparse(settings.public_url).scheme+'://'+urlparse(settings.public_url).netloc and urlparse(origin).netloc!=request.headers.get('host'):
                return JSONResponse({'error':'请求来源不匹配'},status_code=403)
            length=request.headers.get('content-length')
            if length and (not length.isdigit() or int(length)>48*1024*1024):return JSONResponse({'error':'上传内容过大'},status_code=413)
            if request.url.path.endswith(('/generations','/style-previews')) and request.method=='POST' and not length:
                return JSONResponse({'error':'上传请求需要指定长度'},status_code=411)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        if '/api/' in request.url.path:response.headers['Cache-Control']='private, no-store'
        return response
    def identity(request):
        token,row=service.session(request.cookies.get('emjo_session'))
        request.state.emjo_token=token
        return row['id']
    def session_response(request,data):
        response=JSONResponse(data)
        response.set_cookie('emjo_session',request.state.emjo_token,max_age=365*86400,httponly=True,
                            secure=settings.mode=='live',samesite='lax',path='/')
        return response
    prefix=settings.api_prefix
    @app.get(prefix+'/catalog')
    def catalog(request:Request):
        sid=identity(request)
        public_styles=[{k:v for k,v in s.items() if k!='prompt'} for s in CATALOG['styles'] if s['active']]
        products=[dict(p,price_id=os.getenv('PADDLE_PRICE_'+p['id']+'_ID') or None,
                       available=settings.mode=='live' and bool(os.getenv('PADDLE_WEBHOOK_SECRET')) and bool(os.getenv('PADDLE_PRICE_'+p['id']+'_ID'))) for p in PRODUCTS.values()]
        return session_response(request,{'styles':public_styles,'theme':CATALOG['theme'],'products':products,
            'me':service.me(sid),'calibration':{'enabled':settings.calibration_enabled,'limit':settings.calibration_limit,'days':settings.calibration_days},
            'workflow':'personalized_styles_v1',
            'paddle':{'environment':os.getenv('PADDLE_ENVIRONMENT','sandbox'),'clientToken':os.getenv('PADDLE_CLIENT_TOKEN','')}})
    @app.get(prefix+'/me')
    def me(request:Request):return session_response(request,service.me(identity(request)))
    @app.post(prefix+'/auth/code')
    def code(body:EmailInput,request:Request):return session_response(request,service.request_code(identity(request),body.email))
    @app.post(prefix+'/auth/verify')
    def verify(body:VerifyInput,request:Request):return session_response(request,service.verify_code(identity(request),body.email,body.code,body.referral))
    @app.post(prefix+'/auth/logout')
    def logout(request:Request):
        sid=identity(request)
        with store.transaction() as tx:
            row=tx.get('sessions',sid);row['user_id']=None;tx.put('sessions',sid,row)
        return {'ok':True}
    @app.post(prefix+'/generations')
    def generate(request:Request,photos:list[UploadFile]=File(...),request_id:str=Form(...),style:str=Form(...),
                 captions:bool=Form(True),accessories:bool=Form(True),calibration_consent:bool=Form(False)):
        if settings.mode=='live' and os.getenv('EMJO_REQUIRE_STYLE_PREVIEW')=='true':
            raise RuleError('制作流程已更新，请刷新页面后先生成四种风格',409)
        sid=identity(request)
        if not 1<=len(photos)<=3:raise RuleError('请上传 1–3 张照片')
        content=[p.file.read(settings.upload_bytes+1) for p in photos]
        return session_response(request,service.create_job(sid,request_id,content,style,captions,accessories,calibration_consent))
    @app.get(prefix+'/generations/{jid}')
    def generation(jid:str,request:Request):return service.job(identity(request),jid)
    @app.post(prefix+'/style-previews')
    def style_preview(request:Request,photos:list[UploadFile]=File(...),request_id:str=Form(...),
                      captions:bool=Form(True),accessories:bool=Form(True),calibration_consent:bool=Form(False)):
        sid=identity(request)
        if not 1<=len(photos)<=3:raise RuleError('请上传 1–3 张照片')
        content=[p.file.read(settings.upload_bytes+1) for p in photos]
        return session_response(request,service.create_job(sid,request_id,content,None,captions,accessories,calibration_consent,preview=True))
    @app.post(prefix+'/generations/{jid}/style')
    def choose_style(jid:str,body:StyleInput,request:Request):return service.choose_style(identity(request),jid,body.style)
    @app.delete(prefix+'/style-previews/{jid}')
    def cancel_style_preview(jid:str,request:Request):return service.cancel_preview(identity(request),jid)
    @app.get(prefix+'/style-previews/{jid}/{index}')
    def style_image(jid:str,index:int,request:Request):
        return FileResponse(service.preview_file(identity(request),jid,index),media_type='image/jpeg')
    @app.post(prefix+'/generations/{jid}/claim')
    def claim(jid:str,body:ClaimInput,request:Request):return service.claim(identity(request),jid,body.cells)
    @app.post(prefix+'/generations/{jid}/share')
    def share(jid:str,body:ShareInput,request:Request):
        return service.share_link(identity(request),jid,body.cell,body.variant)
    @app.get(prefix+'/files/{jid}/{name}')
    def asset(jid:str,name:str,request:Request,token:str|None=None):
        path=service.authorize_file(identity(request),jid,name,token)
        return FileResponse(path,filename=name if not name.startswith('preview-') else None,
                            media_type='application/zip' if name.endswith('.zip') else 'image/png' if name.endswith('.png') else 'image/gif' if name.endswith('.gif') else 'image/webp' if name.endswith('.webp') else 'image/jpeg')
    @app.post(prefix+'/checkout')
    def checkout(body:CheckoutInput,request:Request):return service.checkout(identity(request),body.product,body.generation_id)
    @app.get(prefix+'/orders/{oid}')
    def order(oid:str,request:Request):
        _,user,_=service.current(identity(request))
        with store.transaction() as tx:
            row=tx.get('orders',oid)
            if not user or not row or row['user_id']!=user['id']:raise RuleError('订单不存在',404)
            return {'state':row['state'],'product':row['product']}
    @app.post(prefix+'/generations/{jid}/feedback')
    def feedback(jid:str,body:FeedbackInput,request:Request):
        sid=identity(request)
        with store.transaction() as tx:
            job=service._owned(tx,sid,jid)
            tx.put('feedback',jid,{'id':jid,'category':body.category,'description':body.description,
                                  'prompt_version':job['prompt_version'],'created':service.clock()})
        return {'ok':True}
    @app.delete(prefix+'/generations/{jid}/calibration')
    def withdraw(jid:str,request:Request):
        sid=identity(request)
        with store.transaction() as tx:
            job=service._owned(tx,sid,jid);job.update(consent=False,calibration=False);tx.put('jobs',jid,job)
            case=tx.get('calibration',jid)
            if case:case['expires']=0;tx.put('calibration',jid,case)
        service.maintenance()
        return {'ok':True}
    @app.post(prefix+'/demo/unlock/{jid}')
    def demo_unlock(jid:str,request:Request):
        if settings.mode!='demo':raise RuleError('接口不存在',404)
        sid=identity(request)
        with store.transaction() as tx:
            job=service._owned(tx,sid,jid);service._ready(job);job['unlocked']=True;tx.put('jobs',jid,job)
        return service.job(sid,jid)
    @app.post('/pet-stickers/api/webhooks/paddle')
    @app.post(prefix+'/webhooks/paddle')
    async def webhook(request:Request):
        if settings.mode=='demo':raise RuleError('示例模式不接收真实支付',404)
        raw=await request.body()
        if not verify_signature(raw,request.headers.get('paddle-signature',''),os.getenv('PADDLE_WEBHOOK_SECRET','')):
            raise RuleError('Invalid signature',401)
        try:event=json.loads(raw)
        except ValueError:raise RuleError('Invalid event')
        kind=event.get('event_type');data=event.get('data',{});eid=event.get('event_id')
        if not eid:raise RuleError('Invalid event')
        if kind=='transaction.completed':
            actual=await run_in_threadpool(service.providers.paddle,'GET','/transactions/'+data['id'])
            await run_in_threadpool(service.complete_payment,eid,actual)
        elif kind=='adjustment.updated' and data.get('action')=='refund' and data.get('status')=='approved':
            # Whole-order refunds only. Partial refunds remain visible for operator review.
            if data.get('type')=='full':await run_in_threadpool(service.refund,eid,data['transaction_id'])
            else:
                with store.transaction() as tx:tx.put('review',eid,{'id':eid,'transaction_id':data.get('transaction_id'),'reason':'partial_refund'})
        return {'ok':True}
    # Explicit public allowlist. Never mount the repository or private data directory.
    @app.get('/')
    @app.get('/sticker/')
    @app.get('/sticker/checkout')
    def index():return FileResponse(ROOT/'index.html')
    for filename in ('styles.css','app.js','config.js'):
        def make_public_file(name):
            def public_file():return FileResponse(ROOT/name)
            return public_file
        public_file=make_public_file(filename)
        app.add_api_route('/'+filename,public_file,methods=['GET'])
        app.add_api_route('/sticker/'+filename,public_file,methods=['GET'])
    app.mount('/assets',StaticFiles(directory=ROOT/'assets'),name='assets')
    app.mount('/sticker/assets',StaticFiles(directory=ROOT/'assets'),name='product-assets')
    return app

app=create_app()
