const {JSDOM} = require('jsdom');
const fs=require('fs'); const assert=require('node:assert/strict');
const path=require('path');
const {execFileSync}=require('child_process');
const html=execFileSync(process.env.UI_PYTHON || 'python', [path.join(__dirname, 'render_ui.py')], {encoding:'utf8'});
const main=fs.readFileSync(path.join(__dirname,'../static/js/main.js'),'utf8');
const code=fs.readFileSync(path.join(__dirname,'../static/js/enhancements.js'),'utf8');
let count=0;
async function create(settings={}){
 const dom=new JSDOM(html,{url:'https://financeiro.example/dashboard',runScripts:'outside-only',pretendToBeVisual:true});
 const w=dom.window; const errors=[];w.addEventListener('error',e=>errors.push(e.error));
 if(w.document.readyState==='loading') await new Promise(r=>w.document.addEventListener('DOMContentLoaded',r,{once:true}));
 const timers=[];w.setTimeout=(fn,delay)=>{timers.push({fn,delay});return timers.length;};w.clearTimeout=()=>{};w.setInterval=()=>1;w.clearInterval=()=>{};
 w.matchMedia=()=>({matches:!!settings.standalone,addEventListener(){}});
 if(settings.installed)w.localStorage.setItem('finance-installed','1');
 w.localStorage.setItem('finance-cursor-2','0');
 w.navigator.serviceWorker={register:async()=>({})};w.isSecureContext=true;
 w.sources=[];w.EventSource=class{constructor(url){this.url=url;this.events={};w.sources.push(this);} addEventListener(key,fn){this.events[key]=fn;}close(){this.closed=true;}};
 w.beepCount=0;
 w.AudioContext=class{constructor(){this.state='suspended';this.currentTime=0;this.destination={};}async resume(){this.state='running';}createOscillator(){return {connect(){},frequency:{setValueAtTime(){}},start(){w.beepCount++;},stop(){}};}createGain(){return {connect(){},gain:{setValueAtTime(){},exponentialRampToValueAtTime(){}}};}};
 w.fetch=async(url)=>({ok:true,status:200,redirected:false,json:async()=>({events:[]}),text:async()=>html.replace('R$ 0,00','R$ 1.234,56')});
 w.eval(main);w.document.dispatchEvent(new w.Event('DOMContentLoaded'));w.eval(code);
 return {dom,w,timers,errors};
}
(async()=>{
 let x=await create(),{w,timers}=x;
 assert.equal(w.sources.length,1);w.sources[0].onopen();assert.equal(w.document.querySelector('#connection-status').textContent,'Conectado');count++;
 const sound=w.document.querySelector('#sound-toggle');sound.click();await new Promise(setImmediate);assert.equal(sound.getAttribute('aria-pressed'),'true');assert.equal(w.beepCount,1);count++;
 const event={id:1,actor_id:1,message:'Ana adicionou uma despesa.',kind:'add_expense'};
 w.sources[0].events.change({data:JSON.stringify(event)});assert.equal(w.document.querySelectorAll('.finance-toast').length,1);assert.equal(w.beepCount,2);count++;
 w.sources[0].events.change({data:JSON.stringify(event)});assert.equal(w.document.querySelectorAll('.finance-toast').length,1);assert.equal(w.beepCount,2);count++;
 await timers.find(t=>t.delay===700).fn();assert.match(w.document.querySelector('.home-stats').textContent,/1\.234,56/);count++;
 w.sources[0].events.change({data:JSON.stringify({...event,id:2,actor_id:2})});assert.equal(w.beepCount,2);count++;
 // XSS in notification content remains inert plain text.
 w.financeToast('<img src=x onerror=alert(1)>');assert.equal(w.document.querySelectorAll('#toast-region img').length,0);count++;
 w.dispatchEvent(new w.Event('beforeinstallprompt',{cancelable:true}));assert.equal(w.document.querySelector('#install-banner').hidden,false);count++;
 w.dispatchEvent(new w.Event('appinstalled'));assert.equal(w.document.querySelector('#install-banner').hidden,true);assert.equal(w.localStorage.getItem('finance-installed'),'1');count++;
 w.dispatchEvent(new w.Event('beforeinstallprompt',{cancelable:true}));assert.equal(w.document.querySelector('#install-banner').hidden,true);count++;
 assert.equal(x.errors.length,0);w.close();
 x=await create({installed:true});x.w.dispatchEvent(new x.w.Event('beforeinstallprompt',{cancelable:true}));assert.equal(x.w.document.querySelector('#install-banner').hidden,true);count++;x.w.close();
 x=await create({standalone:true});assert.equal(x.w.localStorage.getItem('finance-installed'),'1');count++;x.w.close();
 x=await create();x.w.sources[0].onerror();await Promise.resolve();await Promise.resolve();assert.equal(x.w.sources[0].closed,true);count++;x.w.close();
 console.log(`${count} verificações de interface simulada aprovadas.`);
})().catch(e=>{console.error(e);process.exit(1);});
