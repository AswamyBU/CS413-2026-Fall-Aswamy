// Run with node tests/browser-runtime.cjs. Python 3.12+ enables parity checks.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {Worker} = require('node:worker_threads');
const root = path.resolve(__dirname, '..');
require(path.join(root, 'static/runtime.js'));
require(path.join(root, 'static/examples.js'));
const {perform} = globalThis.LambdaRuntime;
const cases = [
 ['D0Eop2("/", D0Eint(-7), D0Eint(3))','D0Vint(arg1=-3)'],
 ['D0Eop2("/", D0Eint(7), D0Eint(-3))','D0Vint(arg1=-3)'],
 ['D0Eop2("*", D0Eint(9007199254740993), D0Eint(3))','D0Vint(arg1=27021597764222979)'],
 ['D0Elet("x",D0Eint(7),D0Elet("f",D0Elam("y",D0Eop2("+",D0Evar("x"),D0Evar("y"))),D0Elet("x",D0Eint(99),D0Eapp(D0Evar("f"),D0Eint(2)))))','D0Vint(arg1=9)'],
 ['D0Epsnd(D0Epair(D0Eint(1),D0Ebtf(True)))','D0Vbtf(arg1=True)'],
 ['D0Eif0(D0Ebtf(False),D0Eop2("/",D0Eint(1),D0Eint(0)),D0Eint(42))','D0Vint(arg1=42)'],
 ["# comment\nD0Elet('x', D0Eint(-0x10), D0Evar('x'),)",'D0Vint(arg1=-16)'],
];
for(const [src,expected] of cases) assert.deepEqual(perform('interpret',src),{outcome:'success',text:expected});
for(const [name,expected] of [['Factorial','120'],['Fibonacci','55'],['Arithmetic','42']]) assert.equal(perform('interpret',LambdaExamples[name]).text,`D0Vint(arg1=${expected})`);
for(const name of Object.keys(LambdaExamples)) assert.equal(LambdaExamples[name],fs.readFileSync(path.join(root,'examples',name+'.lambda'),'utf8'));
assert.equal(perform('lint','D0Elet("x",D0Evar("x"),D0Elam("y",D0Epair(D0Evar("y"),D0Evar("z"))))').text,'Undeclared variables: x, z');
for(const src of ['__import__("os")','D0Eint(1); alert(1)','D0Eint(True)','D0Eint(1,2)','D0Eint(arg1=1)','D0E000()','D0Eint(1).arg1','D0Eint(1)'+' '.repeat(65536)]) assert.equal(perform('interpret',src).outcome,'input_error',src.slice(0,50));
for(const src of ['D0Evar("missing")','D0Epair(D0Eint(1),D0Evar("missing"))','D0Eif0(D0Eint(1),D0Eint(2),D0Eint(3))','D0Eop2("/",D0Eint(1),D0Eint(0))']) assert.equal(perform('interpret',src).outcome,'runtime_error');
for(const op of ['typecheck','compile'])assert.equal(perform(op,'').outcome,'not_implemented');
console.log('JavaScript runtime assertions passed.');
// Compare observable results with the original Python implementation.
for(const src of [...cases.map(c=>c[0]),...Object.values(LambdaExamples), 'D0Elam("x",D0Eop2("+",D0Evar("x"),D0Eint(1)))']) for(const op of ['lint','interpret']) {
 const py=spawnSync('python3',[path.join(root,'backend.py'),op],{input:src,encoding:'utf8',timeout:5000});
 assert.equal(py.status,0,py.stderr);
 const expected=JSON.parse(py.stdout),actual=perform(op,src);
 assert.equal(actual.outcome,expected.outcome);
 if(['success','language_error'].includes(expected.outcome))assert.equal(actual.text,expected.text);
}
console.log('Python parity checks passed.');
// Exercise the actual classic worker script with a Web Worker-compatible bridge.
async function workerTest() {
 const worker = new Worker(`const {parentPort}=require('node:worker_threads');global.self=global;global.importScripts=p=>require(${JSON.stringify(path.join(root,'static'))}+'/'+p);global.postMessage=v=>parentPort.postMessage(v);${globalThis.LambdaWorkerSource};parentPort.on('message',data=>self.onmessage({data}));`,{eval:true});
 try { const result=await new Promise((resolve,reject)=>{worker.once('message',resolve);worker.once('error',reject);worker.postMessage({operation:'interpret',source:LambdaExamples.Factorial});});assert.equal(result.text,'D0Vint(arg1=120)'); } finally {await worker.terminate();}
}
async function controllerTest() {
 const vm=require('node:vm');
 const source=fs.readFileSync(path.join(root,'static/app.js'),'utf8');
 let timerCallback, terminated=false, cleared=false;
 const sandbox={state:{source:'',name:'Untitled',revision:0,results:[]}, bytes:s=>new TextEncoder().encode(s).length, workerURL:'worker.js', LambdaExamples,
  Worker:class {postMessage(){} terminate(){terminated=true;}},
  setTimeout:fn=>{timerCallback=fn;return 1;},clearTimeout:()=>{cleared=true;}};
 vm.createContext(sandbox);
 vm.runInContext(source.slice(source.indexOf('function runWorker('),source.indexOf('async function work(')),sandbox);
 const pending=sandbox.runWorker('interpret','D0Eint(1)');timerCallback();
 assert.equal((await pending).outcome,'backend_error');assert.ok(terminated&&cleared);
 await assert.rejects(sandbox.api('/api/action',{operation:'lint'}),/Apply source/);
 await assert.rejects(sandbox.api('/api/source',{source:'   '}),/empty/);
 await assert.rejects(sandbox.api('/api/source',{source:'a'.repeat(65537)}),/limit/);
 sandbox.state=await sandbox.api('/api/source',{source:'D0Eint(42)',name:'example'});
 assert.equal(sandbox.state.revision,1);
 sandbox.runWorker=async(op,src)=>perform(op,src);
 sandbox.state=await sandbox.api('/api/action',{operation:'interpret'});
 assert.equal(sandbox.state.results[0].text,'D0Vint(arg1=42)');
 const next=await sandbox.api('/api/source',{source:'D0Eint(7)',name:'next'});
 assert.equal(next.results.length,0);assert.equal(next.revision,2);
}
Promise.all([workerTest(),controllerTest()]).then(()=>console.log('Runtime, examples, input validation, Python parity, worker, timeout, and controller checks passed.')).catch(e=>{console.error(e);process.exitCode=1;});
