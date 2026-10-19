'use strict';
const $=id=>document.getElementById(id), API=window.EMJO_CONFIG.apiBase;
let catalog,me,photos=[],cropBlob=null,style,job,selection=new Set(),revealed=new Set(),requestId=null,pollTimer,toastTimer,pendingUnlock=false,pendingGeneration=false;
const busyStates=['PREVIEW_QUEUED','PREVIEW_GENERATING','QUEUED','GENERATING','PROCESSING'];
const localizedPrices=new Map();
let accountHistory=null;
const saved=(key,value)=>{try{if(value===undefined)return localStorage.getItem(key);localStorage.setItem(key,value)}catch{return null}};
const toast=text=>{$('toast').textContent=text;$('toast').hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').hidden=true,5500)};
async function api(path,body,method){const r=await fetch(API+path,{method:method||(body?'POST':'GET'),credentials:'include',headers:body&&!(body instanceof FormData)?{'Content-Type':'application/json'}:{},body:body instanceof FormData?body:body?JSON.stringify(body):undefined});const data=await r.json();if(!r.ok){const e=new Error(data.error||'暂时无法完成，请稍后再试');e.status=r.status;throw e}return data}
function action(id,fn){$(id).addEventListener('click',async()=>{const b=$(id);b.disabled=true;try{await fn()}catch(e){toast(e.message)}finally{b.disabled=false}})}
function node(tag,text,className){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(className)el.className=className;return el}
const shortId=id=>String(id||'').slice(0,8);
const workTitle=item=>`作品 #${shortId(item.id)} · 1 套（9 张）`;
function availablePackProducts(){return catalog.products.filter(p=>p.packs&&p.available&&p.price_id&&catalog.paddle.clientToken&&localizedPrices.has(p.id))}
function taskButton(label,fn,className='button secondary'){const b=node('button',label,className);b.onclick=async()=>{b.disabled=true;try{await fn()}catch(e){toast(e.message)}finally{b.disabled=false}};return b}
async function openWork(id){const email=me.email;clearTimeout(pollTimer);const item=await api('/generations/'+id);if(me.email!==email)return;job=item;saved('emjo-job',job.id);restoreResult();$('account-dialog').close();if(busyStates.includes(job.state))await poll();else await displayJob();window.scrollTo({top:0,behavior:'instant'})}
function orderAmount(item){if(!Number.isSafeInteger(item.amount)||!item.currency)return '';try{const digits=new Intl.NumberFormat('zh-CN',{style:'currency',currency:item.currency}).resolvedOptions().maximumFractionDigits;const number=new Intl.NumberFormat('zh-CN',{minimumFractionDigits:digits,maximumFractionDigits:digits});return `${item.currency} ${number.format(item.amount/10**digits)}`}catch{return ''}}
function deliveryLabel(delivery){return {SENT:'邮件已提交发送',FAILED:'邮件发送失败，可先下载',PENDING:'交付邮件排队中',PROCESSING:'交付邮件发送中'}[delivery?.state]||'尚无交付邮件记录'}
function show(view){$('hero').hidden=true;$('studio').hidden=false;document.body.dataset.screen=view;$('mobile-title').textContent=view==='maker'?'上传与选择':view==='progress-view'?'制作表情包':'领取小心情';for(const id of ['maker','progress-view','result-view'])$(id).hidden=id!==view;$('step-badge').textContent=view==='maker'?'01 / 上传与选择':view==='progress-view'?'02 / 制作中':'03 / 领取小心情'}
function renderEntitlements(){
 const history=accountHistory?.email===me.email?accountHistory:null;
 const unlocked=history?.jobs.filter(j=>j.unlocked&&j.state==='READY').length||0;
 const trial=history?.jobs.some(j=>j.free&&!j.unlocked&&j.state==='READY');
 $('account-access').textContent=unlocked?`已有 ${unlocked} 套作品解锁全部 9 张，可在上方“我的作品”下载。`:me.trial_available?'首次免费体验可用：制作后任选 2 张下载、分享；付费解锁同一套全部 9 张。':trial?'免费体验作品已保留，可领取所选 2 张；打开作品即可付费解锁同一套全部 9 张。':'作品的领取与解锁状态见上方“我的作品”。';
 $('new-pack-balance').hidden=!(me.pack_balance>0);$('account-balance').textContent=me.pack_balance||0;
 $('account-usage').hidden=!(me.pack_total>0);$('account-usage').textContent=`制作额度：累计获得 ${me.pack_total||0} 套 · 已使用 ${me.pack_used||0} 套 · 已预留 ${me.pack_pending||0} 套`;
 $('quota-copy').textContent=me.trial_available?'首次体验，免费任选 2 张；付费解锁同一套 9 张。':me.pack_balance>0?`还可使用 ${me.pack_balance} 套额度；新制作或解锁已有作品，每套各用 1 套额度。`:'已有作品可在“我的作品”领取或解锁。';
}
function renderMe(){ $('mobile-start').textContent=me.email?'上传照片，开始制作 →':'验证邮箱，开始制作 →';$('account-button').textContent='⚙ 设置';$('auth-form').hidden=!!me.email;$('account-details').hidden=!me.email;$('account-email').textContent=me.email||'';renderEntitlements();
 const products=availablePackProducts();
 $('new-pack-products').hidden=!products.length;$('product-list').replaceChildren();for(const p of products){const row=node('div',undefined,'product-row');const details=node('div',undefined,'product-benefits');details.append(node('strong',`${p.packs} 套制作额度`),node('small',`可分次使用。付款后增加 ${p.packs} 套，账户可用额度预计为 ${(me.pack_balance||0)+p.packs} 套。新制作或解锁已有作品，每套各用 1 套额度。`),node('span',priceLabel(p)));row.append(details,taskButton(`购买 ${p.packs} 套额度`,()=>checkout(p.id,null)));$('product-list').append(row)}$('invite-url').value=inviteURL();if(job?.state==='READY')renderUnlockOptions();}
function priceLabel(product){return product?.available?(localizedPrices.get(product.id)?`参考价 ${localizedPrices.get(product.id)} · 以结账页为准`:'金额以结账页为准'):'暂未开放付款'}
async function refreshPrices(){try{const products=catalog.products.filter(p=>p.available&&p.price_id);if(!products.length)return;await initPaddle();const result=await Paddle.PricePreview({items:[...new Set(products.map(p=>p.price_id))].map(priceId=>({priceId,quantity:1}))});for(const line of result.data.details.lineItems){const price=line.formattedTotals?.total;if(price)for(const p of products)if(p.price_id===line.price.id)localizedPrices.set(p.id,price)}renderMe()}catch{renderMe()}}
function inviteURL(){if(!me?.referral_code)return '';const url=new URL('/sticker/',location.origin);url.searchParams.set('ref',me.referral_code);return url.href}
async function copyText(text,field){if(!text)throw new Error('请先验证邮箱');field.value=text;try{if(navigator.clipboard?.writeText){await navigator.clipboard.writeText(text);return true}}catch{}field.hidden=false;field.focus();field.select();field.setSelectionRange(0,text.length);try{if(document.execCommand('copy'))return true}catch{}return false}
function renderStyles(){
 $('style-options').replaceChildren();
 for(const s of job?.preview_styles||[]){
  const b=node('button',undefined,'style-card'+(s.id===style?' active':''));b.setAttribute('aria-pressed',s.id===style);
  const im=node('img',undefined,'personal-style-image');im.src=API+`/style-previews/${job.id}/${s.index}`;im.alt=s.name;
  b.append(im,node('span',s.name,'style-name'),node('span','✓','tick'));
  b.disabled=job.state==='READY';b.onclick=()=>{style=s.id;renderStyles()};$('style-options').append(b);
 }
 $('generate-button').disabled=!style||job?.state!=='STYLE_READY';
 $('style-status').textContent=job?.state==='READY'?'这套表情已生成，可以回看画风。':job?.demo?'本地样例预览 · 未调用 AI':job?.state==='STYLE_READY'?'你的四种画风已准备好':'';
 $('return-result').hidden=job?.state!=='READY';
 $('generate-button').hidden=job?.state==='READY';
 $('back-upload').hidden=job?.state==='READY';
}
async function discardPreview(){
 if(job?.state==='STYLE_READY'){
  await api('/style-previews/'+job.id,null,'DELETE');saved('emjo-job','');job=null;style=null;requestId=null;
  me=await api('/me');renderMe();renderStyles();
 }
}
async function init(){try{catalog=await api('/catalog');me=catalog.me;style=null;$('demo-unlock').hidden=!me.demo;renderMe();if(me.email)refreshHistory();
if(catalog.workflow!=='personalized_styles_v1')throw new Error('新版制作流程正在部署，请稍后刷新');
const next=$('next-style');next.parentNode.insertBefore(document.querySelector('.options'),next);
next.parentNode.insertBefore($('calibration-option'),next);
renderStyles();for(const e of catalog.theme.expressions)$('emotion-chips').append(node('span',`${e.icon||'♡'} ${e.name||e.emotion}`,'emotion-chip'));
if(catalog.calibration.enabled){$('calibration-option').hidden=false;$('calibration-copy').textContent=`可选：同意将本次照片与结果用于提示词校准。仅收集前 ${catalog.calibration.limit} 份同意的成功案例，最多保留 ${catalog.calibration.days} 天，可随时撤回。`}
refreshPrices();
const ref=new URLSearchParams(location.search).get('ref');if(ref)saved('emjo-ref',ref);const jid=saved('emjo-job');if(jid){try{job=await api('/generations/'+jid);restoreResult();$('resume-result').hidden=!['READY','STYLE_READY'].includes(job.state);if(job.state==='STYLE_READY'){$('resume-result').textContent='继续选择我的画风';await displayJob()}if(busyStates.includes(job.state))await poll()}catch{saved('emjo-job','')}}
if(me.email&&saved('emjo-order'))monitorPayment(saved('emjo-order'));
if(new URLSearchParams(location.search).has('_ptxn'))initPaddle();}catch(e){$('connection-error').hidden=false;$('connection-error').textContent='小画室暂时没有连接成功。请稍后刷新页面再试。';toast(e.message)}}
let paddleReady,paymentTimer,paymentRequest=0;
function paymentStatus(text){$('payment-status').textContent=text;$('payment-status').hidden=!text}
function stopPayment(){paymentRequest++;clearTimeout(paymentTimer);paymentStatus('')}
function monitorPayment(oid){
 const request=++paymentRequest;clearTimeout(paymentTimer);let attempts=0,applied=false;
 async function check(){
  if(request!==paymentRequest||saved('emjo-order')!==oid||!me.email)return;
  let delay=2000;
  try{
   const order=await api('/orders/'+encodeURIComponent(oid));if(request!==paymentRequest)return;
   if(order.payment_review_required){me=await api('/me');if(request!==paymentRequest)return;renderMe();paymentStatus('这笔订单有额外付款需要人工核对，请勿重复付款。已有交付与余额可在设置中查看。');refreshHistory();saved('emjo-order','');return}
   if(order.state==='PAID'){
    if(!applied){
     me=await api('/me');if(request!==paymentRequest)return;renderMe();
     if(order.generation_id){job=await api('/generations/'+order.generation_id);if(request!==paymentRequest)return;saved('emjo-job',job.id);restoreResult();show('result-view');renderResult()}
     toast(order.fulfillment==='ALREADY_UNLOCKED'?'作品已解锁，本次购买额度已全部到账':order.generation_id?'支付已确认，这份作品已解锁':'支付已确认，制作次数已到账');applied=true;refreshHistory();
    }
    const delivery=order.delivery_state;
    paymentStatus(order.fulfillment==='ALREADY_UNLOCKED'?'目标作品已解锁，本次购买额度已全部存入账户，没有重复消耗。':!order.generation_id?'支付已确认，制作次数已到账。':delivery==='SENT'?'贴纸邮件已提交发送，请检查收件箱和垃圾邮件。':delivery==='FAILED'?(order.delivery_attempts>=4?'贴纸已解锁，邮件多次发送失败，请下载 ZIP 并联系站点支持。':'贴纸已解锁，邮件暂未发送成功，正在安排重试。'):'贴纸已解锁，邮件正在发送。');
    if(!order.generation_id||delivery==='SENT'){refreshHistory();saved('emjo-order','');return}
    delay=10000;
   }else if(order.state==='REFUND_REQUIRED'||order.state==='REFUNDED'){
    paymentStatus(order.state==='REFUNDED'?'这笔订单已退款。':'已收到付款，交付需要人工处理，请联系站点支持。');saved('emjo-order','');return;
   }else if(order.payment_state==='REVIEW'){paymentStatus('付款核验异常，交付需要核对，请勿重复付款。');refreshHistory();saved('emjo-order','');return;}else if(attempts>=10){paymentStatus('订单尚待确认。如已付款，请勿重复付款，稍后刷新查看。');delay=10000}
  }catch(e){if(request!==paymentRequest)return;if(e.status===404){saved('emjo-order','');paymentStatus('');return}paymentStatus('订单查询暂时中断，请稍后刷新查看；如已付款，请勿重复付款。');delay=10000}
  if(request===paymentRequest&&++attempts<120)paymentTimer=setTimeout(check,delay);
 }
 check();
}
function initPaddle(){if(paddleReady)return paddleReady;paddleReady=new Promise((resolve,reject)=>{if(!catalog.paddle.clientToken){paddleReady=null;reject(new Error('支付配置尚未完成'));return}const s=document.createElement('script');s.src='https://cdn.paddle.com/paddle/v2/paddle.js';s.onerror=()=>{paddleReady=null;reject(new Error('支付页面加载失败，请重试'))};s.onload=()=>{try{if(!window.Paddle)throw new Error('支付组件没有正确加载，请刷新后重试');if(catalog.paddle.environment==='sandbox')Paddle.Environment.set('sandbox');Paddle.Initialize({token:catalog.paddle.clientToken,checkout:{settings:{displayMode:'overlay',variant:'one-page'}},eventCallback:e=>{if(e.name==='checkout.completed'){paymentStatus('正在确认支付结果，请稍候。');const oid=saved('emjo-order');if(oid)monitorPayment(oid)}}});resolve()}catch(e){paddleReady=null;reject(e instanceof Error?e:new Error('支付页面初始化失败，请重试'))}};document.head.append(s)});return paddleReady}
async function addPhotos(files){if(!files.length)return;if((replacePending?0:photos.length)+files.length>3)throw new Error('最多放入三张照片，请先移除不需要的照片');for(const f of files){if(!['image/jpeg','image/png','image/webp'].includes(f.type))throw new Error('请上传 JPG、PNG 或 WebP');if(f.size>15*1024*1024)throw new Error('每张照片请小于 15 MB')}await discardPreview();if(replacePending){photos=[];cropBlob=null;replacePending=false}photos.push(...files);requestId=null;await renderPhotos()}
let previewURL,replacePending=false;
async function renderPhotos(){if(previewURL)URL.revokeObjectURL(previewURL);$('upload-empty').hidden=!!photos.length;$('main-photo').hidden=!photos.length;$('photo-label').hidden=!photos.length;$('photo-actions').hidden=!photos.length;$('generate-button').disabled=!style||job?.state!=='STYLE_READY';$('next-style').disabled=!photos.length;$('add-photo-button').hidden=photos.length>=3;if(photos.length){previewURL=URL.createObjectURL(cropBlob||photos[0]);$('main-photo').src=previewURL}$('file-list').replaceChildren();photos.forEach((f,i)=>{const row=node('div',undefined,'file-row');row.append(node('span',`${i+1===1?'主参考':'补充参考 '+(i+1)} · ${f.name}`));const b=node('button','移除');b.onclick=async()=>{try{await discardPreview();photos.splice(i,1);if(i===0)cropBlob=null;requestId=null;await renderPhotos()}catch(e){toast(e.message)}};row.append(b);$('file-list').append(row)})}
$('photos').onchange=async e=>{try{await addPhotos([...e.target.files])}catch(e){toast(e.message)}finally{$('photos').value='';replacePending=false}};
$('replace-button').onclick=()=>{replacePending=true;$('photos').click()};
$('add-photo-button').onclick=()=>{replacePending=false;$('photos').click()};
$('photos').addEventListener('cancel',()=>replacePending=false);
$('upload-zone').addEventListener('click',e=>{if(e.target!==$('photos'))replacePending=false});
for(const ev of ['dragenter','dragover'])$('upload-zone').addEventListener(ev,e=>{e.preventDefault();$('upload-zone').classList.add('dragging')});$('upload-zone').ondragleave=()=>$('upload-zone').classList.remove('dragging');$('upload-zone').ondrop=async e=>{e.preventDefault();$('upload-zone').classList.remove('dragging');try{await addPhotos([...e.dataTransfer.files])}catch(e){toast(e.message)}};
async function compress(file){const img=await createImageBitmap(file);if(img.width*img.height>40000000){img.close();throw new Error('照片尺寸过大，请使用 4000 万像素以内的图片')}const c=document.createElement('canvas'),r=Math.min(1,2048/Math.max(img.width,img.height));c.width=Math.round(img.width*r);c.height=Math.round(img.height*r);const ctx=c.getContext('2d');ctx.fillStyle='#fff';ctx.fillRect(0,0,c.width,c.height);ctx.drawImage(img,0,0,c.width,c.height);img.close();return new Promise(resolve=>c.toBlob(resolve,'image/jpeg',.92))}
action('generate-button',async()=>{if(!style||job?.state!=='STYLE_READY')return;job=await api(`/generations/${job.id}/style`,{style});selection.clear();revealed.clear();show('progress-view');await poll()});
action('next-style',async()=>{if(job?.state==='STYLE_READY'){await displayJob();return}if(!photos.length)return;if(!me.email){pendingGeneration='generate';$('account-dialog').showModal();return}if(!me.trial_available&&!me.pack_balance){$('account-dialog').showModal();return}requestId=requestId||crypto.randomUUID();const fd=new FormData();for(let i=0;i<photos.length;i++)fd.append('photos',await compress(i===0&&cropBlob?cropBlob:photos[i]),`reference-${i+1}.jpg`);fd.append('request_id',requestId);for(const k of ['captions','accessories'])fd.append(k,$(k).checked);fd.append('calibration_consent',$('calibration-consent').checked);job=await api('/style-previews',fd);style=null;selection.clear();revealed.clear();saved('emjo-job',job.id);show('progress-view');await poll()});
async function poll(){clearTimeout(pollTimer);pollTimer=null;try{job=await api('/generations/'+job.id);await displayJob();if(busyStates.includes(job.state))pollTimer=setTimeout(poll,1700)}catch(e){toast(e.message);pollTimer=setTimeout(poll,5000)}}
async function displayJob(){if(job.state==='STYLE_READY'){show('maker');makerStep('style');renderStyles();$('quota-copy').textContent='本套制作机会已预留';}else if(job.state==='READY'){show('result-view');renderResult();me=await api('/me');renderMe()}else if(busyStates.includes(job.state)){show('progress-view');$('progress-title').textContent={PREVIEW_QUEUED:'照片已收到',PREVIEW_GENERATING:'正在画出你的四种风格',QUEUED:'已选定你的画风',GENERATING:'正在画出九种心情',PROCESSING:'正在整理透明贴纸'}[job.state];$('progress-copy').textContent=job.demo?'这是固定样例制作演示，不会根据上传照片生成。':'本步骤预计 1–2 分钟，繁忙时可能稍久。完成后会自动出现。';['stage-1','stage-2','stage-3'].forEach((id,i)=>$(id).classList.toggle('active',i<({PREVIEW_QUEUED:1,PREVIEW_GENERATING:2,QUEUED:1,GENERATING:2,PROCESSING:3}[job.state])))}else{show('maker');makerStep('upload');toast(job.error||(job.state==='EXPIRED'?'这份心情已过期，请使用已保存的副本。':'作品暂时无法领取'));saved('emjo-job','');requestId=null;style=null;renderStyles();me=await api('/me');renderMe()}}
function restoreResult(){try{const v=JSON.parse(saved('emjo-reveal-'+job.id)||'[]');revealed=new Set(v)}catch{revealed=new Set()}selection=new Set(job.selected||[])}
function persistReveal(){saved('emjo-reveal-'+job.id,JSON.stringify([...revealed]))}
function renderUnlockOptions(){
 if(!job||job.state!=='READY')return;
 const targetId=job.id,workflowReady=catalog.order_workflow==='work_bound_packs_v1',options=job.unlock_options||{},first=catalog.products.find(p=>p.id==='FIRST_PACK_UNLOCK');
 const useBalance=workflowReady&&options.can_use_balance&&me.pack_balance>0,firstOffer=workflowReady&&options.first_offer_available&&first?.available;
 $('result-work-id').textContent=workTitle(job);
 $('unlock-area').hidden=job.unlocked;
 $('unlock-title').textContent='解锁这份作品 · 1 套（9 张）';
 $('unlock-summary').textContent=`本次解锁作品 #${shortId(job.id)} 已生成的这一套，付款或使用额度后可下载、分享并接收交付邮件。`;
 $('balance-unlock-area').hidden=!useBalance;
 $('balance-unlock-copy').textContent=`使用 1 套额度解锁作品 #${shortId(job.id)}；当前 ${me.pack_balance||0} 套，解锁后剩余 ${Math.max(0,(me.pack_balance||0)-1)} 套。`;
 $('balance-unlock-button').textContent='使用 1 套额度，解锁这份作品';
 $('first-unlock-area').hidden=!firstOffer;
 $('unlock-button').disabled=!firstOffer;
 $('unlock-button').textContent='首次优惠，解锁这份作品';
 $('unlock-price').textContent=firstOffer?priceLabel(first):'';
 $('first-unlock-copy').textContent=`首次优惠仅解锁作品 #${shortId(job.id)} 的 1 套（9 张）；已有 ${me.pack_balance||0} 套制作额度继续保留。`;
 const products=workflowReady&&options.can_purchase_pack?availablePackProducts():[];
 const store=$('work-unlock-store');store.hidden=!products.length;
 if(store.dataset.job!==job.id){store.open=!useBalance&&!firstOffer;store.dataset.job=job.id}
 $('work-unlock-products').replaceChildren();
 for(const p of products){
  const row=node('div',undefined,'product-row work-product-row'),details=node('div',undefined,'product-benefits');
  details.append(node('strong',`购买 ${p.packs} 套额度 · 本次解锁 1 套`),node('small',`付款后解锁作品 #${shortId(job.id)} 的 1 套（9 张），本次购买剩余 ${p.packs-1} 套继续保留；账户可用额度预计为 ${(me.pack_balance||0)+p.packs-1} 套。`),node('span',priceLabel(p)));
  row.append(details,taskButton(`购买并解锁这份作品`,()=>checkout(p.id,targetId)));
  $('work-unlock-products').append(row);
 }
 $('unlock-unavailable').hidden=!!(useBalance||firstOffer||products.length);
 $('unlock-unavailable').textContent=!workflowReady?'解锁服务更新中，请稍后刷新。':options.can_purchase_pack?'可用付款方式正在读取，请稍后刷新；已有作品会继续保留。':options.reason||'请稍后刷新查看解锁方式；已有作品会继续保留。';
}
async function unlockWithBalance(){
 if(catalog.order_workflow!=='work_bound_packs_v1')throw new Error('解锁服务更新中，请稍后刷新。');
 const id=job.id,email=me.email;
 const unlocked=await api(`/generations/${id}/unlock`,{}),updatedMe=await api('/me');
 if(me.email!==email)return;
 me=updatedMe;if(job?.id===id){job=unlocked;renderResult()}renderMe();refreshHistory();
 toast(`作品 #${shortId(id)} 已解锁 · 1 套（9 张）`);
}
function renderResult(){if(job.selected?.length)selection=new Set(job.selected);$('result-grid').replaceChildren();for(const e of job.cells||catalog.theme.expressions){const i=e.cell_index,open=revealed.has(i)||job.unlocked||job.selected.includes(i),allowed=job.unlocked||job.selected.includes(i);const card=node('article',undefined,'sticker-card'+(selection.has(i)?' selected':''));card.dataset.cell=i;const picture=node('button',undefined,'sticker-picture');picture.setAttribute('aria-label',open?`${e.name||e.emotion}预览`:`拆开${e.name||e.emotion}`);const flipper=node('span',undefined,'card-flipper'+(open?' is-revealed':''));const back=node('span',undefined,'card-face card-back');const seal=node('span',undefined,'sealed');seal.append(node('span','✦','seal-symbol'),node('span',e.emotion,'seal-text'),node('small','点击翻开'));back.append(node('span',`0${i}`,'card-number'),seal,node('span','给你的一点小惊喜','card-whisper'));const front=node('span',undefined,'card-face card-front');const im=node('img');im.src=API+`/files/${job.id}/${allowed?'sticker-'+i+'.png':'preview-'+i+'.jpg'}?v=20261012-account-recovery`;im.alt=`${e.label} · ${allowed?'512×512透明贴纸':'保护预览'}`;front.classList.toggle('transparent-master',allowed);front.append(im);front.setAttribute('aria-hidden',!open);back.setAttribute('aria-hidden',open);flipper.append(back,front);picture.append(flipper);picture.onclick=()=>{if(!open)return revealCell(i);if(allowed)return openShare(i).catch(e=>toast(e.message));if(!job.free)return toast('这份作品尚未解锁，可在下方使用额度或购买后解锁');if(!job.selected.length){if(selection.has(i))selection.delete(i);else if(selection.size<2)selection.add(i);else return toast('先取消一张，再换选');renderResult()}else toast('解锁整套后可以分享这张')};card.append(picture);const badge=node('span',allowed?'↗':selection.has(i)?'✓':'🔒','card-status');badge.setAttribute('aria-label',allowed?'已解锁，点击分享':selection.has(i)?'已选':'未解锁');card.append(badge);$('result-grid').append(card)}$('claim-area').hidden=job.unlocked||!job.free;$('claim-button').hidden=!!job.selected.length;$('claim-button').disabled=selection.size!==2;$('selection-copy').textContent=job.selected.length?'点已解锁贴纸，即可下载或分享':`翻开后再点选 · 免费选 ${selection.size}/2 张`;$('unlock-area').hidden=job.unlocked;$('delivery-area').hidden=!job.unlocked;$('withdraw-calibration').hidden=!job.calibration;$('privacy-expiry').textContent=job.debug_retained?'生成作品（含未付款作品）暂不自动删除。':job.expires?`本套作品下载截止：${new Date(job.expires*1000).toLocaleString('zh-CN')}。`:'生成结果按下载窗口保留。';$('review-styles').hidden=!job.preview_styles?.length;$('result-description').textContent=job.demo?'本地样例 · 1 套（9 张）':job.unlocked?'已解锁 1 套（9 张）· 点击贴纸即可分享':job.selected?.length?'已领取 2 张 · 点击贴纸即可分享':job.free?'九张均为保护预览；免费体验可任选两张':'这份作品已制作完成；解锁这一套后即可下载和分享';renderUnlockOptions()}
let revealBusy=new Set(),revealTimers=[];
function revealCell(i){
 if(!job||revealed.has(i)||job.unlocked||job.selected.includes(i)||revealBusy.has(i))return;
 const card=document.querySelector(`.sticker-card[data-cell="${i}"]`);if(!card)return;
 revealBusy.add(i);revealed.add(i);persistReveal();
 const flipper=card.querySelector('.card-flipper');flipper.classList.add('is-revealed');card.classList.add('just-revealed');
 card.querySelector('.card-front').setAttribute('aria-hidden','false');card.querySelector('.card-back').setAttribute('aria-hidden','true');
 card.querySelector('.sticker-picture').setAttribute('aria-label',`${(job.cells||catalog.theme.expressions)[i-1].emotion}预览`);
 const sparkle=node('span',undefined,'reveal-sparkles');for(let k=0;k<7;k++){const star=node('i',k%2?'✧':'✦');star.style.setProperty('--k',k);sparkle.append(star)}card.querySelector('.sticker-picture').append(sparkle);
 setTimeout(()=>{card.querySelector('.sticker-picture').onclick=()=>{renderResult();document.querySelector(`.sticker-card[data-cell="${i}"] .sticker-picture`)?.click()};const b=card.querySelector('.select-cell');if(b&&!job.selected.length){b.hidden=false;b.disabled=false;}card.classList.remove('just-revealed');sparkle.remove();revealBusy.delete(i)},850);
}
$('reveal-all').onclick=()=>{revealTimers.forEach(clearTimeout);revealTimers=[];let n=0;for(let i=1;i<=9;i++)if(!revealed.has(i))revealTimers.push(setTimeout(()=>revealCell(i),n++*160));};$('claim-button').onclick=()=>{$('confirm-copy').textContent='你选中了：'+catalog.theme.expressions.filter(e=>selection.has(e.cell_index)).map(e=>e.label).join('、');$('confirm-dialog').showModal()};action('confirm-claim',async()=>{job=await api(`/generations/${job.id}/claim`,{cells:[...selection]});job=await api('/generations/'+job.id);$('confirm-dialog').close();renderResult();toast('这两种小心情，正式属于你啦。')});
async function download(name,share=false){if(!share){const link=node('a');link.href=API+`/files/${job.id}/${name}`;link.download=name;document.body.append(link);link.click();link.remove();return}const r=await fetch(API+`/files/${job.id}/${name}`,{credentials:'include'});if(!r.ok){let d=await r.json();throw new Error(d.error)}const blob=await r.blob();const file=new File([blob],name,{type:blob.type});if(share&&navigator.canShare?.({files:[file]})){try{await navigator.share({files:[file],title:'我的小心情'})}catch(e){if(e.name!=='AbortError')throw e}return}const url=URL.createObjectURL(blob),a=node('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000);if(share)toast('已下载透明图片，可从聊天软件选择文件发送。')}
action('zip-button',()=>download('stickers.zip'));action('grid-button',()=>download('grid.png'));action('demo-unlock',async()=>{job=await api('/demo/unlock/'+job.id,{});renderResult();toast('已解锁固定样例；没有产生付款。')});
async function checkout(product,generationId=null,orderId=null){
 if(!me.email){pendingUnlock={product,generationId,orderId};$('account-dialog').showModal();return}
 if(generationId&&catalog.order_workflow!=='work_bound_packs_v1')throw new Error('解锁服务更新中，请稍后刷新。');
 paymentStatus('正在准备安全结账…');
 try{
  const result=await api('/checkout',{product,generation_id:generationId,order_id:orderId});
  saved('emjo-order',result.order_id);await initPaddle();$('account-dialog').close();
  Paddle.Checkout.open({items:result.items,customData:result.customData,customer:result.customer,settings:{displayMode:'overlay',variant:'one-page',locale:document.documentElement.lang==='zh-CN'?'zh-Hans':'en'}});
  paymentStatus('结账窗口已打开；付款完成后会自动确认。');
 }catch(e){paymentStatus(e.message||'结账暂时无法启动，请稍后重试');if(e.status===409){$('account-dialog').showModal();refreshHistory()}throw e}
}
async function refreshHistory(){if(!me?.email)return;const email=me.email;try{const history=await api('/account/history');if(me?.email!==email)return;accountHistory={...history,email};renderHistory(history);renderEntitlements()}catch(e){if(me?.email!==email)return;$('work-list').replaceChildren(node('p','暂时无法读取作品记录，请稍后重试。','small muted'));$('order-list').replaceChildren(node('p','暂时无法读取订单记录，请稍后重试。','small muted'))}}
function renderHistory(history){
 const stateLabel={READY:'已制作完成',STYLE_READY:'等待选择风格',QUEUED:'等待制作',GENERATING:'制作中',PROCESSING:'整理贴纸',PREVIEW_QUEUED:'风格预览排队中',PREVIEW_GENERATING:'生成风格中',FAILED:'制作失败',EXPIRED:'已过期',CANCELLED:'已取消'};
 const orderLabel={PENDING:'待付款',PAID:'已付款',REFUNDED:'已退款',REFUND_REQUIRED:'需要人工处理'};
 const displayDate=stamp=>new Date(stamp*1000).toLocaleString('zh-CN',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'});
 $('work-list').replaceChildren();
 for(const item of history.jobs){
  const row=node('article',undefined,'history-row work-history-card'),copy=node('div',undefined,'history-copy');
  const thumb=node('div',undefined,'history-thumb');
  if(item.state==='READY'){const im=node('img');im.src=API+`/files/${item.id}/preview-1.jpg`;im.alt=`作品 #${shortId(item.id)} 的保护预览`;im.loading='lazy';thumb.append(im)}else thumb.append(node('span','✦'));
  const state=item.state!=='READY'?(stateLabel[item.state]||item.state):item.unlocked?'已解锁 · 1 套（9 张）':item.selected?.length?'已免费领取 2 张 · 整套待解锁':item.free?'可免费选 2 张 · 整套待解锁':'待解锁 · 1 套（9 张）';
  copy.append(node('strong',workTitle(item)),node('span',state,'work-state'),node('small',`${displayDate(item.created)}${item.style?' · '+(catalog.styles.find(s=>s.id===item.style)?.name||item.style):''}`));
  if(item.delivery_state==='SENT')copy.append(node('small','交付邮件已提交发送'));
  if(item.related_order_ids?.length)copy.append(node('small','关联订单 '+item.related_order_ids.map(id=>'#'+shortId(id)).join('、')));
  row.append(thumb,copy);
  const actions=node('div',undefined,'history-actions');
  const view=taskButton(item.state==='STYLE_READY'?'继续选画风':item.state==='READY'?(item.unlocked?'下载 / 分享':'查看并解锁'):'查看进度',()=>openWork(item.id));
  view.disabled=!['READY','STYLE_READY',...busyStates].includes(item.state);actions.append(view);row.append(actions);$('work-list').append(row);
 }
 if(!history.jobs.length)$('work-list').append(node('p','还没有关联到此邮箱的作品。','small muted'));
 $('order-list').replaceChildren();
 for(const item of history.orders){
  const row=node('article',undefined,'history-row order-history-card'),copy=node('div',undefined,'history-copy');
  const product=catalog.products.find(p=>p.id===item.product),entitlement=item.entitlement;
  const state=item.state==='PENDING'&&item.payment_state==='REVIEW'?'付款核验异常':item.state==='PENDING'&&item.payment_state==='CONFIRMING'?'付款确认中':orderLabel[item.state]||item.state;
  copy.append(node('strong',product?.name||item.product),node('span',state,'order-state'),node('small',`订单 #${shortId(item.id)} · ${displayDate(item.created)}`));
  const amount=orderAmount(item);
  if(amount&&['PAID','REFUNDED','REFUND_REQUIRED'].includes(item.state))copy.append(node('small',`${item.state==='REFUNDED'?'原实付':'实付'} ${amount}${item.amount===0?'（全额优惠）':''}`));
  else if(item.state==='PENDING'&&product)copy.append(node('small',priceLabel(product)));
  if(item.payment_review_required){const issue=item.payment_issues?.includes('duplicate_order_transaction')?'同一订单检测到额外付款，需要人工核对。请勿重复付款。':'这笔订单有付款需要人工核对。请勿重复付款。';copy.append(node('p',issue,'payment-issue'))}
  if(product?.packs&&entitlement){
   copy.append(node('span',`购买 ${entitlement.quantity} 套 · 已使用 ${entitlement.used} 套 · 剩余 ${entitlement.remaining} 套`,'order-entitlement'));
   if(entitlement.pending)copy.append(node('small',`另有 ${entitlement.pending} 套已预留，正在制作或等待选择画风。`));
   if(entitlement.revoked)copy.append(node('small','此订单的制作额度已撤回。'));
  }else if(product?.packs&&item.state==='PENDING')copy.append(node('small',`付款后获得 ${product.packs} 套制作额度，可分次使用。`));
  if(item.fulfillment==='ALREADY_UNLOCKED')copy.append(node('small','目标作品已解锁，本次购买的额度已全部存入账户，没有重复消耗。'));
  else if(item.generation_id)copy.append(node('small',`本单用于解锁作品 #${shortId(item.generation_id)} · 1 套（9 张）。`));
  else if(item.state==='PAID'&&product?.packs)copy.append(node('small',item.generation_ids?.length?'已用于下方作品，剩余额度可继续使用。':'制作额度已到账，从上方“我的作品”解锁，或新制作。'));
  if(!item.deliveries?.length&&item.delivery_state==='SENT')copy.append(node('small','交付邮件已提交发送'));
  const actions=node('div',undefined,'history-actions');
  if(item.payment_review_required)actions.append(taskButton('刷新核验状态',()=>refreshHistory()));
  else if(item.state==='PENDING'&&!item.payment_state)actions.append(taskButton('继续付款',()=>checkout(item.product,item.generation_id,item.id)));
  else if(item.state==='PENDING'){copy.append(node('small','请勿重复付款，正在核对状态。'));actions.append(taskButton('刷新状态',()=>refreshHistory()))}
  const ids=[...new Set([...(item.generation_ids||[]),...(item.generation_id?[item.generation_id]:[])])];
  const links=node('div',undefined,'order-work-links');
  for(const id of ids){const entry=node('div',undefined,'order-work-entry');entry.append(taskButton(`查看作品 #${shortId(id)}`,()=>openWork(id),'quiet order-work-link'));const delivery=item.deliveries?.find(d=>d.generation_id===id);if(delivery)entry.append(node('small',deliveryLabel(delivery)));links.append(entry)}
  if(!ids.length&&item.state==='PAID'&&product?.packs)actions.append(taskButton('选择作品 / 制作',()=>{$('work-list').scrollIntoView({behavior:'smooth',block:'start'});toast('打开一份待解锁作品使用额度，或关闭设置后开始新制作。')}));
  row.append(copy);if(links.childNodes.length)row.append(links);if(actions.childNodes.length)row.append(actions);$('order-list').append(row);
 }
 if(!history.orders.length)$('order-list').append(node('p','还没有订单记录。','small muted'));
}
action('unlock-button',()=>checkout('FIRST_PACK_UNLOCK',job.id));action('balance-unlock-button',unlockWithBalance);$('account-button').onclick=()=>{$('account-dialog').showModal();refreshHistory()};action('send-code',async()=>{const result=await api('/auth/code',{email:$('email-input').value});$('code-hint').textContent=result.demo_code?`本地样例验证码：${result.demo_code}（不会发送邮件）`:'验证码已发送，请检查收件箱和垃圾邮件。'});action('verify-code',async()=>{me=await api('/auth/verify',{email:$('email-input').value,code:$('code-input').value,referral:saved('emjo-ref')||null});renderMe();refreshHistory();toast('邮箱已验证');if(saved('emjo-order'))monitorPayment(saved('emjo-order'));if(pendingGeneration){const next=pendingGeneration==='start'?'mobile-start':'next-style';pendingGeneration=false;$('account-dialog').close();$(next).click();return}if(pendingUnlock){const next=pendingUnlock;pendingUnlock=false;$('account-dialog').close();await checkout(next.product,next.generationId,next.orderId)}});action('logout-button',async()=>{await api('/auth/logout',{});pendingGeneration=false;pendingUnlock=false;stopPayment();me=await api('/me');renderMe();$('account-dialog').close();if(job){job=null;show('maker');saved('emjo-job','')}});action('copy-invite',async()=>{const copied=await copyText(inviteURL(),$('invite-url'));toast(copied?'邀请链接已复制':'长按下方邀请链接，选择复制。')});action('withdraw-calibration',async()=>{await api(`/generations/${job.id}/calibration`,null,'DELETE');job.calibration=false;renderResult();toast('校准授权已撤回，校准副本已安排删除。')});$('privacy-button').onclick=()=>{renderPrivacy();$('privacy-dialog').showModal()};document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>$(b.dataset.close).close());
// Optional crop: the original remains the default. Crop only affects the first reference.
let cropImage,cropRatio=1,zoom=1,offset={x:0,y:0},drag;
const canvas=$('crop-canvas'),ctx=canvas.getContext('2d');
function drawCrop(){if(!cropImage)return;canvas.width=420;canvas.height=Math.round(420/cropRatio);const scale=Math.max(canvas.width/cropImage.width,canvas.height/cropImage.height)*zoom;const w=cropImage.width*scale,h=cropImage.height*scale;offset.x=Math.max(-(w-canvas.width)/2,Math.min((w-canvas.width)/2,offset.x));offset.y=Math.max(-(h-canvas.height)/2,Math.min((h-canvas.height)/2,offset.y));ctx.fillStyle='#fff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(cropImage,(canvas.width-w)/2+offset.x,(canvas.height-h)/2+offset.y,w,h);ctx.strokeStyle='#ffffff88';ctx.lineWidth=1;for(let i=1;i<3;i++){ctx.beginPath();ctx.moveTo(i*canvas.width/3,0);ctx.lineTo(i*canvas.width/3,canvas.height);ctx.stroke();ctx.beginPath();ctx.moveTo(0,i*canvas.height/3);ctx.lineTo(canvas.width,i*canvas.height/3);ctx.stroke()}}
action('crop-button',async()=>{cropImage?.close();cropImage=await createImageBitmap(photos[0]);zoom=1;offset={x:0,y:0};$('crop-zoom').value=1;drawCrop();$('crop-dialog').showModal()});document.querySelectorAll('[data-ratio]').forEach(b=>b.onclick=()=>{cropRatio=Number(b.dataset.ratio);zoom=1;offset={x:0,y:0};$('crop-zoom').value=1;document.querySelectorAll('[data-ratio]').forEach(x=>x.classList.toggle('active',x===b));drawCrop()});$('crop-zoom').oninput=e=>{zoom=Number(e.target.value);drawCrop()};canvas.onpointerdown=e=>{drag={x:e.clientX,y:e.clientY,ox:offset.x,oy:offset.y};canvas.setPointerCapture(e.pointerId)};canvas.onpointermove=e=>{if(!drag)return;const ratio=canvas.width/canvas.getBoundingClientRect().width;offset={x:drag.ox+(e.clientX-drag.x)*ratio,y:drag.oy+(e.clientY-drag.y)*ratio};drawCrop()};canvas.onpointerup=canvas.onpointercancel=()=>drag=null;
action('crop-save',async()=>{const out=document.createElement('canvas');out.width=1536;out.height=Math.round(1536/cropRatio);const c=out.getContext('2d'),scale=Math.max(canvas.width/cropImage.width,canvas.height/cropImage.height)*zoom,f=out.width/canvas.width;c.fillStyle='#fff';c.fillRect(0,0,out.width,out.height);c.drawImage(cropImage,((canvas.width-cropImage.width*scale)/2+offset.x)*f,((canvas.height-cropImage.height*scale)/2+offset.y)*f,cropImage.width*scale*f,cropImage.height*scale*f);cropBlob=await new Promise(r=>out.toBlob(r,'image/jpeg',.94));requestId=null;await renderPhotos();$('crop-dialog').close()});$('crop-reset').onclick=()=>{cropBlob=null;requestId=null;renderPhotos();$('crop-dialog').close()};for(const id of ['captions','accessories','calibration-consent'])$(id).onchange=()=>requestId=null;
init();

// Mobile H5 screens; a wide browser keeps the same phone-sized composition.
document.body.dataset.screen='home';
$('mobile-start').onclick=async()=>{if(!me?.email){pendingGeneration='start';$('account-dialog').showModal();return}if(['STYLE_READY','READY'].includes(job?.state)||busyStates.includes(job?.state)){await displayJob();return}makerStep('upload');show('maker');window.scrollTo({top:0,behavior:'instant'})};
$('mobile-back').onclick=()=>{if(document.body.dataset.screen==='home')return;$('hero').hidden=false;$('studio').hidden=true;document.body.dataset.screen='home';$('mobile-title').textContent='自助表情包生成器';window.scrollTo({top:0,behavior:'instant'})};

$('resume-result').onclick=async()=>{try{await displayJob();window.scrollTo({top:0,behavior:'instant'})}catch(e){toast(e.message)}};

function makerStep(step){$('maker').dataset.step=step;$('flow-upload').classList.toggle('active',step==='upload');$('flow-style').classList.toggle('active',step==='style');$('studio-title').textContent=step==='upload'?'上传你喜欢的照片':'选一种喜欢的画风';window.scrollTo({top:0,behavior:'instant'})}
action('back-upload',async()=>{await discardPreview();makerStep('upload');await renderPhotos()});
$('start-again').onclick=()=>{if(!me.trial_available&&!me.pack_balance){$('account-dialog').showModal();toast('这套作品已保留。购买制作次数后可做新的一套。');return}job=null;style=null;photos=[];cropBlob=null;requestId=null;saved('emjo-job','');renderStyles();makerStep('upload');show('maker');renderPhotos()};
$('review-styles').onclick=()=>{style=job.style;show('maker');makerStep('style');renderStyles();$('quota-copy').textContent='已保留当前九张表情'};
$('return-result').onclick=()=>{style=job.style;displayJob()};
async function saveFile(file){const url=URL.createObjectURL(file),a=node('a');a.href=url;a.download=file.name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),60000)}

function renderPrivacy(){const retained=catalog?.debug_retain_assets||job?.debug_retained;$('privacy-retention').textContent=retained?'生成图片（含未付款作品）暂不自动删除；后续计划保留约 30 天，清理规则启用后另行说明。原照片在制作完成后删除。':'原照片在制作完成或预览到期后删除；生成结果按下载窗口保留，到期后自动清理。';$('privacy-expiry').textContent=retained?'分享链接仍有独立有效期，可以重新生成。':job?.expires?`本套作品下载截止：${new Date(job.expires*1000).toLocaleString('zh-CN')}。`:''}
let shareCell=null,shareData=null,shareFile=null,shareRequest=0,sharePreviewURL=null;
function imageMime(bytes){const head=new Uint8Array(bytes,0,Math.min(bytes.byteLength,12));if(head.length>=8&&[137,80,78,71,13,10,26,10].every((v,i)=>head[i]===v))return 'image/png';const signature=String.fromCharCode(...head);if(signature.startsWith('GIF87a')||signature.startsWith('GIF89a'))return 'image/gif';if(signature.startsWith('RIFF')&&signature.slice(8,12)==='WEBP')return 'image/webp';throw new Error('下载文件不是有效图片，请刷新后重试')}
async function openShare(cell){shareCell=cell;$('share-dialog').showModal();await prepareShare()}
async function prepareShare(){
 const request=++shareRequest;shareData=null;shareFile=null;
 for(const id of ['copy-share','native-share','whatsapp-share','save-share','save-archive'])$(id).disabled=true;
 $('share-preview').hidden=true;$('share-file-info').textContent='';
 if(sharePreviewURL){URL.revokeObjectURL(sharePreviewURL);sharePreviewURL=null}
 $('share-status').textContent='正在准备透明单张…';
 try{
  const variant=$('share-format').value;
  const data=await api(`/generations/${job.id}/share`,{cell:shareCell,variant});
  const response=await fetch(API+`/files/${job.id}/${data.name}`,{credentials:'include',cache:'no-store'});if(!response.ok)throw new Error('贴纸已失效，请刷新作品');
  const bytes=await response.arrayBuffer();if(request!==shareRequest)return;
  const mime=imageMime(bytes),file=new File([bytes],data.name,{type:mime});
  if(data.sha256&&crypto.subtle){const digest=await crypto.subtle.digest('SHA-256',bytes);const hash=[...new Uint8Array(digest)].map(v=>v.toString(16).padStart(2,'0')).join('');if(hash!==data.sha256)throw new Error('下载文件与原文件不一致，请重新打开')}
  const previewURL=URL.createObjectURL(file),image=new Image();image.src=previewURL;
  try{await image.decode();if(request!==shareRequest){URL.revokeObjectURL(previewURL);return}const check=document.createElement('canvas');check.width=image.naturalWidth;check.height=image.naturalHeight;const context=check.getContext('2d',{willReadFrequently:true});context.drawImage(image,0,0);const pixels=context.getImageData(0,0,check.width,check.height).data;let transparent=false;for(let i=3;i<pixels.length;i+=4)if(pixels[i]===0){transparent=true;break}if(!transparent)throw new Error('这张文件未检测到全透明像素，已暂停下载；请联系站点修复');$('share-file-info').textContent=`${mime.split('/')[1].toUpperCase()} · ${check.width}×${check.height} · 含透明像素`;}catch(e){URL.revokeObjectURL(previewURL);throw e}
  shareData=data;shareFile=file;sharePreviewURL=previewURL;$('share-image').src=previewURL;$('share-preview').hidden=false;
  $('share-status').textContent=data.local_only?'本地测试链接：仅本机可访问，正式部署后才能发给朋友。':`持链接者可下载这张贴纸；有效至 ${new Date(data.expires*1000).toLocaleString('zh-CN')}。`;
  $('share-url').value=data.url;
  for(const id of ['copy-share','native-share','save-share'])$(id).disabled=false;
  $('save-archive').disabled=!data.archive_url;
  $('whatsapp-share').disabled=data.local_only;
 }catch(e){if(request===shareRequest)$('share-status').textContent=e.message}
}
$('share-format').onchange=prepareShare;
document.querySelectorAll('[name=share-background]').forEach(input=>input.onchange=()=>{$('share-preview').dataset.background=input.value});
action('save-archive',async()=>{const data=shareData;if(!data?.archive_url)return;const response=await fetch(data.archive_url,{credentials:'include',cache:'no-store'});if(!response.ok)throw new Error('原文件暂时无法下载，请重新打开贴纸');await saveFile(new File([await response.blob()],data.name+'.zip',{type:'application/zip'}))});
action('copy-share',async()=>{if(!shareData)return;const copied=await copyText(shareData.url,$('share-url'));toast(copied?'分享链接已复制':'长按下方分享链接，选择复制。')});
action('save-share',async()=>{if(shareFile)await saveFile(shareFile)});
$('native-share').onclick=async()=>{try{if(!shareFile)return;if(navigator.canShare?.({files:[shareFile]}))await navigator.share({files:[shareFile],title:'送你一张小表情'});else{await saveFile(shareFile);toast('此浏览器不支持文件分享，已下载单张文件。')}}catch(e){if(e.name!=='AbortError')toast('系统分享未完成，可下载后发送')}};
$('whatsapp-share').onclick=()=>{if(!shareData||shareData.local_only)return;window.open('https://wa.me/?text='+encodeURIComponent('送你一张小表情：'+shareData.url),'_blank','noopener,noreferrer')};
