(()=>{const $=s=>document.querySelector(s),esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const slug=n=>n.toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"");const NV='<span class="nv">Not yet verified</span>';
const dom=u=>{try{return new URL(u).hostname.replace(/^www\./,"")}catch(e){return""}};
const fd=s=>{if(!s)return"";const d=new Date(s+"T00:00:00");return d.toLocaleDateString("en-GB",{day:"numeric",month:"short",year:"numeric"})};
const pn=s=>{const m=/[$€£]\s?([0-9][0-9,]*(?:\.[0-9]+)?)/.exec(s||"");return m?parseFloat(m[1].replace(/,/g,"")):null};
let T=[],RV={},sel=[];const P=t=>t.pricing_detail||{};
const freeP=t=>P(t).free_tier?"yes":(t.last_verified&&P(t).model==="paid"?"no":null);
const trial=t=>/trial/i.test((P(t).free_tier||"")+" "+(P(t).notes||""));
const yn=v=>v==="yes"?'<span class="yes">✓ Yes</span>':v==="no"?'<span class="no">✕ No</span>':NV;
const nv=v=>v?esc(v):NV;
function url(){history.replaceState(null,"",location.pathname+(sel.length?"?tools="+sel.join(","):"")+location.hash)}
function filt(){const c=$("#fcat").value,f=$("#ffree").checked,tr=$("#ftrial").checked,v=$("#fver").checked,mx=+$("#fprice").value,pl=[...document.querySelectorAll("#fplat input:checked")].map(x=>x.value),q=$("#fq").value.toLowerCase().trim();
 return T.filter(t=>(!c||t.cat===c)&&(!f||freeP(t)==="yes")&&(!tr||trial(t))&&(!v||t.last_verified)&&(mx>=100||(pn(P(t).starting_price)??(freeP(t)==="yes"?0:1e9))<=mx)&&(!pl.length||pl.some(p=>(t.platforms||[]).includes(p)))&&(!q||t.name.toLowerCase().includes(q)))}
function list(){const r=filt().filter(t=>!sel.includes(t.s)).slice(0,40);$("#fres").innerHTML=r.map(t=>`<li><button type="button" data-add="${t.s}"><img src="/assets/logos/${t.s}.png" alt="" onerror="this.remove()" width="18" height="18">${esc(t.name)}<span class="muted small">${esc(t.ct)}</span>${t.last_verified?'<span class="vb">verified</span>':""}</button></li>`).join("")||'<li class="muted small">No tools match these filters.</li>'}
function rating(t){const rs=RV[t.s]||[];if(!rs.length)return'<span class="muted small">No reviews yet</span>';const a=Math.round(rs.reduce((x,r)=>x+r.rating,0)/rs.length*10)/10;return`<span class="st">★ ${a}</span> <span class="muted small">${rs.length} review${rs.length>1?"s":""}</span>`}
function render(){const ts=sel.map(s=>T.find(t=>t.s===s)).filter(Boolean);
 $("#ccards").innerHTML=ts.map((t,k)=>`<article class="ccard c${k}"><div class="cg"><span class="lg" data-l="${esc(t.name[0])}"><img src="/assets/logos/${t.s}.png" alt="" width="40" height="40" onerror="this.remove()"></span><button type="button" class="rm" data-rm="${t.s}" aria-label="Remove ${esc(t.name)}">×</button></div>
 <div class="cb"><h3><a href="/tools/${t.s}/">${esc(t.name)}</a></h3><p class="muted small">#${t.r} in ${esc(t.ct)}</p><div>${rating(t)}</div><dl class="evd"><dt>Starts at</dt><dd>${nv(P(t).starting_price)}</dd><dt>Free plan</dt><dd>${yn(freeP(t))}</dd><dt>Best for</dt><dd>${nv(t.best_for)}</dd><dt>Main limitation</dt><dd>${nv(t.main_limitation)}</dd><dt>Last verified</dt><dd>${t.last_verified?fd(t.last_verified):NV}</dd></dl>
 <a class="btn sm" href="${esc(t.affiliate_url||t.url)}" target="_blank" rel="noopener${t.affiliate_url?" sponsored":""}">Visit site →</a></div></article>`).join("")+(ts.length<4?`<button type="button" class="ccard add" id="addf" aria-haspopup="dialog"><span class="plus" aria-hidden="true">+</span><span class="al">Add tool</span><span class="muted small">${4-ts.length} slot${4-ts.length>1?"s":""} left</span></button>`:"");
 const a=$("#addf");if(a)a.onclick=openPick;
 const rows=[["Pricing model",t=>nv(P(t).model)],["Starting price",t=>nv(P(t).starting_price)],["Free tier",t=>freeP(t)==="yes"?'<span class="yes">✓</span> '+esc(P(t).free_tier):freeP(t)==="no"?'<span class="no">✕ None listed</span>':NV],["Free trial",t=>trial(t)?'<span class="yes">✓ Yes</span>':(t.last_verified?'<span class="no">✕ Not listed</span>':NV)],
  ["Platforms",t=>(t.platforms||[]).length?esc(t.platforms.join(", ")):NV],["Integrations",t=>(t.integrations||[]).length?esc(t.integrations.join(", ")):NV],["Model / provider",t=>nv(t.model_provider)],["Best for",t=>nv(t.best_for)],["Avoid if",t=>nv(t.avoid_if)],["Last verified",t=>t.last_verified?fd(t.last_verified):NV],["Sources",t=>(t.sources||[]).length?t.sources.map(x=>`<a href="${esc(x.url)}" target="_blank" rel="noopener nofollow">${esc(x.label)}</a>`).join("<br>"):NV]];
 $("#cmatrix").innerHTML=ts.length?`<h2>Feature matrix</h2><div class="tbl mx"><table class="cmp"><thead><tr><th>Feature</th>${ts.map((t,k)=>`<th class="c${k}">${esc(t.name)}</th>`).join("")}</tr></thead><tbody>${rows.map(([l,f])=>`<tr><th scope="row">${l}</th>${ts.map(t=>`<td>${f(t)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`:'<p class="muted">Pick tools to compare, or start with a preset above.</p>';
 url();list()}
const logo=t=>`<img src="/assets/logos/${t.s}.png" alt="" width="28" height="28" loading="lazy" onerror="this.remove()">`;
const prow=t=>`<li><button type="button" data-add="${t.s}" class="pr">${logo(t)}<span class="pn">${esc(t.name)}<span class="muted small">${esc(t.ct)} · #${t.r}</span></span>${t.last_verified?'<span class="vb">verified</span>':""}</button></li>`;
function pickList(){const q=$("#pq").value.toLowerCase().trim(),av=T.filter(t=>!sel.includes(t.s));
 const c0=T.find(t=>t.s===sel[0]),cat=c0?c0.cat:"coding",ct=c0?c0.ct:"Coding & App Building";
 $("#ppop").innerHTML=q?"":`<h3 class="ph3">Popular in ${esc(ct)}</h3><ul class="plist">${av.filter(t=>t.cat===cat).slice(0,6).map(prow).join("")}</ul>`;
 const r=q?av.filter(t=>t.name.toLowerCase().includes(q)||t.ct.toLowerCase().includes(q)).slice(0,30):[];
 $("#pres").innerHTML=q?(r.length?`<h3 class="ph3">Results</h3><ul class="plist">${r.map(prow).join("")}</ul>`:'<p class="muted">No tools match.</p>'):""}
function openPick(){const d=$("#pick");$("#pq").value="";pickList();d.showModal();$("#pq").focus()}
document.addEventListener("click",e=>{const a=e.target.closest("[data-add]"),r=e.target.closest("[data-rm]");if(a&&sel.length<4){sel.push(a.dataset.add);const d=$("#pick");if(d.open)d.close();render();const n=$("#addf");if(n)n.focus()}else if(a){alert("You can compare up to 4 tools. Remove one first.")}if(r){sel=sel.filter(s=>s!==r.dataset.rm);render()}});
Promise.all([fetch("/data/tools.json").then(r=>r.json()),fetch("/data/reviews.json").then(r=>r.json()).catch(()=>({reviews:[]}))]).then(([d,rv])=>{
 d.categories.forEach(c=>c.tools.forEach((t,i)=>T.push({...t,s:slug(t.name),cat:c.id,ct:c.title,r:i+1})));
 (rv.reviews||[]).filter(r=>r.listed).forEach(r=>(RV[r.tool_slug]=RV[r.tool_slug]||[]).push(r));
 const pls=[...new Set(T.flatMap(t=>t.platforms||[]))].sort();$("#fplat").innerHTML=pls.map(p=>`<label class="ck"><input type="checkbox" value="${esc(p)}"> ${esc(p)}</label>`).join("");
 const q=new URLSearchParams(location.search).get("tools");sel=(q?q.split(","):["cursor","claude-code"]).filter(s=>T.some(t=>t.s===s)).filter((s,i,a)=>a.indexOf(s)===i).slice(0,4);
 const c0=T.find(t=>t.s===sel[0]);if(c0&&q&&sel.length===1)$("#fcat").value=c0.cat;
 ["#fcat","#ffree","#ftrial","#fver","#fprice","#fq"].forEach(s=>$(s).addEventListener("input",()=>{if(s==="#fprice"){const v=+$(s).value;$("#fpv").textContent=v>=100?"Any":"$"+v}list()}));$("#fplat").addEventListener("change",list);$("#pq").addEventListener("input",pickList);$("#pclose").onclick=()=>$("#pick").close();$("#pick").addEventListener("click",e=>{if(e.target.id==="pick")$("#pick").close()});render()})})();
