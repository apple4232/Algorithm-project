'use strict';
const $ = id => document.getElementById(id);
const algorithms = ['given','nn','exhaustive','dp','ca-plus','ca-minus','nn+2opt','ca-plus+2opt','ca-minus+2opt'];
const labels = {'given':'입력 순서','nn':'NN','exhaustive':'완전 탐색','dp':'DP','ca-plus':'CA-plus','ca-minus':'CA-minus','nn+2opt':'NN + 2-opt','ca-plus+2opt':'CA-plus + 2-opt','ca-minus+2opt':'CA-minus + 2-opt'};
const patterns = {'clustered':'군집형','random-stow-like':'Random-Stow-like','directional':'방향형','paired-far':'반사 쌍 · 원거리','paired-near':'반사 쌍 · 근거리'};
const statuses = {'completed':'완료','timeout':'시간 초과','resource_limit':'자원 제한','error':'오류','invalid_input':'입력 오류','infeasible':'경로 없음'};
const terms = {'completed':'완료','local_optimum':'지역 최적점','evaluation_limit':'평가 횟수 제한','deadline':'시간 제한','dp_size':'DP 위치 수 제한','exhaustive_size':'완전 탐색 위치 수 제한','dp_memory_estimate':'DP 메모리 추정 제한','allocation_failed':'메모리 할당 실패'};
const scenarios = {
 A:['정확성','작은 작업에서 완전 탐색과 DP의 결과를 비교합니다.',3,'clustered','exhaustive','dp'],
 B:['계산 규모','위치 수에 따라 DP의 시간과 완료 상태를 확인합니다.',15,'random-stow-like','dp','nn+2opt'],
 C:['큰 작업','큰 작업에서 빠른 방법들의 경로와 비용을 비교합니다.',50,'random-stow-like','nn','nn+2opt'],
 D:['군집 배치','인접한 통로에 모인 물건에서 경로 개선 효과를 살펴봅니다.',10,'clustered','nn','nn+2opt'],
 E:['분산도','물건 사이의 실제 평균 통로 거리와 경로 개선을 살펴봅니다.',10,'random-stow-like','nn','nn+2opt'],
 F:['도착점 관계','같은 위치 구조를 좌우로 반사한 작업을 비교합니다. 출발점까지 거리도 함께 변합니다.',10,'paired-far','nn','nn'],
 G:['방향·패턴','창고 뒤쪽에 배치된 물건에서 컨베이어 고려 방법을 비교합니다.',10,'directional','nn','ca-minus'],
 H:['출발점 변경','같은 물건 집합에서 출발점만 바꿔 비교합니다.',10,'clustered','nn','nn']
};
let tasks = [], scenario = 'A', current = null, other = null, live = null, playing = false, frame = null, lastTime = 0, mapPaths = [], refreshToken = 0;
const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = (v, digits=2) => v == null || !Number.isFinite(v) ? '—' : Number(v).toFixed(digits);
const time = v => v == null ? '—' : `${fmt(v*1000,3)} ms`;
async function api(url, options) { const r = await fetch(url, options); let data; try { data = await r.json(); } catch { throw new Error('서버 응답을 읽지 못했습니다.'); } if (!r.ok) throw new Error(data.error || '요청을 처리하지 못했습니다.'); return data; }
function error(message) { $('error').hidden = !message; $('error').textContent = message || ''; }
function option(value, label) { const o = document.createElement('option'); o.value = value; o.textContent = label; return o; }
function setOptions(select, entries, selected) { select.replaceChildren(...entries.map(([v,l]) => option(String(v),l))); if ([...select.options].some(o => o.value === String(selected))) select.value = String(selected); }
function taskLabel(t) { return `${t.id}  ·  ${patterns[t.pattern] || t.pattern}`; }
function getFilters() { return Object.fromEntries(['split','n','pattern','start','seed'].map(k => [k,$(k).value])); }
function filtered() { const f=getFilters(); return tasks.filter(t => (!f.split || t.split===f.split) && (!f.n || t.required.length===Number(f.n)) && (!f.pattern || t.pattern===f.pattern) && (!f.start || t.id.split(':')[3]===f.start) && (!f.seed || String(t.seed)===f.seed)); }
function updateTaskOptions(preferred) {
 const list=filtered(); setOptions($('task'), list.map(t=>[t.id,taskLabel(t)]), preferred);
 $('task-count').textContent = `${list.length.toLocaleString()}개 작업 일치`;
 $('split-note').textContent = $('split').value === 'dev' ? '개발 데이터: 규칙 생성에 사용됨' : '평가 데이터: 규칙 고정 후 사용됨';
 $('run').disabled = !list.length;
 if (!list.length) { refreshToken++; current=other=null; $('map-a').textContent=$('map-b').textContent='조건에 맞는 작업이 없습니다.'; $('results').replaceChildren(); $('task-info').textContent=''; return; }
 loadDetail();
}
async function aggregate() {
 const qs = new URLSearchParams({...getFilters(),mode:$('mode').value});
 try { const rows=await api('/api/aggregate?'+qs); $('aggregate').innerHTML=rows.map(r=>`<tr><td>${escapeHtml(labels[r.algorithm])}</td><td class="num">${r.attempts}</td><td class="num">${r.completed} / ${r.attempts}</td><td>${escapeHtml(Object.entries(r.statuses).filter(([s])=>s!=='completed').map(([s,n])=>`${statuses[s]||s} ${n}`).join(' · ') || '—')}</td><td class="num">${r.median_distance==null?'—':fmt(r.median_distance,1)+' m'}</td><td class="num">${time(r.median_seconds)}</td></tr>`).join(''); } catch(e) { error(e.message); }
}
function setScenario(key) {
 scenario=key; const s=scenarios[key];
 for(const button of $('scenarios').children) { const active=button.dataset.key===key; button.classList.toggle('active',active); button.setAttribute('aria-pressed',String(active)); }
 $('scenario-description').textContent=s[1]; $('n').value=String(s[2]); $('pattern').value=s[3]; $('start').value='0'; $('algorithm-a').value=s[4]; $('algorithm-b').value=s[5];
 live=null; updateTaskOptions(); aggregate();
}
async function loadDetail() {
 const id=$('task').value; if(!id)return;
 const token=++refreshToken; live=null; $('restore').hidden=true; $('live-note').textContent=''; stop();
 try {
   const mode=$('mode').value; const data=await api(`/api/detail?id=${encodeURIComponent(id)}&mode=${mode}`);
   let paired=null; const pairId=scenario==='F'?data.pair_f:scenario==='H'?data.pair_h:null;
   if(pairId) { try { paired=await api(`/api/detail?id=${encodeURIComponent(pairId)}&mode=${mode}`); } catch { paired=null; } }
   if(token!==refreshToken)return; current=data; other=paired; error('');
   $('comparison-note').hidden=!(scenario==='F'||scenario==='H');
   $('comparison-note').textContent=paired ? (scenario==='F'?'A는 원래 작업, B는 동일 seed·위치 수·출발점의 좌우 반사 작업입니다. 출발점과 물건 사이 거리도 달라집니다.':'A와 B는 같은 물건 집합이며 출발점이 다릅니다.') : '짝이 되는 작업이 없습니다. 해당 시나리오의 배치 또는 출발점을 선택하세요.';
   render(); aggregate();
 } catch(e) { if(token===refreshToken)error(e.message); }
}
function rowFor(detail, name) { return detail?.results.find(r=>r.algorithm===name); }
function xy(p) { return [50+Number(p[0])*10,430-Number(p[1])*10]; }
const svgNS='http://www.w3.org/2000/svg';
function el(name, attrs={}) { const e=document.createElementNS(svgNS,name); Object.entries(attrs).forEach(([k,v])=>e.setAttribute(k,v)); return e; }
function renderMap(target, detail, result, color, dashed, overlay) {
 const container=$(target); container.replaceChildren();
 if(!detail) { container.textContent='비교할 작업이 없습니다.'; return; }
 const svg=el('svg',{viewBox:'0 0 480 480','aria-hidden':'true'}); container.append(svg);
 for(const y of [0,20,40]) { const [x1,y1]=xy([0,y]), [x2,y2]=xy([36,y]); svg.append(el('line',{x1,y1,x2,y2,stroke:'#d4dfd9','stroke-width':7,'stroke-linecap':'round'})); }
 for(let x=0;x<=36;x+=4) { const [x1,y1]=xy([x,0]),[x2,y2]=xy([x,40]); svg.append(el('line',{x1,y1,x2,y2,stroke:'#d4dfd9','stroke-width':7,'stroke-linecap':'round'})); }
 for(let x=0;x<=36;x+=4) for(let y=2;y<40;y+=2) if(y!==20) { const [cx,cy]=xy([x,y]); svg.append(el('circle',{cx,cy,r:2,fill:'#b5c5bd'})); }
 let progressPath=null, marker=null;
 if(overlay?.path?.length) svg.append(el('polyline',{points:overlay.path.map(p=>xy(p).join(',')).join(' '),fill:'none',stroke:color==='#2874c1'?'#df8249':'#2874c1','stroke-width':2,'stroke-opacity':'.65','stroke-dasharray':'5 4','stroke-linecap':'round','stroke-linejoin':'round'}));
 if(result?.path?.length) {
   const points=result.path.map(p=>xy(p).join(',')).join(' ');
   svg.append(el('polyline',{points,fill:'none',stroke:color,'stroke-width':6,'stroke-opacity':'.13','stroke-linecap':'round','stroke-linejoin':'round'}));
   progressPath=el('polyline',{points,fill:'none',stroke:color,'stroke-width':3.5,'stroke-linecap':'round','stroke-linejoin':'round',...(dashed?{'stroke-dasharray':'7 4'}:{})}); svg.append(progressPath);
 }
 const order=result?.order || []; const orderMap=new Map(order.map((p,i)=>[p.join(','),i+1]));
 for(const p of detail.task.required) { const [cx,cy]=xy(p); svg.append(el('circle',{cx,cy,r:7,fill:'#fff',stroke:color,'stroke-width':2})); const text=el('text',{x:cx,y:cy+3,'text-anchor':'middle','font-size':8,'font-weight':'700',fill:color}); text.textContent=orderMap.get(p.join(',')) || '•'; svg.append(text); }
 for(const [name,p,fill] of [['S',detail.task.start,'#2b7f67'],['C',[36,0],'#354e68']]) { const [cx,cy]=xy(p); svg.append(el('circle',{cx,cy,r:12,fill,stroke:'#fff','stroke-width':2})); const text=el('text',{x:cx,y:cy+4,'text-anchor':'middle','font-size':11,'font-weight':'700',fill:'#fff'}); text.textContent=name; svg.append(text); }
 if(progressPath) { marker=el('circle',{r:6,fill:color,stroke:'#fff','stroke-width':2}); svg.append(marker); mapPaths.push({path:progressPath,marker,dashed}); }
 else { const text=el('text',{x:240,y:465,'text-anchor':'middle','font-size':12,fill:'#a26d4e'}); text.textContent=result?.path_error?'경로 검증 실패':result?.message || '표시할 경로가 없습니다'; svg.append(text); }
}
function renderSide(which, detail, result, overlay) {
 const badge=$('badge-'+which); badge.textContent = result ? (statuses[result.status]||result.status)+(result.fallback_used?' · 대체 경로':'') : '기록 없음'; badge.classList.toggle('bad',!!result && result.status!=='completed');
 const returned=result?.distance != null ? labels[result.returned_algorithm]||result.returned_algorithm||'—' : '—';
 $('route-info-'+which).innerHTML=`<div class="metric"><small>이동 거리</small><strong>${fmt(result?.distance,1)} <span>m</span></strong></div><div class="metric"><small>${live?'재계산 · 전체 요청':$('mode').value==='request'?'전체 요청':'후보 탐색'}</small><strong>${result?.seconds == null?'—':fmt(result.seconds*1000,3)} <span>ms</span></strong></div><div class="route-detail">반환 방법: ${escapeHtml(returned)}<br>${result?.optimal && result.status==='completed'?'최적해 확인':escapeHtml(terms[result?.termination]||result?.message||'최적성 미증명')}</div>`;
 renderMap('map-'+which,detail,result,which==='a'?'#2874c1':'#df8249',which==='b',overlay);
}
function drawProgress() {
 const ratio=Number($('progress').value)/1000; $('progress-label').value=`${Math.round(ratio*100)}%`;
 for(const {path,marker,dashed} of mapPaths) { const len=path.getTotalLength(); if(dashed && ratio===1) path.setAttribute('stroke-dasharray','7 4'); else path.setAttribute('stroke-dasharray',`${len*ratio} ${len}`); const p=path.getPointAtLength(len*ratio); marker.setAttribute('cx',p.x); marker.setAttribute('cy',p.y); }
}
function stop() {playing=false; if(frame)cancelAnimationFrame(frame); frame=null; $('play').textContent='▶'; $('play').setAttribute('aria-label','경로 재생');}
function tick(now) { if(!playing)return; if(lastTime) $('progress').value=Math.min(1000,Number($('progress').value)+(now-lastTime)*Number($('speed').value)/12); lastTime=now; drawProgress(); if(Number($('progress').value)>=1000)stop(); else frame=requestAnimationFrame(tick); }
function renderTable(detail) {
 const nn=rowFor(detail,'nn'); const optimum=detail.results.filter(r=>r.status==='completed'&&r.optimal&&r.distance!=null).map(r=>r.distance); const best=optimum.length?Math.min(...optimum):null;
 $('time-heading').textContent=$('mode').value==='request'?'전체 요청 시간':'후보 탐색 시간';
 $('results').innerHTML=detail.results.map(r=>{const comparable=r.status==='completed'&&!r.budget_exceeded&&r.distance!=null; const nnDiff=comparable&&nn?.status==='completed'&&nn.distance!=null?r.distance-nn.distance:null; const gap=comparable&&best!=null?r.distance-best:null; return `<tr><td>${escapeHtml(labels[r.algorithm])}</td><td>${escapeHtml(statuses[r.status]||r.status)}${r.termination?' · '+escapeHtml(terms[r.termination]||r.termination):''}${r.budget_exceeded?' · 예산 초과':''}</td><td>${r.distance==null?'—':escapeHtml(labels[r.returned_algorithm]||r.returned_algorithm||'—')}${r.fallback_used?' (대체)':''}</td><td class="num">${r.distance==null?'—':fmt(r.distance,1)+' m'}</td><td class="num">${time(r.seconds)}</td><td class="num">${nnDiff==null?'—':fmt(nnDiff,1)+' m'}</td><td class="num">${gap==null?'—':fmt(gap,1)+' m'}</td><td>${r.optimal&&r.status==='completed'?'최적해 확인':'—'}</td></tr>`;}).join('');
 const f=detail.features; $('task-info').textContent=`${detail.task.id} · ${f.n}개 위치 · 분산 ${fmt(f.dispersion,1)} m · 출발점 평균 ${fmt(f.start_mean,1)} m · 도착점 평균 ${fmt(f.conveyor_mean,1)} m`;
 const rule=detail.rules.count; const chosen=rule.algorithm || (f[rule.feature] <= rule.threshold?rule.left:rule.right); $('rule').textContent=`저장된 개수 기반 선택 규칙: ${rule.feature || '고정'} ${rule.threshold == null?'':`≤ ${rule.threshold}`} → ${labels[rule.left]||rule.algorithm}, 그 외 → ${labels[rule.right]||rule.algorithm}. 이 작업의 선택: ${labels[chosen]}. 규칙은 개발 데이터에서 정해졌습니다.`;
}
function render() {
 if(!current)return; mapPaths=[];
 const pairedScenario=scenario==='F'||scenario==='H';
 const rightDetail=pairedScenario ? other : current;
 const a=live?.[0] || rowFor(current,$('algorithm-a').value); const b=live?.[1] || rowFor(rightDetail,$('algorithm-b').value);
 const canOverlay=!!rightDetail && rightDetail.task.id===current.task.id;
 $('overlay').disabled=!canOverlay; if(!canOverlay)$('overlay').checked=false;
 $('run').disabled=pairedScenario && !other;
 renderSide('a',current,a,$('overlay').checked?b:null); renderSide('b',rightDetail,b,$('overlay').checked?a:null); $('progress').value=1000; drawProgress(); renderTable(current);
 $('source-tag').textContent='아래 표: 저장된 실험 기록';
}
async function runLive() {
 if(!current)return; $('run').disabled=true; $('live-note').textContent='선택한 후보를 순서대로 계산하고 있습니다…'; error('');
 const budget=Number($('budget').value), coefficient=Number($('coefficient').value);
 try {
   const results=[];
   for(const [detail,id] of [[current,'algorithm-a'],[other||current,'algorithm-b']]) {
     const data=await api('/api/recalculate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:detail.task.id,algorithms:[$(id).value],budget,coefficient})}); results.push(data.results[0]);
   }
   live=results; $('restore').hidden=false; $('live-note').textContent=`이번 데모에서 재측정 · ${new Date().toLocaleString('ko-KR')} · ${budget}초 / 계수 ${coefficient}${budget!==0.2||coefficient!==0.5?' · 본실험과 다른 설정':''}. 아래 표는 저장된 기록입니다.`; stop(); render();
 } catch(e){error(e.message); $('live-note').textContent='재계산에 실패했습니다. 저장된 결과는 유지됩니다.';} finally {$('run').disabled=false;}
}
async function init() {
 try {
   for(const [key,s] of Object.entries(scenarios)) { const b=document.createElement('button'); b.className='scenario'; b.dataset.key=key; b.innerHTML=`<b>${key}</b><span>${s[0]}</span>`; b.addEventListener('click',()=>setScenario(key)); $('scenarios').append(b); }
   for(const id of ['algorithm-a','algorithm-b']) { setOptions($(id),algorithms.map(a=>[a,labels[a]]),'nn'); $(id).addEventListener('change',()=>{live=null;$('restore').hidden=true;$('live-note').textContent='';render();}); }
   tasks=await api('/api/tasks');
   setOptions($('n'),[[ '', '전체'],...[...new Set(tasks.map(t=>t.required.length))].sort((a,b)=>a-b).map(n=>[n,`${n}개`])],'3');
   setOptions($('pattern'),[['','전체'],...Object.entries(patterns)],'clustered');
   setOptions($('start'),[['','전체'],['0','앞쪽'],['1','중앙'],['2','가장자리']],'0');
   setOptions($('seed'),[['','전체'],...[...new Set(tasks.map(t=>t.seed))].sort((a,b)=>a-b).map(s=>[s,String(s)])],'');
   for(const id of ['split','n','pattern','start','seed']) $(id).addEventListener('change',()=>{live=null;updateTaskOptions();aggregate();});
   $('task').addEventListener('change',loadDetail); $('mode').addEventListener('change',loadDetail);
   $('run').addEventListener('click',runLive); $('restore').addEventListener('click',()=>{live=null;$('restore').hidden=true;$('live-note').textContent='';render();});
   $('play').addEventListener('click',()=>{if(playing){stop();return;} if(Number($('progress').value)>=1000)$('progress').value=0; playing=true;lastTime=0;$('play').textContent='Ⅱ';$('play').setAttribute('aria-label','경로 일시정지');frame=requestAnimationFrame(tick);});
   $('overlay').addEventListener('change',render);
   $('reset').addEventListener('click',()=>{stop();$('progress').value=0;drawProgress();}); $('progress').addEventListener('input',()=>{stop();drawProgress();});
   setScenario('A');
 } catch(e) {error(`데이터를 불러오지 못했습니다: ${e.message}`);}
}
init();
