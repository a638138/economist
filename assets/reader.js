
(function(){
  var SKEY='econ.settings', PKEY='econ.progress';
  var slug=window.__ISSUE__||'';
  var doc=document.documentElement, body=document.body;
  function rj(k,d){try{return JSON.parse(localStorage.getItem(k))||d;}catch(e){return d;}}
  function wj(k,v){try{localStorage.setItem(k,JSON.stringify(v));}catch(e){}}
  var st=rj(SKEY,{});
  var SANS='"Noto Sans TC","PingFang TC","Microsoft JhengHei",system-ui,sans-serif';
  var SERIF='"Noto Serif TC","Source Han Serif TC","PingFang TC","Microsoft JhengHei",Georgia,serif';

  function applySettings(){
    if(st.theme&&st.theme!=='light')doc.setAttribute('data-theme',st.theme);
    else doc.removeAttribute('data-theme');
    body.style.fontSize   = st.fontPx? st.fontPx+'px' : '';
    body.style.lineHeight = st.lineHeight? st.lineHeight : '';
    body.style.fontFamily = st.font==='sans'? SANS : (st.font==='serif'? SERIF : '');
  }
  function save(){ wj(SKEY,st); applySettings(); syncUI(); }

  // 樣式（面板 / 浮動鈕）
  var css=document.createElement('style');
  css.textContent=`
  .rd-fabs{position:fixed;right:14px;bottom:14px;z-index:70;display:flex;flex-direction:column;gap:10px}
  .rd-fab{width:46px;height:46px;border-radius:50%;border:0;cursor:pointer;
   display:flex;align-items:center;justify-content:center;text-decoration:none;
   background:var(--red);color:#fff;font:700 15px/1 "Noto Sans TC",system-ui,sans-serif;
   box-shadow:0 4px 14px rgba(0,0,0,.28);-webkit-tap-highlight-color:transparent}
  .rd-fab:active{transform:scale(.94)}
  .rd-panel{position:fixed;right:14px;bottom:70px;z-index:71;width:250px;max-width:calc(100vw - 28px);
   background:var(--card);color:var(--ink);border:1px solid var(--line);border-radius:14px;
   box-shadow:0 12px 34px rgba(0,0,0,.30);padding:14px 16px;
   font-family:"Noto Sans TC","PingFang TC",system-ui,sans-serif}
  .rd-panel[hidden]{display:none}
  .rd-row{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:10px 0}
  .rd-row>span{color:var(--grey);font-size:14px;flex:0 0 auto}
  .rd-seg,.rd-step{display:flex;border:1px solid var(--line);border-radius:9px;overflow:hidden}
  .rd-seg button,.rd-step button{border:0;background:transparent;color:var(--ink);
   padding:7px 10px;font-size:14px;cursor:pointer;-webkit-tap-highlight-color:transparent}
  .rd-seg button.on{background:var(--red);color:#fff}
  .rd-step b{min-width:44px;text-align:center;align-self:center;font-size:14px;font-variant-numeric:tabular-nums}
  .rd-reset{width:100%;border:1px solid var(--line);background:transparent;color:var(--grey);
   border-radius:9px;padding:8px;cursor:pointer;font-size:13px}
  .rd-toast{position:fixed;left:50%;bottom:78px;transform:translateX(-50%);z-index:80;
   background:rgba(0,0,0,.82);color:#fff;padding:9px 15px;border-radius:999px;font-size:13px;
   opacity:0;transition:opacity .25s;pointer-events:none}
  .rd-toast.show{opacity:1}
  `;
  document.head.appendChild(css);

  var fabs=document.createElement('div'); fabs.className='rd-fabs';
  fabs.innerHTML='<a class="rd-fab" href="../index.html" title="回目錄">☰</a>'
    +'<button class="rd-fab" id="rdSet" title="閱讀設定">Aa</button>';
  document.body.appendChild(fabs);

  var panel=document.createElement('div'); panel.className='rd-panel'; panel.hidden=true;
  panel.innerHTML=
    '<div class="rd-row"><span>背景</span><div class="rd-seg" data-k="theme">'
    +'<button data-v="light">白</button><button data-v="sepia">米</button>'
    +'<button data-v="grey">灰</button><button data-v="dark">夜</button></div></div>'
    +'<div class="rd-row"><span>字型</span><div class="rd-seg" data-k="font">'
    +'<button data-v="serif">明體</button><button data-v="sans">黑體</button></div></div>'
    +'<div class="rd-row"><span>字級</span><div class="rd-step" data-k="fontPx">'
    +'<button data-d="-1">A−</button><b id="rdFs">–</b><button data-d="1">A＋</button></div></div>'
    +'<div class="rd-row"><span>行距</span><div class="rd-step" data-k="lineHeight">'
    +'<button data-d="-1">−</button><b id="rdLh">–</b><button data-d="1">＋</button></div></div>'
    +'<div class="rd-row"><button id="rdReset" class="rd-reset">恢復預設</button></div>';
  document.body.appendChild(panel);

  document.getElementById('rdSet').onclick=function(){panel.hidden=!panel.hidden;};

  function curFs(){return st.fontPx||Math.round(parseFloat(getComputedStyle(body).fontSize))||18;}
  function curLh(){return st.lineHeight||1.85;}

  panel.addEventListener('click',function(e){
    var b=e.target.closest('button'); if(!b)return;
    var seg=b.closest('.rd-seg'), step=b.closest('.rd-step');
    if(b.id==='rdReset'){st={};save();return;}
    if(seg){st[seg.dataset.k]=b.dataset.v;save();return;}
    if(step){
      var k=step.dataset.k, d=parseInt(b.dataset.d,10);
      if(k==='fontPx'){st.fontPx=Math.min(26,Math.max(13,curFs()+d));}
      else{st.lineHeight=Math.round((curLh()+d*0.05)*100)/100;
           st.lineHeight=Math.min(2.4,Math.max(1.35,st.lineHeight));}
      save();return;
    }
  });

  function syncUI(){
    panel.querySelectorAll('.rd-seg[data-k="theme"] button').forEach(function(x){
      x.classList.toggle('on', x.dataset.v===(st.theme||'light'));});
    panel.querySelectorAll('.rd-seg[data-k="font"] button').forEach(function(x){
      x.classList.toggle('on', x.dataset.v===(st.font||'serif'));});
    var fs=document.getElementById('rdFs'), lh=document.getElementById('rdLh');
    if(fs)fs.textContent=curFs()+'px';
    if(lh)lh.textContent=st.lineHeight?st.lineHeight.toFixed(2):'標準';
  }

  // ---- 閱讀進度 ----
  var bar=document.createElement('div'); bar.id='econ-progress'; document.body.appendChild(bar);
  function maxScroll(){return Math.max(1,doc.scrollHeight-window.innerHeight);}
  function curPct(){return Math.min(1,Math.max(0,(window.scrollY||window.pageYOffset)/maxScroll()));}
  var prog=rj(PKEY,{}), tmr;
  function paint(){bar.style.width=(curPct()*100)+'%';}
  function saveProg(){var pct=curPct(),prev=prog[slug]||{};
    prog[slug]={pct:pct,read:(prev.read||pct>=0.9),ts:Date.now()};wj(PKEY,prog);}
  var toastEl;
  function toast(msg){if(!toastEl){toastEl=document.createElement('div');toastEl.className='rd-toast';
    document.body.appendChild(toastEl);} toastEl.textContent=msg; toastEl.classList.add('show');
    setTimeout(function(){toastEl.classList.remove('show');},1800);}

  applySettings(); syncUI();
  window.addEventListener('load',function(){
    var p=prog[slug];
    if(p&&p.pct>0.02&&p.pct<0.985){window.scrollTo(0,p.pct*maxScroll());toast('已回到上次閱讀位置');}
    paint();
  });
  window.addEventListener('scroll',function(){paint();clearTimeout(tmr);tmr=setTimeout(saveProg,400);},{passive:true});
  window.addEventListener('pagehide',saveProg);
  document.addEventListener('visibilitychange',function(){if(document.hidden)saveProg();});
})();
