const $=s=>document.querySelector(s);let D,sel="";
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const SYN={edit:"edit",edits:"edit",editing:"edit",editor:"edit",editors:"edit",video:"video",videos:"video",code:"code",coding:"code",coder:"code",image:"image",images:"image",photo:"image",photos:"image",picture:"image",voice:"voice",audio:"voice",speech:"voice",agent:"agent",agents:"agent",agentic:"agent",write:"write",writing:"write",writer:"write",writers:"write"};
const STOP=new Set(["a","an","the","for","and","or","to","of","with","in","on","ai","tool","tools","best"]);
const stem=w=>SYN[w]||w.replace(/(ing|ers|er|es|s)$/,"").replace(/(.)\1$/,"$1")||w;
const toks=s=>String(s).toLowerCase().split(/[^a-z0-9]+/).filter(w=>w&&!STOP.has(w)).map(stem);
const priceOk=(t,p)=>!p||t.pricing===p||(p==="free"&&t.pricing==="freemium");
const score=(t,c,qt)=>{const h=new Set(toks([t.name,t.verdict,c.title,c.id,t.pricing,(t.tags||[]).join(" ")].join(" ")));return qt.filter(w=>h.has(w)||[...h].some(x=>x.length>3&&w.length>3&&(x.startsWith(w)||w.startsWith(x)))).length};
const card=t=>`<article class="card">
  ${t.featured?'<span class="tag feat">Featured</span>':''}<h3><span class="rank">#${t.r}</span>${esc(t.name)}</h3><p>${esc(t.verdict)}</p>
  <span class="tag ${t.pricing}">${t.pricing}</span><a class="go" href="${esc(t.affiliate_url||t.url)}" target="_blank" rel="noopener${t.affiliate_url?' sponsored':''}">Visit ${esc(t.name)} →</a></article>`;
function render(){const qt=toks($("#q").value),p=$("#price").value;sel=$("#cat").value;
 document.querySelectorAll(".chip").forEach(c=>c.classList.toggle("on",c.dataset.id===sel));
 const cs=D.categories.filter(c=>!sel||c.id===sel).map(c=>{const ts=c.tools.map((t,i)=>({...t,r:i+1,s:qt.length?score(t,c,qt):0}))
   .filter(t=>priceOk(t,p)&&(!qt.length||t.s>0)).sort((a,b)=>b.s-a.s||b.featured-a.featured||a.r-b.r);return{c,ts,m:Math.max(0,...ts.map(t=>t.s))}})
  .filter(x=>x.ts.length).sort((a,b)=>b.m-a.m);
 let h=cs.map(({c,ts})=>`<section id="${c.id}"><h2><a href="/best/${c.id}/">${esc(c.title)}</a></h2><p class="muted">${esc(c.blurb)}</p><div class="grid">${ts.map(card).join("")}</div></section>`).join("");
 if(!h){const all=D.categories.flatMap(c=>c.tools.map((t,i)=>({...t,r:i+1,s:qt.length?score(t,c,qt):0})));
  let pk=all.filter(t=>t.s>0&&priceOk(t,p));if(!pk.length)pk=all.filter(t=>t.s>0);if(!pk.length)pk=all.filter(t=>priceOk(t,p)&&t.r===1);
  pk=pk.sort((a,b)=>b.s-a.s||a.r-b.r).slice(0,6);
  h=`<section class="wrap"><p class="muted">No exact match, closest picks:</p><div class="grid">${pk.map(card).join("")}</div><p class="muted">Missing a tool? <a href="/submit.html">Submit a tool</a> (free).</p></section>`}
 $("#cats").innerHTML=h}
fetch("data/tools.json").then(r=>r.json()).then(d=>{D=d;$("#upd").textContent=d.updated;
 d.categories.forEach(c=>{$("#cat").add(new Option(c.title,c.id));$("#chips").insertAdjacentHTML("beforeend",`<span class="chip" data-id="${c.id}">${esc(c.title.replace(/^Best (for )?/,""))}</span>`)});
 $("#chips").onclick=e=>{const id=e.target.dataset.id;if(id==null)return;$("#cat").value=sel===id?"":id;render()};
 const uq=new URLSearchParams(location.search).get("q");if(uq)$("#q").value=uq;
 ["q","cat","price"].forEach(i=>$("#"+i).oninput=render);render()});
fetch("data/new-this-week.json").then(r=>r.json()).then(d=>{$("#newlist").innerHTML=d.items.sort((a,b)=>b.date.localeCompare(a.date)).map(n=>`<article class="card"><span class="date">${esc(n.date)} · ${esc(n.type)}</span><h3>${esc(n.title)}</h3><p>${esc(n.summary)}</p><a class="go" href="${esc(n.url)}" target="_blank" rel="noopener">Read: ${esc(n.title)} →</a></article>`).join("")});
$("#nl").onsubmit=e=>{e.preventDefault();$("#nlmsg").textContent="Thanks! (placeholder — no signup was sent)"};
