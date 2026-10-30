/* ToolRank PWA: service worker registration + subtle, dismissible footer "Install app" control. No deps. */
(function(){
var L=location,ok=L.protocol==="https:"||L.hostname==="localhost"||L.hostname==="127.0.0.1";
if(ok&&"serviceWorker" in navigator)addEventListener("load",function(){navigator.serviceWorker.register("/sw.js").catch(function(){})});
var K="tr-pwa-dismissed",S="tr-pwa-ios-seen";
function get(k){try{return localStorage.getItem(k)}catch(e){return null}}
function set(k){try{localStorage.setItem(k,"1")}catch(e){}}
var standalone=(window.matchMedia&&matchMedia("(display-mode: standalone)").matches)||navigator.standalone===true;
var box=document.querySelector(".pwa-i");if(!box||standalone||get(K))return;
var btn=box.querySelector(".pwa-btn"),hint=box.querySelector(".pwa-hint"),x=box.querySelector(".pwa-x"),ev=null;
function hide(){box.hidden=true}
x.onclick=function(){set(K);hide()};
addEventListener("beforeinstallprompt",function(e){e.preventDefault();ev=e;btn.hidden=false;hint.hidden=true;box.hidden=false});
btn.onclick=function(){if(!ev)return;ev.prompt();ev.userChoice.then(function(c){ev=null;if(c&&c.outcome==="accepted")hide()}).catch(hide)};
addEventListener("appinstalled",function(){set(K);hide()});
var ua=navigator.userAgent,ios=/iP(hone|ad|od)/.test(ua)||(/Macintosh/.test(ua)&&navigator.maxTouchPoints>1);
var safari=/Safari/.test(ua)&&!/CriOS|FxiOS|EdgiOS|OPiOS|GSA\//.test(ua);
if(ios&&safari&&!get(S)){btn.hidden=true;hint.hidden=false;box.hidden=false;
 /* "only once": count the hint as seen the first time it actually scrolls into view */
 if("IntersectionObserver" in window){var io=new IntersectionObserver(function(es){if(es[0].isIntersecting){set(S);io.disconnect()}});io.observe(box)}else set(S)}
})();
