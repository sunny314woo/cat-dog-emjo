const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(require('node:path').join(__dirname, '../app.js'), 'utf8');
const monitor = source.slice(source.indexOf('let paddleReady,'), source.indexOf('function initPaddle()'));

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
    renderMe: () => {}, restoreResult: () => {}, show: () => {}, renderResult: () => {}, toast: () => {},
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
