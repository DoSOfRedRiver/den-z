const assert = require('node:assert/strict');
const fs = require('node:fs');
const {JSDOM} = require('jsdom');

const html = fs.readFileSync('docs/lessons/2026-10-29.html', 'utf8');
const render = source => new JSDOM(source, {url:'https://study.example/lessons/2026-10-29.html', runScripts:'dangerously'}).window.document;
const current = render(html);
const flows = current.querySelectorAll('.reading figure.diagram svg');
assert(flows.length >= 2, 'existing flow blocks should render as connected diagrams');
for (const svg of flows) {
  assert(svg.querySelectorAll('path.diagram-edge').length >= 1, 'diagram has visible arrows');
  assert(svg.querySelectorAll('rect.diagram-node').length >= 2, 'diagram has shaped nodes');
  assert(svg.getAttribute('viewBox'), 'diagram has responsive SVG dimensions');
}
assert(current.querySelector('.reading figure.diagram figcaption')?.textContent, 'diagram has a caption');

const source = JSON.parse(current.querySelector('#lesson-data').textContent);
source.sections[0].blocks.push({type:'diagram', caption:'Развилка записи', nodes:[
  {id:'start',label:'Начало',x:0,y:0},
  {id:'check',label:'Есть запись?',x:0,y:1,kind:'decision'},
  {id:'yes',label:'Читать результат',x:-1,y:2},
  {id:'no',label:'Создать запись',x:1,y:2}
],edges:[{from:'start',to:'check'},{from:'check',to:'yes',label:'да'},{from:'check',to:'no',label:'нет'}]});
const fixture = html.replace(/(<script id="lesson-data" type="application\/json">)(.*?)(<\/script>)/s, (_,open,_json,close) => open+JSON.stringify(source).replaceAll('<','\\u003c')+close);
const branched = render(fixture);
const svg = [...branched.querySelectorAll('.reading figure.diagram')].find(f=>f.querySelector('figcaption')?.textContent==='Развилка записи')?.querySelector('svg');
assert(svg, 'explicit diagram block rendered');
assert.equal(svg.querySelectorAll('path.diagram-edge').length, 3);
assert.equal(svg.querySelectorAll('rect.diagram-node').length, 4);
assert(svg.textContent.includes('да') && svg.textContent.includes('нет'), 'edges retain branch labels');
assert(svg.textContent.includes('Есть') && svg.textContent.includes('запись?'), 'decision node text rendered');
assert.equal(svg.querySelector('img'),null,'labels remain text, not HTML');
console.log('PASS connected flow and branching diagrams');
