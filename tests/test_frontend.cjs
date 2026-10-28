const fs=require('node:fs');const assert=require('node:assert/strict');const {JSDOM}=require('jsdom');
const html=fs.readFileSync('docs/index.html','utf8');
const lesson=JSON.parse(html.match(/<script id="lesson-data" type="application\/json">([^<]*)<\/script>/)[1]);
let calls=[];
const dom=new JSDOM(html,{url:'https://study.example/#key=private-owner-key',runScripts:'dangerously',beforeParse(win){
  win.scrollTo=()=>{};
  win.fetch=async (url,opts={})=>{calls.push({url,opts});return {ok:true,status:url==='/api/submissions'?201:200,json:async()=>url==='/api/submissions'?{choice_score:3,choice_total:3,open_status:'pending'}:{submissions:[]}}};
}});
const d=dom.window.document;
assert.equal(dom.window.location.hash,'','secret fragment must be scrubbed');
assert.equal(dom.window.localStorage.getItem('den-z-owner-key'),'private-owner-key');
d.querySelector('#start-quiz').click();
for(const q of lesson.questions){if(q.type==='choice')d.querySelector(`input[name=${q.id}][value='${q.answer}']`).checked=true;else d.querySelector(`textarea[name=${q.id}]`).value='Сначала ограничить новые записи'}
d.querySelector('#form').dispatchEvent(new dom.window.Event('submit',{bubbles:true,cancelable:true}));
const save=d.querySelector('#save-server');assert(save,'save action exists');save.click();
setTimeout(()=>{
 try{const call=calls.find(x=>x.url==='/api/submissions');assert(call,'POST was sent');assert.equal(call.opts.headers.Authorization,'Bearer private-owner-key');assert.equal(JSON.parse(call.opts.body).lesson_id,lesson.id);assert.match(d.querySelector('#server-status').textContent,/сохран/);console.log('PASS: owner link, submission and confirmation')}catch(e){console.error(e);process.exitCode=1}
},30);
