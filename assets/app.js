const $=s=>document.querySelector(s);let D,sel="";
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
function render(){const q=$("#q").value.toLowerCase(),p=$("#price").value;sel=$("#cat").value;
 document.querySelectorAll(".chip").forEach(c=>c.classList.toggle("on",c.dataset.id===sel));
 $("#cats").innerHTML=D.categories.filter(c=>!sel||c.id===sel).map(c=>{
  const ts=c.tools.map((t,i)=>({...t,r:i+1})).filter(t=>(!p||t.pricing===p)&&(!q||(t.name+" "+t.verdict+" "+c.title).toLowerCase().includes(q)))
   .sort((a,b)=>b.featured-a.featured);
  if(!ts.length)return"";
  return`<section id="${c.id}"><h2><a href="/best/${c.id}/">${esc(c.title)}</a></h2><p class="muted">${esc(c.blurb)}</p><div class="grid">${ts.map(t=>`<article class="card">
  ${t.featured?'<span class="tag feat">Featured</span>':''}<h3><span class="rank">#${t.r}</span>${esc(t.name)}</h3><p>${esc(t.verdict)}</p>
  <span class="tag ${t.pricing}">${t.pricing}</span><a class="go" href="${esc(t.affiliate_url||t.url)}" target="_blank" rel="noopener${t.affiliate_url?' sponsored':''}">Visit ${esc(t.name)} →</a></article>`).join("")}</div></section>`}).join("")||'<p class="wrap muted">No tools match.</p>'}
fetch("data/tools.json").then(r=>r.json()).then(d=>{D=d;$("#upd").textContent=d.updated;
 d.categories.forEach(c=>{$("#cat").add(new Option(c.title,c.id));$("#chips").insertAdjacentHTML("beforeend",`<span class="chip" data-id="${c.id}">${esc(c.title.replace(/^Best (for )?/,""))}</span>`)});
 $("#chips").onclick=e=>{const id=e.target.dataset.id;if(id==null)return;$("#cat").value=sel===id?"":id;render()};
 const uq=new URLSearchParams(location.search).get("q");if(uq)$("#q").value=uq;
 ["q","cat","price"].forEach(i=>$("#"+i).oninput=render);render()});
fetch("data/new-this-week.json").then(r=>r.json()).then(d=>{$("#newlist").innerHTML=d.items.sort((a,b)=>b.date.localeCompare(a.date)).map(n=>`<article class="card"><span class="date">${esc(n.date)} · ${esc(n.type)}</span><h3>${esc(n.title)}</h3><p>${esc(n.summary)}</p><a class="go" href="${esc(n.url)}" target="_blank" rel="noopener">Read: ${esc(n.title)} →</a></article>`).join("")});
$("#nl").onsubmit=e=>{e.preventDefault();$("#nlmsg").textContent="Thanks! (placeholder — no signup was sent)"};
