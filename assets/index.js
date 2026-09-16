
(function(){
  var SKEY='econ.settings', PKEY='econ.progress';
  function rj(k,d){try{return JSON.parse(localStorage.getItem(k))||d;}catch(e){return d;}}
  function wj(k,v){try{localStorage.setItem(k,JSON.stringify(v));}catch(e){}}
  var st=rj(SKEY,{}), prog=rj(PKEY,{}), doc=document.documentElement;
  function applyTheme(){if(st.theme&&st.theme!=='light')doc.setAttribute('data-theme',st.theme);
    else doc.removeAttribute('data-theme');}
  applyTheme();

  var btn=document.getElementById('themeBtn'), order=['light','sepia','grey','dark'];
  function icon(){btn.textContent=st.theme==='dark'?'🌙':(st.theme==='sepia'?'📖':(st.theme==='grey'?'▧':'◐'));}
  if(btn){icon();btn.onclick=function(){var i=order.indexOf(st.theme||'light');
    st.theme=order[(i+1)%order.length];wj(SKEY,st);applyTheme();icon();};}

  document.querySelectorAll('a.card').forEach(function(a){
    var m=(a.getAttribute('href')||'').match(/issues\/(.+)\.html/); if(!m)return;
    var p=prog[m[1]]; if(!p)return;
    var b=document.createElement('span'); b.className='badge';
    if(p.read){a.classList.add('read');b.className='badge done';b.textContent='✓ 已讀';}
    else if(p.pct>0.02){b.textContent='繼續 '+Math.round(p.pct*100)+'%';}
    else return;
    a.appendChild(b);
  });
})();
