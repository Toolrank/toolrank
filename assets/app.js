/* ToolRank home v2: tabs, search, category tiles with expanding panel. No deps. */
(function(){
const $=s=>document.querySelector(s),$$=s=>[...document.querySelectorAll(s)];
let D=null,RV={},tab="you",openId=null;
const REVIEW_NEW="https://github.com/Toolrank/toolrank/issues/new?template=review.yml";
const slug=n=>n.toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"");
const esc=s=>String(s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const RM=matchMedia("(prefers-reduced-motion: reduce)").matches;
const TAG={you:"Everyday and creator AI tools, hand-picked and ranked. No fluff.",business:"AI for teams, developers and venues: ranked for work.",makers:"Built an AI tool? Get listed free, collect reviews, get featured."};
const inTab=t=>tab==="you"?t.audience!=="business":tab==="business"?t.audience!=="consumer":true;
const SYN={editing:"edit",editor:"edit",videos:"video",coding:"code",coder:"code",app:"code",apps:"code",images:"image",photo:"image",photos:"image",picture:"image",design:"image",audio:"voice",speech:"voice",music:"voice",agents:"agent",agentic:"agent",writing:"write",writer:"write",cryptocurrency:"crypto",bitcoin:"crypto",btc:"crypto",eth:"crypto",web3:"crypto",blockchain:"crypto",defi:"crypto",wallet:"crypto",restaurant:"restaurant",bar:"restaurant",cafe:"restaurant",hotel:"hospitality",travel:"hospitality",trip:"hospitality",learn:"education",study:"education",teacher:"education",language:"education",fitness:"health",workout:"health",sleep:"health",game:"gaming",games:"gaming",sales:"marketing",seo:"marketing"};
const STOP=new Set(["a","an","the","for","and","or","to","of","with","in","on","ai","tool","tools","best","i","want","my","me","do","help"]);
const stem=w=>SYN[w]||w.replace(/(ing|ers|er|es|s)$/,"").replace(/(.)\1$/,"$1")||w;
const toks=s=>String(s).toLowerCase().split(/[^a-z0-9]+/).filter(w=>w&&!STOP.has(w)).map(stem);
const priceOk=(t,p)=>!p||(p==="free"?t.pricing!=="paid":t.pricing===p);
const score=(t,c,qt)=>{const h=new Set(toks([t.name,t.verdict,c.title,c.id,c.blurb,(t.tags||[]).join(" ")].join(" ")));return qt.filter(w=>h.has(w)||[...h].some(x=>x.length>3&&w.length>3&&(x.startsWith(w)||w.startsWith(x)))).length+(toks(t.name).some(x=>qt.includes(x))?3:0)};
const dom=u=>{try{return new URL(u).hostname.replace(/^www\./,"")}catch(e){return""}};
const rvl=t=>{const rs=RV[slug(t.name)]||[],n=rs.length,a=n?Math.round(rs.reduce((x,r)=>x+r.rating,0)/n*10)/10:0,s=slug(t.name);
 return `<div class="rvl">${n?`<a href="/reviews.html#${s}"><span class="st">★ ${a}</span> · ${n} review${n!==1?"s":""}</a>`:`<a href="/reviews.html#${s}">Reviews (0)</a>`}<a class="rvbtn" href="${esc(REVIEW_NEW+"&tool_name="+encodeURIComponent(t.name))}" target="_blank" rel="noopener">${n?"Review":"Be the first to review"}</a></div>`};
const card=t=>`<article class="card tool"><div class="th"><span class="lg" data-l="${esc(t.name[0].toUpperCase())}" aria-hidden="true"><img src="https://www.google.com/s2/favicons?domain=${esc(dom(t.url))}&amp;sz=64" alt="" width="40" height="40" loading="lazy" decoding="async" onerror="this.remove()"></span><div class="tt"><h3><span class="rank">#${t.r}</span>${esc(t.name)}</h3><div class="tm"><span class="tag ${t.pricing}">${t.pricing}</span>${t.featured?'<span class="tag feat">Featured</span>':''}</div></div></div>
 <p>${esc(t.verdict)}</p>${rvl(t)}<a class="go" href="${esc(t.affiliate_url||t.url)}" target="_blank" rel="noopener${t.affiliate_url?' sponsored':''}">Visit ${esc(t.name)} →</a></article>`;
const catTools=(c,all)=>c.tools.map((t,i)=>({...t,r:i+1})).filter(t=>(all||inTab(t))&&priceOk(t,$("#price").value));
function updTiles(){if(!D)return;$$(".tile").forEach(el=>{const c=D.categories.find(x=>x.id===el.dataset.cat);if(!c)return;const n=catTools(c).length;el.hidden=tab!=="makers"&&n===0;el.querySelector(".tc").textContent=n+" tool"+(n!==1?"s":"")})}
function closePanel(){const p=$("#panel");if(p)p.remove();$$(".tile.on").forEach(t=>{t.classList.remove("on");t.setAttribute("aria-expanded","false")});openId=null}
function openPanel(id,all,lim){const c=D.categories.find(x=>x.id===id);if(!c)return;const tile=$(`.tile[data-cat="${id}"]`);closePanel();openId=id;
 tile.classList.add("on");tile.setAttribute("aria-expanded","true");
 const ts=catTools(c,all),tot=catTools(c,true).length,L=lim||9,sh=ts.slice(0,L);
 const p=document.createElement("div");p.className="panel";p.id="panel";p.setAttribute("role","region");p.setAttribute("aria-label",c.title);
 p.innerHTML=`<div class="ph"><img src="/assets/cat/${c.id}.svg" alt=""><div><h3>${esc(c.title)}</h3><p>${esc(c.blurb)}</p></div><button type="button" class="x" aria-label="Close ${esc(c.title)}">×</button></div>
 <div class="tgrid">${sh.map(card).join("")||'<p class="muted">No tools match this filter.</p>'}</div>
 <div class="pfoot"><span class="muted small">Showing ${sh.length} of ${ts.length}${!all&&ts.length<tot?` for ${tab==="you"?"you":"business"} (${tot} total)`:""}</span><span>${ts.length>L?`<button type="button" class="btn ghost sm" data-more>Show all ${ts.length}</button> `:""}${!all&&ts.length<tot?`<button type="button" class="btn ghost sm" data-all>Show all audiences</button> `:""}<a class="btn sm" href="/best/${c.id}/">Full ranking &amp; FAQ →</a></span></div>`;
 tile.after(p);
 p.querySelector(".x").onclick=()=>{closePanel();tile.focus()};
 const m=p.querySelector("[data-more]");if(m)m.onclick=()=>openPanel(id,all,999);
 const a=p.querySelector("[data-all]");if(a)a.onclick=()=>openPanel(id,true,lim);
 if(!lim)p.scrollIntoView({behavior:RM?"auto":"smooth",block:"start"})}
$("#tiles").addEventListener("click",e=>{const t=e.target.closest(".tile");if(!t||!D||e.metaKey||e.ctrlKey)return;e.preventDefault();openId===t.dataset.cat?closePanel():openPanel(t.dataset.cat)});
$$(".tile").forEach(t=>t.setAttribute("aria-expanded","false"));
addEventListener("keydown",e=>{if(e.key==="Escape"&&openId)closePanel()});
if(!RM&&matchMedia("(hover:hover)").matches)$$(".tile").forEach(t=>{t.addEventListener("pointermove",e=>{const r=t.getBoundingClientRect(),x=(e.clientX-r.left)/r.width-.5,y=(e.clientY-r.top)/r.height-.5;t.style.setProperty("--ry",(x*10).toFixed(2)+"deg");t.style.setProperty("--rx",(-y*10).toFixed(2)+"deg")});t.addEventListener("pointerleave",()=>{t.style.removeProperty("--rx");t.style.removeProperty("--ry")})});
function search(){const qt=toks($("#q").value),p=$("#price").value,R=$("#results");
 if(!qt.length||!D){R.hidden=true;return}
 let all=D.categories.flatMap(c=>c.tools.map((t,i)=>({...t,r:i+1,s:score(t,c,qt),c})));
 let pk=all.filter(t=>t.s>0&&priceOk(t,p)).sort((a,b)=>b.s-a.s||b.featured-a.featured||a.r-b.r).slice(0,24);
 $("#rtitle").textContent=pk.length?`Top matches for “${$("#q").value.trim()}”`:"No exact match. Try a category below.";
 $("#rgrid").innerHTML=pk.map(card).join("");R.hidden=false}
function setTab(t,push){if(!TAG[t])t="you";tab=t;
 $$(".seg button").forEach((b,i)=>{const on=b.dataset.tab===t;b.setAttribute("aria-selected",on);b.classList.toggle("on",on);if(on)$(".seg").style.setProperty("--i",i)});
 $("#tagline").textContent=TAG[t];const mk=t==="makers";
 [["#dirwrap",!mk],["#makerspane",mk]].forEach(([s,show])=>{const e=$(s);if(show){e.hidden=false;e.classList.remove("in");void e.offsetWidth;e.classList.add("in")}else e.hidden=true});
 $("#sf").style.display=mk?"none":"";
 if(push&&location.hash!=="#"+t)history.replaceState(null,"","#"+t);
 if(D&&!mk){updTiles();if(openId)openPanel(openId,false,0)}}
$$(".seg button").forEach(b=>b.onclick=()=>setTab(b.dataset.tab,true));
setTab(["you","business","makers"].includes(location.hash.slice(1))?location.hash.slice(1):"you");
$("#price").onchange=()=>{updTiles();search();if(openId)openPanel(openId)};
$("#q").oninput=search;
$("#rclear").onclick=()=>{$("#q").value="";search();$("#q").focus()};
$("#sf").onsubmit=e=>{e.preventDefault();const term=$("#q").value.trim().toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"").slice(0,40);
 if(term&&window.goatcounter&&goatcounter.count)goatcounter.count({path:"search/"+term,title:"Search: "+term,event:true});
 if(tab==="makers")setTab("you",true);search();$("#q").blur();if(!$("#results").hidden)$("#results").scrollIntoView({behavior:RM?"auto":"smooth"})};
const rvP=fetch("/data/reviews.json",{cache:"no-cache"}).then(r=>r.json()).then(d=>{d.reviews.filter(r=>r.listed).forEach(r=>(RV[r.tool_slug]=RV[r.tool_slug]||[]).push(r))}).catch(()=>{});
fetch("/data/tools.json",{cache:"no-cache"}).then(r=>r.json()).then(async d=>{await rvP;D=d;updTiles();
 const uq=new URLSearchParams(location.search);if(uq.get("q")){$("#q").value=uq.get("q");search()}
 if(uq.get("cat"))openPanel(uq.get("cat"))});
})();
