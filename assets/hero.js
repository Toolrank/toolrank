/* ToolRank "ranking signal" hero background: rising glow lines + linking particles. No deps. */
(function(){
  var heroes=document.querySelectorAll('.hero');if(!heroes.length||!window.requestAnimationFrame)return;
  var reduce=window.matchMedia&&matchMedia('(prefers-reduced-motion: reduce)').matches;
  var COLS=['124,92,255','34,211,238','167,139,250'];
  heroes.forEach(function(hero,idx){
    var home=idx===0&&!!document.getElementById('q')||location.pathname==='/'||/index\.html$/.test(location.pathname)&&location.pathname.split('/').length<3;
    var k=home?1:0.55; // lighter on inner pages
    hero.classList.add('has-sig');
    var c=document.createElement('canvas');c.className='sig-bg';c.setAttribute('aria-hidden','true');hero.insertBefore(c,hero.firstChild);
    var x=c.getContext('2d'),W=0,H=0,dpr=1,t=Math.random()*100,run=true,vis=true,mx=0,my=0,tx=0,ty=0;
    var lines=[],dots=[];
    function setup(){
      dpr=Math.min(window.devicePixelRatio||1,2);var r=hero.getBoundingClientRect();W=r.width;H=r.height;
      c.width=Math.round(W*dpr);c.height=Math.round(H*dpr);x.setTransform(dpr,0,0,dpr,0,0);
      var n=W<600?3:5;lines=[];for(var i=0;i<n;i++)lines.push({c:COLS[i%3],a:0.5+Math.random()*1.2,f:0.6+Math.random()*1.4,p:Math.random()*6,s:0.15+Math.random()*0.25,o:(i+1)/(n+1)});
      var m=Math.round((W<600?18:36)*k);dots=[];for(var j=0;j<m;j++)dots.push({x:Math.random()*W,y:Math.random()*H,vx:(Math.random()-.5)*.15,vy:-(0.05+Math.random()*.2),r:0.6+Math.random()*1.4,c:COLS[j%3]});
    }
    function yAt(L,u){ // rising chart: baseline climbs left->right, gentle wave + steps
      var base=H*(0.95-L.o*0.55)-u*H*0.28*L.a*0.6;
      return base+Math.sin(u*Math.PI*2*L.f+t*L.s+L.p)*H*0.06+Math.sin(u*17+t*L.s*2+L.p)*H*0.012;
    }
    function draw(){
      x.clearRect(0,0,W,H);tx+=(mx-tx)*0.05;ty+=(my-ty)*0.05;
      x.globalCompositeOperation='lighter';
      lines.forEach(function(L,i){
        var px=tx*(6+i*3),py=ty*(4+i*2);
        x.beginPath();for(var s=0;s<=60;s++){var u=s/60,X=u*W+px,Y=yAt(L,u)+py;s?x.lineTo(X,Y):x.moveTo(X,Y);}
        var g=x.createLinearGradient(0,0,W,0);g.addColorStop(0,'rgba('+L.c+',0)');g.addColorStop(.5,'rgba('+L.c+','+(0.35*k)+')');g.addColorStop(1,'rgba('+L.c+','+(0.6*k)+')');
        x.strokeStyle=g;x.lineWidth=1.2;x.shadowColor='rgba('+L.c+',.8)';x.shadowBlur=10*k;x.stroke();
        var hu=((t*L.s*0.08+L.p)%1),hx=hu*W+px,hy=yAt(L,hu)+py; // travelling signal pulse
        x.shadowBlur=14;x.fillStyle='rgba('+L.c+','+(0.9*k)+')';x.beginPath();x.arc(hx,hy,1.8,0,7);x.fill();
      });
      x.shadowBlur=0;
      for(var i=0;i<dots.length;i++){var d=dots[i];
        if(!reduce){d.x+=d.vx;d.y+=d.vy;if(d.y<-5){d.y=H+5;d.x=Math.random()*W}if(d.x<-5)d.x=W+5;if(d.x>W+5)d.x=-5;}
        var X=d.x+tx*10,Y=d.y+ty*8;
        for(var j=i+1;j<dots.length;j++){var e=dots[j],dx=d.x-e.x,dy=d.y-e.y,q=dx*dx+dy*dy;if(q<6400){x.strokeStyle='rgba('+d.c+','+(0.18*k*(1-q/6400))+')';x.lineWidth=.6;x.beginPath();x.moveTo(X,Y);x.lineTo(e.x+tx*10,e.y+ty*8);x.stroke();}}
        x.fillStyle='rgba('+d.c+','+(0.55*k)+')';x.beginPath();x.arc(X,Y,d.r,0,7);x.fill();
      }
      x.globalCompositeOperation='source-over';
    }
    var last=0;
    function loop(ts){if(!run||!vis||document.hidden){last=0;return;}
      if(ts-last>=32){t+=0.032;last=ts;draw();} // ~30fps cap for low CPU
      requestAnimationFrame(loop);}
    function start(){if(reduce||!vis||document.hidden)return;if(!run){run=true;}requestAnimationFrame(loop);}
    setup();draw();
    if(reduce)return;
    var rt;window.addEventListener('resize',function(){clearTimeout(rt);rt=setTimeout(function(){setup();draw();},150)});
    if('IntersectionObserver'in window)new IntersectionObserver(function(es){var was=vis;vis=es[0].isIntersecting;if(vis&&!was)start();}).observe(hero);
    document.addEventListener('visibilitychange',function(){if(!document.hidden)start();});
    if(window.matchMedia('(pointer:fine)').matches)hero.addEventListener('pointermove',function(e){var r=hero.getBoundingClientRect();mx=(e.clientX-r.left)/r.width-.5;my=(e.clientY-r.top)/r.height-.5;});
    start();
  });
})();
