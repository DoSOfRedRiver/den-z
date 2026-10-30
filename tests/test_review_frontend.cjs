const assert=require('node:assert/strict');
const fs=require('node:fs');
const {JSDOM}=require('jsdom');
const html=fs.readFileSync('docs/lessons/2026-10-28.html','utf8');
const example={id:2,lesson_id:'2026-10-28',answers:{},choice_score:9,choice_total:9,
 open_status:'reviewed',open_score:3,open_total:8,overall_percent:53.13,
 review_feedback:'Восстановление: опиши стабильный ключ провайдера. Неизвестный исход нельзя считать отказом.',
 open_scores:{q10:[2,4],q11:[1,4]}};
const dom=new JSDOM(html,{url:'https://study.example/lessons/2026-10-28.html#key=test-owner',runScripts:'dangerously',beforeParse(w){w.fetch=async()=>({ok:true,json:async()=>({submissions:[example]})})}});
setTimeout(()=>{
 try{
  const history=dom.window.document.querySelector('#history-list');
  assert.match(history.textContent,/открытый ответ: 3\/8/);
  assert.match(history.textContent,/итог: 53[,.]13%/);
  assert.match(history.textContent,/стабильный ключ провайдера/);
  assert.equal(history.querySelector('img'),null);
  console.log('PASS reviewed score and feedback visible in authorized history');
 }catch(e){console.error(e);process.exitCode=1}
},40);
