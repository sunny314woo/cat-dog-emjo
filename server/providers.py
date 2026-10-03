"""Server-only integration adapters. Demo never sends photos, email or payments."""
import base64
import hashlib
import hmac
import json
import os
import time
import httpx
from .settings import ROOT

class ProviderError(Exception): pass

def require(*names):
    missing=[n for n in names if not os.getenv(n)]
    if missing: raise ProviderError('服务配置尚未完成：'+', '.join(missing))

class Providers:
    def __init__(self, settings): self.settings=settings
    def generate(self, prompt, photos):
        if self.settings.mode=='demo': return (ROOT/'assets/cat-grid.png').read_bytes()
        require('VOLCENGINE_API_KEY','VOLCENGINE_MODEL_ID','VOLCENGINE_FINAL_SIZE')
        payload={'model':os.environ['VOLCENGINE_MODEL_ID'],'prompt':prompt,
                 'image':['data:image/jpeg;base64,'+base64.b64encode(p).decode() for p in photos],
                 'size':os.environ['VOLCENGINE_FINAL_SIZE'],'response_format':'b64_json',
                 'sequential_image_generation':'disabled','watermark':False}
        with httpx.Client(timeout=180) as client:
            response=client.post(os.getenv('VOLCENGINE_BASE_URL','https://ark.cn-beijing.volces.com/api/v3').rstrip('/')+'/images/generations',
                headers={'Authorization':'Bearer '+os.environ['VOLCENGINE_API_KEY']},json=payload)
            if not response.is_success: raise ProviderError('图片服务暂未完成，请稍后重试')
            data=response.json().get('data',[])
            if len(data)!=1 or not data[0].get('b64_json'): raise ProviderError('图片服务未返回单张有效母图')
            return base64.b64decode(data[0]['b64_json'],validate=True)
    def email(self, address, subject, html, key, attachment=None):
        if self.settings.mode=='demo': return 'demo-mail-'+key
        require('RESEND_API_KEY','MAIL_FROM')
        payload={'from':os.environ['MAIL_FROM'],'to':[address],'subject':subject,'html':html}
        if attachment:
            payload['attachments']=[{'filename':'my-stickers.zip','content':base64.b64encode(attachment).decode()}]
        with httpx.Client(timeout=25) as client:
            response=client.post('https://api.resend.com/emails',json=payload,headers={
                'Authorization':'Bearer '+os.environ['RESEND_API_KEY'],'Idempotency-Key':key})
            if not response.is_success: raise ProviderError('邮件发送暂未完成')
            return response.json()['id']
    def paddle(self, method, path, body=None):
        if self.settings.mode=='demo': raise ProviderError('示例模式不创建支付或扣款')
        require('PADDLE_API_KEY')
        base='https://api.paddle.com' if os.getenv('PADDLE_ENVIRONMENT')=='live' else 'https://sandbox-api.paddle.com'
        with httpx.Client(timeout=25) as client:
            response=client.request(method,base+path,json=body,headers={'Authorization':'Bearer '+os.environ['PADDLE_API_KEY']})
            if not response.is_success: raise ProviderError('支付服务暂未完成，请稍后重试')
            return response.json()['data']

def verify_signature(raw, header, secret, now=None):
    fields={}
    for pair in header.split(';'):
        if '=' in pair:
            key,value=pair.split('=',1); fields.setdefault(key,[]).append(value)
    try:
        timestamp=fields['ts'][0]
        if abs((now if now is not None else time.time())-int(timestamp))>5: return False
        expected=hmac.new(secret.encode(),timestamp.encode()+b':'+raw,hashlib.sha256).hexdigest()
        return bool(secret) and any(hmac.compare_digest(expected,v) for v in fields.get('h1',[]))
    except (KeyError,ValueError): return False
