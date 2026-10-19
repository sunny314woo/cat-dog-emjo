const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../app.js'), 'utf8');
const monitor = source.slice(source.indexOf('let paddleReady,'), source.indexOf('function initPaddle()'));
const paddleInit = source.slice(source.indexOf('function initPaddle()'), source.indexOf('async function addPhotos'));
const checkout = source.slice(source.indexOf('async function checkout('), source.indexOf('async function refreshHistory()'));

function page(responses, storage = new Map([['emjo-order', 'order-1']])) {
  const status = {textContent: '', hidden: true};
  const timers = [];
  const calls = [];
  const context = vm.createContext({
    $: () => status,
    saved: (key, value) => value === undefined ? storage.get(key) : storage.set(key, value),
    setTimeout: callback => { timers.push(callback); return timers.length; },
    clearTimeout: () => {},
    api: async path => {
      calls.push(path);
      if (path === '/me') return {email: 'buyer@example.com', pack_balance: 3};
      if (path.startsWith('/generations/')) return {id: 'generation-1', unlocked: true};
      const response = responses.shift();
      if (response instanceof Error) throw response;
      return response;
    },
    renderMe: () => {}, refreshHistory: () => {}, restoreResult: () => {}, show: () => {}, renderResult: () => {}, toast: () => {},
  });
  vm.runInContext("let me={email:'buyer@example.com'},job;" + monitor, context);
  const settle = () => new Promise(resolve => setImmediate(resolve));
  return {status, storage, calls, timers, context, settle};
}

test('payment confirmation after more than 20 seconds still unlocks and follows mail retries', async () => {
  const pending = Array.from({length: 25}, () => ({state: 'PENDING'}));
  const paid = {state: 'PAID', generation_id: 'generation-1'};
  const p = page([...pending, {...paid, delivery_state: 'FAILED', delivery_attempts: 1}, {...paid, delivery_state: 'SENT'}]);
  vm.runInContext("monitorPayment('order-1')", p.context);
  await p.settle();
  for (let i = 0; i < 25; i++) { p.timers.shift()(); await p.settle(); }
  assert.match(p.status.textContent, /邮件暂未发送成功/);
  assert.equal(p.storage.get('emjo-job'), 'generation-1');
  assert.equal(p.storage.get('emjo-order'), 'order-1');
  p.timers.shift()(); await p.settle();
  assert.match(p.status.textContent, /邮件已提交发送/);
  assert.equal(p.storage.get('emjo-order'), '');
  assert.equal(p.calls.filter(path => path.startsWith('/generations/')).length, 1);
});

test('a refreshed page can confirm the persisted order and restore purchased credits', async () => {
  const storage = new Map([['emjo-order', 'order-1']]);
  const before = page([{state: 'PENDING'}], storage);
  vm.runInContext("monitorPayment('order-1')", before.context); await before.settle();
  const after = page([{state: 'PAID', generation_id: null}], storage);
  vm.runInContext("monitorPayment(saved('emjo-order'))", after.context); await after.settle();
  assert.match(after.status.textContent, /制作次数已到账/);
  assert.equal(storage.get('emjo-order'), '');
  assert.ok(after.calls.includes('/me'));
});

test('logout cancels an in-flight response before private order details render', async () => {
  const p = page([]); let complete;
  p.context.api = () => new Promise(resolve => { complete = resolve; });
  vm.runInContext("monitorPayment('order-1');stopPayment();", p.context);
  complete({state: 'PAID', generation_id: 'generation-1', delivery_state: 'SENT'});
  await p.settle();
  assert.equal(p.status.textContent, '');
  assert.equal(p.timers.length, 0);
  assert.equal(p.storage.get('emjo-job'), undefined);
});

test('Paddle initialization failures reject visibly and can be retried', async () => {
  let script;
  const context = vm.createContext({
    catalog: {paddle: {clientToken: 'test-token', environment: 'live'}},
    window: {},
    document: {createElement: () => (script = {}), head: {append: item => { script = item; }}},
    paymentStatus: () => {}, saved: () => '', monitorPayment: () => {},
    Error, Promise,
  });
  vm.runInContext('let paddleReady;' + paddleInit, context);
  const pending = vm.runInContext('initPaddle()', context);
  script.onload();
  await assert.rejects(pending, /支付组件没有正确加载/);
  assert.equal(vm.runInContext('paddleReady', context), null);
});

test('checkout errors retain a visible recovery message', () => {
  assert.match(source, /paymentStatus\(e\.message\|\|'结账暂时无法启动，请稍后重试'\)/);
  assert.match(source, /e\.status===409\)\{\$\('account-dialog'\)\.showModal\(\);refreshHistory\(\)\}/);
});

test('payment review stops checkout polling and visibly warns against duplicate payment', async () => {
  const p=page([{state:'PENDING',payment_state:'REVIEW'}]);
  vm.runInContext("monitorPayment('order-1')",p.context);await p.settle();
  assert.match(p.status.textContent,/付款核验异常/);
  assert.match(p.status.textContent,/请勿重复付款/);
  assert.equal(p.timers.length,0);
});

test('an extra charge on a paid order remains a visible review issue', async () => {
  const p=page([{state:'PAID',generation_id:'generation-1',payment_review_required:true,payment_issues:['duplicate_order_transaction']}]);
  vm.runInContext("monitorPayment('order-1')",p.context);await p.settle();
  assert.match(p.status.textContent,/额外付款需要人工核对/);
  assert.match(p.status.textContent,/请勿重复付款/);
  assert.equal(p.storage.get('emjo-order'),'');
  assert.equal(p.storage.get('emjo-job'),undefined);
  assert.equal(p.timers.length,0);
});

test('an already unlocked target reports retained quota instead of another consumption', async () => {
  const p=page([{state:'PAID',generation_id:'generation-1',fulfillment:'ALREADY_UNLOCKED',delivery_state:'SENT'}]);
  vm.runInContext("monitorPayment('order-1')",p.context);await p.settle();
  assert.match(p.status.textContent,/购买额度已全部存入账户/);
  assert.match(p.status.textContent,/没有重复消耗/);
  assert.equal(p.storage.get('emjo-order'),'');
});

function checkoutPage(workflow){
  const calls=[];
  const context=vm.createContext({
    me:{email:'buyer@example.com'},catalog:{order_workflow:workflow},
    api:async(path,body)=>{calls.push({path,body});return {order_id:'order-1',items:[],customData:{},customer:{}}},
    $:()=>({close:()=>{},showModal:()=>{}}),saved:()=>{},initPaddle:async()=>{},
    Paddle:{Checkout:{open:()=>{}}},paymentStatus:()=>{},refreshHistory:()=>{},
    document:{documentElement:{lang:'zh-CN'}},
  });
  vm.runInContext(checkout,context);
  return {calls,context};
}

test('work-bound purchases are blocked before sending to an older backend', async()=>{
  const p=checkoutPage(undefined);
  await assert.rejects(vm.runInContext("checkout('PACK_3','work-1')",p.context),/解锁服务更新中/);
  assert.equal(p.calls.length,0);
});

test('work-bound purchases keep the explicit target while account top-ups have none', async()=>{
  const p=checkoutPage('work_bound_packs_v1');
  await vm.runInContext("checkout('PACK_3','work-1')",p.context);
  await vm.runInContext("checkout('PACK_1')",p.context);
  assert.equal(p.calls[0].body.generation_id,'work-1');
  assert.equal(p.calls[1].body.generation_id,null);
  assert.equal(p.calls[0].body.product,'PACK_3');
  assert.equal(p.calls[1].body.product,'PACK_1');
});
