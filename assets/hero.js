/* ToolRank hero: flowing lines ease into leaderboard tiers; data points climb, the #1 gets a soft glow. No deps. */
(function(){
  var heroes=document.querySelectorAll('.hero');if(!heroes.length||!window.requestAnimationFrame)return;
  var reduce=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  var COLS=['59,130,246','56,189,248','147,197,253']; // blue-500, sky-400, blue-300
  function ss(a,b,v){v=Math.max(0,Math.min(1,(v-a)/(b-a)));return v*v*(3-2*v);}
  heroes.forEach(function(hero,idx){
    var home=idx===0&&!!document.getElementById('q')||location.pathname==='/'||/index\.html$/.test(location.pathname)&&location.pathname.split('/').length<3;
    var k=home?1:0.55;
    hero.classList.add('has-sig');
    var c=document.createElement('canvas');c.className='sig-bg';c.setAttribute('aria-hidden','true');hero.insertBefore(c,hero.firstChild);
    var x=c.getContext('2d'),W=0,H=0,dpr=1,t=0,run=true,vis=true,mx=0,my=0,tx=0,ty=0;
    var lines=[],dots=[],n=5,champ=null,glow=0,CYC=16;
    function tierY(i){return H*(0.22+i*(0.62/(n-1)));}
    function newDot(d){d=d||{};d.tier=n-1;d.from=d.tier;d.hop=1;d.u=Math.random()*0.5;d.sp=0.0012+Math.random()*0.0016;d.wait=40+Math.random()*160;d.r=1+Math.random()*1.2;d.c=COLS[Math.floor(Math.random()*3)];return d;}
    function setup(){
      dpr=Math.min(window.devicePixelRatio||1,2);var r=hero.getBoundingClientRect();W=r.width;H=r.height;
      c.width=Math.round(W*dpr);c.height=Math.round(H*dpr);x.setTransform(dpr,0,0,dpr,0,0);
      n=W<600?4:5;lines=[];for(var i=0;i<n;i++)lines.push({c:COLS[i%3],a:0.6+Math.random(),f:0.6+Math.random()*1.2,p:Math.random()*6,s:0.2+Math.random()*0.2});
      var m=Math.round((W<600?7:14)*k);dots=[];for(var j=0;j<m;j++){var d=newDot();d.tier=d.from=Math.floor(Math.random()*n);if(!d.tier)d.tier=d.from=1;dots.push(d);}
      champ=null;glow=0;
    }
    function settle(){var p=(t%CYC)/CYC;return ss(0.08,0.35,p)*(1-ss(0.82,1,p));} // wave -> tiers -> release
    function yAt(i,u){var L=lines[i],S=settle(),wave=H*(0.9-(n-i)/(n+1)*0.6)-u*H*0.15*L.a+Math.sin(u*Math.PI*2*L.f+t*L.s+L.p)*H*0.06;
      var flat=tierY(i)+Math.sin(u*9+t*L.s+L.p)*H*0.004,e=ss(0.12,0.7,u)*S;return wave+(flat-wave)*e;}
    function draw(){
      x.clearRect(0,0,W,H);tx+=(mx-tx)*0.05;ty+=(my-ty)*0.05;x.globalCompositeOperation='lighter';
      var S=settle();
      for(var i=0;i<n;i++){var L=lines[i],px=tx*(4+i*2),py=ty*(3+i);
        x.beginPath();for(var s=0;s<=48;s++){var u=s/48,X=u*W+px,Y=yAt(i,u)+py;s?x.lineTo(X,Y):x.moveTo(X,Y);}
        var a=(i===0?0.5:0.32)*k,g=x.createLinearGradient(0,0,W,0);g.addColorStop(0,'rgba('+L.c+',0)');g.addColorStop(.55,'rgba('+L.c+','+a*0.6+')');g.addColorStop(1,'rgba('+L.c+','+a+')');
        x.strokeStyle=g;x.lineWidth=i===0?1.4:1.1;x.stroke();
      }
      for(var j=0;j<dots.length;j++){var d=dots[j];
        if(!reduce&&d!==champ){d.u+=d.sp;if(d.u>1.02)d.u=0.05+Math.random()*0.2;
          if(d.hop<1)d.hop=Math.min(1,d.hop+0.02);else if(S>0.6&&--d.wait<0&&d.u>0.35){d.from=d.tier;d.tier=Math.max(0,d.tier-1);d.hop=0;d.wait=60+Math.random()*180;}
          if(d.tier===0&&d.hop>=1&&!champ){champ=d;glow=0;}}
        var e=ss(0,1,d.hop),Y=yAt(d.from,d.u)+(yAt(d.tier,d.u)-yAt(d.from,d.u))*e-Math.sin(e*Math.PI)*H*0.02,X=d.u*W;
        X+=tx*8;Y+=ty*6;d.X=X;d.Y=Y;
        x.fillStyle='rgba('+d.c+','+(0.6*k)+')';x.beginPath();x.arc(X,Y,d.r,0,7);x.fill();
      }
      if(champ){glow+=0.012;var gA=Math.sin(Math.min(glow,1)*Math.PI)*0.5*k,R=26+glow*10,rg=x.createRadialGradient(champ.X,champ.Y,0,champ.X,champ.Y,R);
        rg.addColorStop(0,'rgba(125,211,252,'+gA+')');rg.addColorStop(1,'rgba(59,130,246,0)');x.fillStyle=rg;x.beginPath();x.arc(champ.X,champ.Y,R,0,7);x.fill();
        x.fillStyle='rgba(224,242,254,'+(0.4+gA)+')';x.beginPath();x.arc(champ.X,champ.Y,2.2,0,7);x.fill();
        if(glow>=1){newDot(champ);champ=null;}}
      x.globalCompositeOperation='source-over';
    }
    var last=0;
    function loop(ts){if(!run||!vis||document.hidden){last=0;return;}
      if(ts-last>=32){t+=0.032;last=ts;draw();} // ~30fps cap
      requestAnimationFrame(loop);}
    function start(){if(reduce||!vis||document.hidden)return;requestAnimationFrame(loop);}
    setup();if(reduce){t=CYC*0.5;dots.forEach(function(d,i){d.u=0.4+0.5*(i/dots.length);});draw();return;} // static tiered frame
    t=CYC*0.3;draw();
    var rt;window.addEventListener('resize',function(){clearTimeout(rt);rt=setTimeout(function(){setup();draw();},150)});
    if('IntersectionObserver'in window)new IntersectionObserver(function(es){var was=vis;vis=es[0].isIntersecting;if(vis&&!was)start();}).observe(hero);
    document.addEventListener('visibilitychange',function(){if(!document.hidden)start();});
    if(window.matchMedia('(pointer:fine)').matches)hero.addEventListener('pointermove',function(e){var r=hero.getBoundingClientRect();mx=(e.clientX-r.left)/r.width-.5;my=(e.clientY-r.top)/r.height-.5;});
    start();
  });
})();
