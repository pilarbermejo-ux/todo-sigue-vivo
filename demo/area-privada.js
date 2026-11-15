/* Todo Sigue Vivo · app de la POC (dueños y cuidadores) conectada a servidor.py */
(function(){
"use strict";

/* ---------- arranque y sesión ---------- */
const P=new URLSearchParams(location.search);
const FRAME=P.get("frame")||"main";
const IN_FRAME=window.top!==window;
const TK="tsv-token-"+FRAME;
const LOGIN=P.get("login");
if(IN_FRAME)document.documentElement.classList.add("in-frame");
let token=null;try{token=localStorage.getItem(TK)}catch(e){}
let ME=null,CAT=null,ES=null;
const DR={};            // borradores de campos (chat, notas…) que sobreviven a los repintados
const TYPING={};        // candidatura -> hasta cuándo mostrar «escribiendo»
let W=null;             // borrador del anuncio

/* ---------- iconos ---------- */
const I={
  leaf:'<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 19c0-8 5-13 14-14 0 9-5 14-13 14z" fill="currentColor"/></svg>',
  home:'<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/></svg>',
  ad:'<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="4" width="16" height="16" rx="3"/><path d="M8 9h8M8 13h8M8 17h5"/></svg>',
  chat:'<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 5h16v11H9l-5 4z"/></svg>',
  bell:'<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4z"/><path d="M10 20a2 2 0 0 0 4 0"/></svg>',
  house:'<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 21c-4-3-7-6-7-10a7 7 0 0 1 14 0c0 4-3 7-7 10z"/><circle cx="12" cy="11" r="2.5"/></svg>',
  inbox:'<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 13l2-8h12l2 8v6H4z"/><path d="M4 13h5l1 2h4l1-2h5"/></svg>',
  cal:'<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="5" width="16" height="15" rx="2"/><path d="M4 10h16M9 3v4M15 3v4"/></svg>',
  user:'<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 21c1-4 4-6 8-6s7 2 8 6"/></svg>',
  plus:'<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
  cat:'<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 20v-9l-1-6 4 3h8l4-3-1 6v9z"/><path d="M9.5 13h.01M14.5 13h.01M11 16h2"/></svg>',
  lizard:'<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3c2 0 3 2 3 4v4c0 3-1 5-3 6-2 1-2 3 0 4"/><path d="M12 3c-2 0-3 2-3 4v4c0 3 1 5 3 6"/><path d="M9 9H6M15 9h3M9 14H6M15 14h3"/></svg>',
  plant:'<svg class="ic" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 15h10l-1.5 6h-7z"/><path d="M12 15V8"/><path d="M12 10c0-3-2-5-5-5 0 3 2 5 5 5zM12 8c0-3 2-5 5-5 0 3-2 5-5 5z"/></svg>',
  lock:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>',
  warn:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M12 3l10 18H2z"/><path d="M12 10v5M12 18h.01"/></svg>',
  info:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5h.01"/></svg>',
  sun:'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2M5 5l1.5 1.5M17.5 17.5L19 19M5 19l1.5-1.5M17.5 6.5L19 5"/></svg>',
  send:'<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>',
  back:'<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 6l-6 6 6 6"/></svg>',
  moon:'<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9z"/></svg>',
  x:'<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>',
  cam:'<svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/></svg>'
};
const icoCat=c=>c==="pl"?I.plant:c==="ex"?I.lizard:I.cat;

/* ---------- utilidades ---------- */
const $=s=>document.querySelector(s);
const esc=s=>String(s==null?"":s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const pad=n=>String(n).padStart(2,"0");
const hhmm=t=>{const d=new Date(t);return pad(d.getHours())+":"+pad(d.getMinutes())};
const MES=["ene","feb","mar","abr","may","jun","jul","ago","sept","oct","nov","dic"];
const DIA=["dom","lun","mar","mié","jue","vie","sáb"];
const parseD=s=>{const [y,m,d]=s.split("-").map(Number);return new Date(y,m-1,d)};
const iso=d=>d.getFullYear()+"-"+pad(d.getMonth()+1)+"-"+pad(d.getDate());
const fmtD=s=>{const d=typeof s==="string"?parseD(s):s;return d.getDate()+" "+MES[d.getMonth()]};
const fmtDL=d=>DIA[d.getDay()]+" "+d.getDate()+" "+MES[d.getMonth()];
const addDays=(d,n)=>{const x=new Date(d);x.setDate(x.getDate()+n);return x};
const eur=n=>{n=Math.round(n*100)/100;return n.toLocaleString("es-ES",{minimumFractionDigits:n%1?2:0,maximumFractionDigits:2})+" €"};
const plural=(n,a,b)=>n+" "+(n===1?a:b);
const today=()=>{const d=new Date();d.setHours(0,0,0,0);return d};
const FR={m:"Mañana",t:"Tarde",n:"Noche"};
const km=k=>String(k).replace(".",",");
const cuando=t=>{const d=new Date(t),h=today();return d>=h?hhmm(t):fmtD(d)+" · "+hhmm(t)};
const relTexto=t=>t.replace(/\[dato oculto\]/g,'<span class="hid">dato oculto</span>');

function avatar(u,lg,cls){
  const n=(u&&u.nombre)||"?";
  const tono=u&&u.rol==="dueno"?"":(u&&u.id%3===0?"sv":u&&u.id%3===1?"":"dk");
  return `<span class="av ${cls||tono}${lg?" lg":""}" aria-hidden="true">${esc(n[0])}</span>`;
}
const appAv=()=>`<span class="av dk" aria-hidden="true"><span style="width:20px;height:20px;color:#fff">${I.leaf}</span></span>`;

/* ---------- API ---------- */
async function api(path,body){
  let r;
  try{
    r=await fetch("/api"+path,{method:body!==undefined?"POST":"GET",headers:Object.assign({"Content-Type":"application/json"},token?{Authorization:"Bearer "+token}:{}),body:body!==undefined?JSON.stringify(body):undefined});
  }catch(e){offline(true);throw new Error("No hay conexión con el servidor. Vuelve a intentarlo.")}
  offline(false);
  let j={};try{j=await r.json()}catch(e){}
  if(r.status===401&&j.auth===false){await perderSesion();throw new Error(j.error)}
  if(!r.ok)throw new Error(j.error||"Algo ha fallado");
  return j;
}
function offline(on){let el=$("#offline");if(on&&!el){el=document.createElement("p");el.id="offline";el.className="offline";el.setAttribute("role","status");el.textContent="No hay conexión con el servidor. Reintentando…";document.body.appendChild(el)}if(!on&&el)el.remove()}
function track(nombre,datos){fetch("/api/ev",{method:"POST",headers:Object.assign({"Content-Type":"application/json"},token?{Authorization:"Bearer "+token}:{}),body:JSON.stringify({nombre,datos:datos||{}})}).catch(()=>{})}
function setToken(t){token=t;try{t?localStorage.setItem(TK,t):localStorage.removeItem(TK)}catch(e){}}
async function perderSesion(){setToken(null);ME=null;if(ES){ES.close();ES=null}if(LOGIN&&!perderSesion.busy){perderSesion.busy=true;try{await autoLogin()}finally{perderSesion.busy=false}}else location.hash="#/entrar"}
async function autoLogin(){const j=await api("/test/entrar",{correo:LOGIN});setToken(j.token);await cargarYo();conectarStream()}
async function cargarYo(){ME=await api("/yo");if(!CAT)CAT=await api("/catalogo");try{const k="tsv-wiz-"+FRAME+"-"+ME.id;W=JSON.parse(localStorage.getItem(k))||null}catch(e){}}

/* ---------- tiempo real ---------- */
function conectarStream(){
  if(ES)ES.close();if(!token)return;
  ES=new EventSource("/api/stream?token="+encodeURIComponent(token));
  ES.onmessage=e=>{let m;try{m=JSON.parse(e.data)}catch(_){return}onEvent(m)};
  ES.onerror=()=>{};
}
let refreshT=null;
function refresh(){clearTimeout(refreshT);refreshT=setTimeout(()=>route("evento"),120)}
async function onEvent(m){
  if(m.type==="reset"){setToken(null);location.reload();return}
  if(m.type==="typing"){TYPING[m.cand]=Date.now()+3500;if(curView()==="mensajes")refresh();setTimeout(()=>{if(curView()==="mensajes")refresh()},3600);return}
  if(m.type==="seq"){pedirSeq(m);return}
  if(m.type==="notif"){toast(m.notif);navNotif(m.notif)}
  if(m.type==="msg"&&m.cand)delete TYPING[m.cand];
  try{ME=await api("/yo")}catch(e){}
  refresh();
}
function navNotif(n){
  if(!("Notification" in window)||Notification.permission!=="granted"||!document.hidden)return;
  try{const x=new Notification(n.texto,{body:n.sub||"",tag:"tsv-"+n.id});x.onclick=()=>{window.focus();location.hash=n.enlace||"#/inicio";x.close()}}catch(e){}
}

/* ---------- avisos emergentes ---------- */
function toast(n){
  const box=$("#toasts");const el=document.createElement("div");el.className="toast";
  el.innerHTML=`${appAv()}<div style="cursor:pointer"><p>${esc(n.texto)}</p><small class="m">${hhmm(n.creada)}${n.sub?" · "+esc(n.sub):""}</small></div><button type="button" aria-label="Cerrar">${I.x}</button>`;
  el.querySelector("div").onclick=()=>{abrirNotif(n);el.remove()};
  el.querySelector("button").onclick=()=>el.remove();
  box.prepend(el);setTimeout(()=>el.remove(),7000);
}
async function abrirNotif(n){try{await api("/notifs/leidas",{id:n.id})}catch(e){}track("notif_abierta",{tipo:n.tipo});location.hash=n.enlace||"#/inicio";refresh()}
function flash(texto,ok){toast({texto,sub:"",creada:Date.now(),enlace:location.hash})}

/* ---------- repintado ---------- */
let seq=0,lastHash="";
function curView(){return (location.hash.replace(/^#\/?/,"")||"inicio").split("/")[0]}
function draw(html){
  const ae=document.activeElement;const id=ae&&ae.id;const sel=ae&&"selectionStart" in ae?[ae.selectionStart,ae.selectionEnd]:null;
  const m=$("#msgs");const atBottom=m?m.scrollHeight-m.scrollTop-m.clientHeight<80:true;
  const sx=window.scrollY;
  $("#root").innerHTML=html;
  if(id){const el=document.getElementById(id);if(el){el.focus({preventScroll:true});if(sel&&el.setSelectionRange)try{el.setSelectionRange(sel[0],sel[1])}catch(e){}}}
  const m2=$("#msgs");if(m2&&(atBottom||lastHash!==location.hash))m2.scrollTop=m2.scrollHeight;
  if(lastHash!==location.hash){window.scrollTo(0,0);lastHash=location.hash;const h=$("#main h1");if(h&&!id){h.setAttribute("tabindex","-1")}}else window.scrollTo(0,sx);
}
async function route(soft){
  const my=++seq;
  const h=location.hash.replace(/^#\/?/,"")||"inicio";
  const [view,arg]=h.split("/");
  if(!token&&LOGIN){try{await autoLogin()}catch(e){}}
  if(!token){if(view!=="registro"&&view!=="entrar"){location.replace("#/entrar");return}draw(view==="registro"?vRegistro():vEntrar());return}
  if(!ME){try{await cargarYo();conectarStream()}catch(e){draw(`<div class="login-form"><div class="err-box">${I.warn}<span>${esc(e.message)}</span></div></div>`);return}}
  if(view==="entrar"||view==="registro"){location.replace("#/inicio");return}
  const R=ME.rol==="dueno"?RD:RC;
  const fn=R[view]||R.inicio;
  if(!soft){draw(shell(view,'<div class="loading" role="status" aria-label="Cargando"></div>'));track("vista",{v:view})}
  if(soft==="evento"&&(view==="publicar"||view==="casa"||view==="perfil")){paintBadges();return}
  let html;
  try{html=await fn(arg)}catch(e){html=`<div class="err-box" role="alert">${I.warn}<span>${esc(e.message)}</span></div>`}
  if(my!==seq)return;
  draw(shell(view,html));
  document.title=(TITLES[view]||"Todo Sigue Vivo")+" · Todo Sigue Vivo";
}
const TITLES={inicio:"Inicio",publicar:"Publicar anuncio",anuncio:"Mi anuncio",mensajes:"Mensajes",avisos:"Avisos",casa:"Mi casa",solicitud:"Solicitud",servicios:"Mis servicios",perfil:"Perfil",reserva:"Reserva",entrar:"Entrar",registro:"Crear cuenta"};
function paintBadges(){const nn=ME.no_leidos.notifs,nc=ME.no_leidos.chats;document.querySelectorAll("[data-badge=notifs]").forEach(e=>{e.textContent=nn;e.hidden=!nn});document.querySelectorAll("[data-badge=chats]").forEach(e=>{e.textContent=nc;e.hidden=!nc})}

/* ---------- estructura ---------- */
function shell(view,content){
  const d=ME.rol==="dueno";
  const nav=d?[["inicio","Inicio",I.home],["anuncio","Mi anuncio",I.ad],["mensajes","Mensajes",I.chat,"chats"],["avisos","Avisos",I.bell,"notifs"],["casa","Mi casa",I.house]]
             :[["inicio","Solicitudes",I.inbox],["servicios","Mis servicios",I.cal],["mensajes","Mensajes",I.chat,"chats"],["avisos","Avisos",I.bell,"notifs"],["perfil","Perfil",I.user]];
  const nn=ME.no_leidos.notifs,nc=ME.no_leidos.chats;const bn={notifs:nn,chats:nc};
  const cur=view==="solicitud"?"inicio":view==="reserva"?(d?"anuncio":"servicios"):view==="publicar"?"anuncio":view;
  return `<div class="app">
  <aside class="side" aria-label="Menú">
    <a class="wordmark" href="../web/index.html" target="_top">${I.leaf}Todo Sigue Vivo</a>
    ${d?`<a class="btn primary side-new" href="#/publicar">${I.plus} Publicar anuncio</a>`:""}
    <nav class="navlist">${nav.map(([k,t,ic,b])=>`<a href="#/${k}" ${cur===k?'aria-current="page"':""}>${ic}<span>${t}</span>${b?`<span class="badge" data-badge="${b}" ${bn[b]?"":"hidden"}>${bn[b]}</span>`:""}</a>`).join("")}</nav>
    <div class="me">${avatar(ME)}<div><b>${esc(ME.nombre)} ${esc(ME.apellido||"")}</b><small>${esc(ME.barrio||ME.cp)} · <span class="role ${d?"du":""}">${d?"Dueña/o":"Cuidador/a"}</span></small><button type="button" class="link" data-act="logout" style="font-size:13px;padding:2px 0">Salir</button></div>
      <button class="iconbtn" type="button" data-act="theme" aria-label="Cambiar tema claro u oscuro" style="margin-left:auto">${I.moon}</button></div>
  </aside>
  <header class="mtop"><span style="display:flex;align-items:center;gap:8px">${avatar(ME)}<span><b style="display:block;line-height:1.1">${esc(ME.nombre)}</b><span class="role ${d?"du":""}">${d?"Dueña/o":"Cuidador/a"}</span></span></span>
    <div style="display:flex;gap:8px"><button class="iconbtn" type="button" data-act="theme" aria-label="Cambiar tema">${I.moon}</button><a class="iconbtn" href="#/avisos" aria-label="Avisos">${I.bell}<span class="dot" data-badge="notifs" ${nn?"":"hidden"}>${nn}</span></a></div></header>
  <main class="main" id="main">${content}</main>
  <nav class="tabbar" aria-label="Menú">${nav.filter(n=>n[0]!=="avisos").map(([k,t,ic,b])=>`<a href="#/${k}" ${cur===k?'aria-current="page"':""}>${ic}<span>${t}</span>${b?`<span class="dot" data-badge="${b}" ${bn[b]?"":"hidden"}>${bn[b]}</span>`:""}</a>`).join("")}</nav>
</div>`;
}
const head=(t,sub,lbl,right)=>`<div class="head"><div>${lbl?`<p class="lbl">${lbl}</p>`:""}<h1>${t}</h1>${sub?`<p>${sub}</p>`:""}</div>${right||""}</div>`;
const errBox=m=>`<div class="err-box" role="alert">${I.warn}<span>${esc(m)}</span></div>`;

/* ---------- entrar y registro ---------- */
const CUENTAS=[["marta","Marta","Dueña · gata y plantas delicadas · Malasaña","du"],["pablo","Pablo","Dueño coleccionista · 19 plantas · Chamberí","du"],["alex","Álex","Dueño de exóticos · gecko y pogona · Lavapiés","du"],["lucas","Lucas","Dueño con gata · Hortaleza","du"],["irene","Irene","Cuidadora nueva · Malasaña","cu"],["marisa","Marisa","Cuidadora de gatos · Fuencarral-El Pardo","cu"],["ruben","Rubén","Cuidador de gatos · Fuencarral-El Pardo","cu"],["noa","Noa","Cuidadora nueva · Fuencarral-El Pardo","cu"]];
function vEntrar(){
  return `<div class="login">
  <div class="login-art"><img src="img/hero.jpg" alt=""><span class="ai-note">Imagen creada con IA</span>
    <h1>Vete tranquilo. En casa, todo sigue vivo.</h1><p>Entra para publicar un anuncio, o para encontrar casas que cuidar en tu barrio.</p></div>
  <div class="login-form"><form id="f-login" novalidate>
    <a class="wordmark" href="../web/index.html">${I.leaf}Todo Sigue Vivo</a>
    <h2>Entrar</h2>
    <div id="login-err"></div>
    <div class="field"><label for="l-mail">Correo <small>· obligatorio</small></label><input class="input" id="l-mail" type="email" autocomplete="username"></div>
    <div class="field"><label for="l-pass">Contraseña <small>· obligatorio</small></label><input class="input" id="l-pass" type="password" autocomplete="current-password"></div>
    <button class="btn primary block" type="submit">Entrar</button>
    <p style="font-size:15px">¿Aún no tienes cuenta? <a href="#/registro">Crear una cuenta</a></p>
    <div class="field"><p class="lbl">Cuentas de prueba</p><div class="quick-accounts">${CUENTAS.map(([k,n,d,r])=>`<button type="button" data-quick-login="${k}@ejemplo.com">${avatar({nombre:n,rol:r==="du"?"dueno":"cuidador",id:k.length})}<span><b>${n}</b><small>${d}</small></span><span class="role ${r}">${r==="du"?"Dueño":"Cuidadora"}</span></button>`).join("")}</div></div>
    <a href="../web/index.html" class="muted" style="font-size:14px">← Volver a la web</a>
  </form></div></div>`;
}
function vRegistro(){
  return `<div class="login">
  <div class="login-art"><img src="img/hero.jpg" alt=""><span class="ai-note">Imagen creada con IA</span><h1>Cuidadores de barrio que saben de plantas y animales.</h1></div>
  <div class="login-form"><form id="f-reg" novalidate>
    <a class="wordmark" href="../web/index.html">${I.leaf}Todo Sigue Vivo</a>
    <h2>Crear una cuenta</h2>
    <div id="reg-err"></div>
    <fieldset class="field" style="border:0;padding:0;margin:0"><legend class="flabel" style="margin-bottom:6px">¿Qué quieres hacer? <small>· obligatorio</small></legend>
      <div class="seg" style="grid-template-columns:1fr 1fr"><label><input type="radio" name="rol" value="dueno" checked><span>Me voy de viaje</span></label><label><input type="radio" name="rol" value="cuidador"><span>Quiero cuidar</span></label></div></fieldset>
    <div class="field"><label for="r-nombre">Nombre <small>· obligatorio</small></label><input class="input" id="r-nombre" autocomplete="given-name"><p class="error" id="e-nombre" hidden></p></div>
    <div class="field"><label for="r-correo">Correo <small>· obligatorio</small></label><input class="input" id="r-correo" type="email" autocomplete="email"><p class="error" id="e-correo" hidden></p></div>
    <div class="field"><label for="r-clave">Contraseña <small>· al menos 8 caracteres</small></label><input class="input" id="r-clave" type="password" autocomplete="new-password"><p class="error" id="e-clave" hidden></p></div>
    <div class="field"><label for="r-cp">Código postal <small>· obligatorio</small></label><input class="input" id="r-cp" inputmode="numeric" maxlength="5" autocomplete="postal-code"><p class="error" id="e-cp" hidden></p><small>Prueba piloto en Madrid.</small></div>
    <button class="btn primary block" type="submit">Crear cuenta</button>
    <p class="hint">Prueba de concepto: los datos se guardan solo en este ordenador.</p>
    <p style="font-size:15px">¿Ya tienes cuenta? <a href="#/entrar">Entrar</a></p>
  </form></div></div>`;
}

/* ================================================================ DUEÑO */
function track5(a){
  const st=a?a.estado:null;
  const k=!a?0:st==="completado"?5:st==="en_curso"||st==="reservado"?4:st==="asignado"?3:a.n_cands?2:1;
  const steps=["Publicado","Candidaturas","Encuentro","Reserva","Terminado"];
  return `<ol class="track" style="grid-template-columns:repeat(5,minmax(0,1fr))" aria-label="Progreso">${steps.map((t,i)=>`<li class="${i<k?"on":""} ${i===k-1&&k<5?"now":""}">${t}</li>`).join("")}</ol>`;
}
function estadoBadge(a){
  const m={abierto:["st-pilot","Abierto"],asignado:["st-pilot","Encuentro previo"],reservado:["st-ok","Reservado"],en_curso:["st-ok","En curso"],completado:["st-off","Terminado"],cancelado:["st-off","Cancelado"]};
  const [c,t]=m[a.estado]||["st-off",a.estado];return `<span class="status ${c}">${t}</span>`;
}
const serChip=s=>`<span class="chip ${s.cat==="pl"?"pl":"an"}">${s.cantidad>1?s.cantidad+" ":""}${esc(s.nombre)}</span>`;
function serRow(s,extra){
  return `<div class="ser"><span class="sic ${s.cat==="pl"?"pl":"an"}">${icoCat(s.cat)}</span><div><b>${s.cantidad>1?s.cantidad+" ":""}${esc(s.nombre)}</b><small>${esc(s.especie)} · cada ${plural(s.cada,"día","días")} · dificultad ${s.dif}/5${s.medicacion?" · medicación":""}</small></div>${extra||`<span class="chip ${s.cat==="pl"?"pl":"an"}">${s.cat==="pl"?"Planta":s.cat==="ex"?"Exótico":"Animal"}</span>`}</div>`;
}
function notifList(list){
  if(!list.length)return `<p class="muted">Aún no tienes avisos.</p>`;
  return list.map(n=>`<button type="button" class="notif ${n.leida?"":"unread"}" data-notif='${esc(JSON.stringify({id:n.id,enlace:n.enlace,tipo:n.tipo}))}'>${n.tipo==="calor"?`<span class="av" style="background:var(--azafran-soft);color:var(--azafran)" aria-hidden="true"><span style="width:22px;height:22px">${I.sun}</span></span>`:appAv()}<span><p>${esc(n.texto)}</p>${n.sub?`<small>${esc(n.sub)}</small>`:""}</span><span class="t m">${cuando(n.creada)}</span></button>`).join("");
}

async function vInicioD(){
  const [anuncios,notifs,casa]=await Promise.all([api("/anuncios/mios"),api("/notifs"),api("/casa")]);
  const activo=anuncios.find(a=>["abierto","asignado","reservado","en_curso"].includes(a.estado))||anuncios.find(a=>a.estado==="completado");
  let top;
  if(!ME.zona_activa){
    top=`<section class="waitlist"><p class="lbl" style="color:var(--lavanda-200)">${esc(ME.barrio||ME.cp)} · lista de espera</p><h2 style="font-size:30px">Aún no hay cuidadores en tu barrio. Te avisamos.</h2><p>Estás apuntado con tu código postal ${esc(ME.cp)} y lo que vive en tu casa. Cuando abramos tu zona, conservarás tu ficha.</p><a class="btn ghost" style="color:#fff;box-shadow:inset 0 0 0 1.5px #fff;justify-self:start" href="#/casa">Completar mi ficha</a></section>`;
  }else if(activo){
    top=`<section class="card ad-head"><div class="ad-top"><div><p class="lbl">Tu anuncio</p><h2>${esc(activo.plan.servicio)} · ${fmtD(activo.inicio)} – ${fmtD(activo.fin)}</h2></div>${estadoBadge(activo)}</div>${track5(activo)}
      <div class="stats"><div><b>${activo.avisados}</b><span>avisados</span></div><div><b>${activo.n_cands}</b><span>candidaturas</span></div>${activo.elegido?`<div><b style="font-size:20px">${esc(activo.elegido.nombre)}</b><span>tu cuidadora</span></div>`:""}</div>
      <a class="btn primary" style="justify-self:start" href="#/${["reservado","en_curso","completado"].includes(activo.estado)||activo.estado==="asignado"?"reserva":"anuncio"}/${activo.id}">${activo.estado==="abierto"?(activo.n_cands?"Ver candidaturas":"Ver mi anuncio"):activo.estado==="completado"?"Ver y valorar":"Ver la reserva"}</a></section>`;
  }else{
    top=`<section class="empty"><p class="lbl" style="color:var(--lavanda-200)">Aún no tienes anuncios activos</p><h2>¿Te vas pronto? Cuéntanos qué hay que cuidar.</h2><p>Usamos la ficha de tu casa: no tienes que explicar nada dos veces. Solo avisamos a los cuidadores que encajan contigo.</p><a class="btn" href="#/publicar">Publicar un anuncio →</a></section>`;
  }
  return head("Hola, "+esc(ME.nombre),fmtDL(new Date())+" · "+esc(ME.barrio||ME.cp))+`
  <div class="grid2"><div class="stack">${top}
    ${avisoNavegador()}
    <section class="card"><div class="ad-top" style="margin-bottom:8px"><h2 style="font-size:22px">Últimos avisos</h2><a href="#/avisos" style="font-size:14px">Ver todos</a></div>${notifList(notifs.slice(0,4))}</section></div>
  <section class="card"><div class="ad-top"><div><p class="lbl">Ficha de la casa</p><h2 style="font-size:22px">Lo que vive en tu casa</h2></div>${casa.seres.length?`<span class="status st-ok">${plural(casa.seres.length,"ser vivo","seres vivos")}</span>`:`<span class="status st-pend">Incompleta</span>`}</div>
    <div style="margin-top:8px">${casa.seres.map(s=>serRow(s)).join("")||`<p class="muted">Añade al menos un animal o planta.</p>`}</div><a href="#/casa" style="font-size:14px">Editar la ficha</a></section></div>`;
}
function avisoNavegador(){
  if(IN_FRAME||!("Notification" in window)||Notification.permission!=="default")return "";
  return `<section class="info" style="align-items:center">${I.bell.replace('class="ic"','width="22" height="22"')}<span style="flex:1">Activa los avisos del navegador para enterarte aunque no tengas esta pestaña delante.</span><button class="btn ghost small" type="button" data-act="notif-perm">Activar</button></section>`;
}

/* ----- publicar ----- */
function wDefault(seres){const s=addDays(today(),11);return {inicio:iso(s),fin:iso(addDays(s,5)),seres:seres.map(x=>x.id),franja:"t",habitada:false,opt:null,nota:"",step:1,res:null}}
function wSave(){try{localStorage.setItem("tsv-wiz-"+FRAME+"-"+ME.id,JSON.stringify(Object.assign({},W,{res:null})))}catch(e){}}
function wValid(){
  const e={};const t1=addDays(today(),1);
  if(!W.inicio)e.inicio="Elige el primer día.";else if(parseD(W.inicio)<t1)e.inicio="El primer día tiene que ser a partir de mañana.";
  if(!W.fin)e.fin="Elige el día de vuelta.";else if(W.inicio&&parseD(W.fin)<=parseD(W.inicio))e.fin="La vuelta tiene que ser después del primer día.";else if(W.inicio&&(parseD(W.fin)-parseD(W.inicio))/864e5>30)e.fin="Como máximo 30 días por anuncio.";
  if(!W.seres.length)e.seres="Elige al menos un animal o planta.";
  return e;
}
let countT=null;
function wCount(now){
  clearTimeout(countT);
  countT=setTimeout(async()=>{
    if(Object.keys(wValid()).length){W.res=null;route(true);return}
    try{W.res=await api("/idoneos",W)}catch(e){W.res={error:e.message}}
    if(curView()==="publicar")route(true).then(()=>{});
    const b=$("#big-n");if(b){b.classList.remove("bump");void b.offsetWidth;b.classList.add("bump")}
  },now?0:160);
}
async function vPublicar(){
  if(!ME.zona_activa)return head("Publicar un anuncio")+`<section class="waitlist"><h2 style="font-size:28px">Aún no hay cuidadores en tu barrio. Te avisamos.</h2><p>Cuando abramos ${esc(ME.barrio||ME.cp)}, podrás publicar con tu ficha tal y como la tienes.</p></section>`;
  const [anuncios,casa]=await Promise.all([api("/anuncios/mios"),api("/casa")]);
  const act=anuncios.find(a=>["abierto","asignado","reservado","en_curso"].includes(a.estado));
  if(act)return head("Ya tienes un anuncio activo")+`<p>En esta prueba solo puede haber uno a la vez. <a href="#/anuncio/${act.id}">Ver mi anuncio</a></p>`;
  if(!casa.seres.length)return head("Publicar un anuncio")+`<section class="card stack"><p>Primero añade a tu ficha lo que vive en tu casa. Solo se hace una vez.</p><a class="btn primary" style="justify-self:start" href="#/casa">Completar mi ficha</a></section>`;
  if(!W)W=wDefault(casa.seres);
  W.seres=W.seres.filter(id=>casa.seres.some(s=>s.id===id));
  const seresSel=casa.seres.filter(s=>W.seres.includes(s.id));
  if(!W.opt)W.opt={del:seresSel.some(s=>s.cat==="pl"&&s.dif>=4),esp:false,rat:false,serv:false,fr:false};
  if(!W.res&&!Object.keys(wValid()).length){wCount(true)}
  const errs=wValid(),step=W.step,r=W.res||{},p=r.plan;
  const n=r.n;const urgent=!errs.inicio&&W.inicio&&(parseD(W.inicio)-today())/864e5<2;
  let body="";
  if(step===1){
    body=`<div class="field"><span class="flabel">¿Cuándo te vas? <small>· obligatorio</small></span>
      <div class="row2"><div class="field"><label for="w-ini" style="font-size:13.5px">Primer día sin ti</label><input class="input" type="date" id="w-ini" data-w="inicio" value="${W.inicio}" min="${iso(addDays(today(),1))}" ${errs.inicio?'aria-invalid="true" aria-describedby="e-ini"':""}></div>
      <div class="field"><label for="w-fin" style="font-size:13.5px">Vuelves el</label><input class="input" type="date" id="w-fin" data-w="fin" value="${W.fin}" min="${W.inicio}" ${errs.fin?'aria-invalid="true" aria-describedby="e-fin"':""}></div></div>
      ${errs.inicio?`<p class="error" id="e-ini">${errs.inicio}</p>`:""}${errs.fin?`<p class="error" id="e-fin">${errs.fin}</p>`:""}
      ${urgent?`<div class="warn">${I.warn}<span>Con tan poco margen es difícil encontrar a alguien. Puedes intentarlo igualmente.</span></div>`:""}</div>
    <fieldset class="field" style="border:0;padding:0;margin:0"><legend class="flabel" style="margin-bottom:6px">¿Qué hay que cuidar? <small>· de tu ficha</small></legend>
      <div class="pick">${casa.seres.map(s=>`<label><input type="checkbox" data-wser="${s.id}" ${W.seres.includes(s.id)?"checked":""}><span style="width:44px;height:44px;border-radius:12px;display:grid;place-items:center;background:var(--${s.cat==="pl"?"savia-soft":"primary-soft"});color:var(--${s.cat==="pl"?"savia":"primary-text"})">${icoCat(s.cat)}</span><span><b>${s.cantidad>1?s.cantidad+" ":""}${esc(s.nombre)}</b><small>${esc(s.especie)} · cada ${plural(s.cada,"día","días")}</small></span></label>`).join("")}</div>
      ${errs.seres?`<p class="error">${errs.seres}</p>`:""}</fieldset>
    <fieldset class="field" style="border:0;padding:0;margin:0"><legend class="flabel" style="margin-bottom:6px">Franja preferida</legend>
      <div class="seg">${Object.entries(FR).map(([k,t])=>`<label><input type="radio" name="fr" value="${k}" data-wfr ${W.franja===k?"checked":""}><span>${t}</span></label>`).join("")}</div></fieldset>
    <label class="checkline"><input type="checkbox" data-wcheck="habitada" ${W.habitada?"checked":""}><span><b>Casa habitada</b> <span class="m">+3 € / visita</span><small>Subir y bajar persianas, recoger el correo y encender alguna luz.</small></span></label>`;
  }
  if(step===2){
    const hasAn=seresSel.some(s=>s.cat!=="pl"),hasPl=seresSel.some(s=>s.cat==="pl"),hasEx=seresSel.some(s=>s.cat==="ex");
    const obl=[ME.zona_unica?"Trabaja en la zona piloto (Madrid)":`Trabaja en tu barrio (${esc(ME.cp)})`,`Libre del ${fmtD(W.inicio)} al ${fmtD(W.fin)}`,hasAn&&hasPl?"Acepta animales y plantas":hasAn?"Acepta animales":"Acepta plantas","Identidad verificada"];
    if(hasEx)obl.push("Insignia de exóticos del grupo de tus animales");
    if(seresSel.some(s=>s.medicacion))obl.push("Experiencia con medicación");
    const claves=(r.claves||[]).map(e=>e==="Gato"?"gatos":e.toLowerCase()).join(" y ");
    const OPT=[["del","Insignia «Plantas delicadas»",seresSel.some(s=>s.cat==="pl"&&s.dif>=4)?"Activada porque tienes plantas de dificultad 4 o más.":"Formación avalada por el vivero socio."],["esp","Ya ha cuidado tus especies delicadas",claves?"En tu caso: "+claves+".":"Según su historial."],["rat","Valoración de 4,5 o más","Deja fuera a quien aún no tiene reseñas."],["serv","Al menos 5 servicios completados","Más experiencia, menos cuidadores nuevos."],["fr","Franja horaria estricta · "+FR[W.franja].toLowerCase(),"Solo quien puede ir en esa franja."]];
    body=`<div class="req"><p class="flabel" style="font-weight:600">Siempre se exige <small class="muted" style="font-weight:400">· no se pueden quitar</small></p><ul>${obl.map(t=>`<li class="lock">${I.lock}${t}</li>`).join("")}</ul></div>
    <div class="req"><p class="flabel" style="font-weight:600">Tu nivel de precisión <small class="muted" style="font-weight:400">· opcional</small></p>
      <p class="muted" style="font-size:14.5px">Cada requisito que añades avisa a menos cuidadores, pero más ajustados a tu casa.</p>
      <ul>${OPT.map(([k,t,d])=>`<li class="opt"><span><label for="o-${k}" style="font-weight:500">${t}</label><small>${d}</small></span><span class="switch"><input type="checkbox" role="switch" id="o-${k}" data-wopt="${k}" ${W.opt[k]?"checked":""}><span></span></span></li>`).join("")}</ul></div>
    ${n===0?`<div class="warn" role="status">${I.warn}<span>Con estos requisitos aún no hay nadie.${r.sugerencia?` Prueba a quitar <b>«${esc(r.sugerencia.texto)}»</b>: habría ≈ ${r.sugerencia.n}. <button type="button" class="link" data-act="w-relax" data-k="${r.sugerencia.k}" style="padding:0">Quitarlo</button>`:" Los requisitos obligatorios no se pueden quitar."}</span></div>`:""}
    ${n>0&&n<3?`<div class="warn" role="status">${I.warn}<span>Con tan pocos cuidadores es difícil que se cubra. Si puedes, relaja algún requisito.</span></div>`:""}`;
  }
  if(step===3){
    body=`<div class="summary"><dl>
      <dt>Fechas</dt><dd>${fmtDL(parseD(W.inicio))} – ${fmtDL(parseD(W.fin))}${p?" · "+plural(p.dias,"día","días"):""}</dd>
      <dt>Qué cuidar</dt><dd><div class="chips">${seresSel.map(serChip).join("")}</div></dd>
      <dt>Servicio</dt><dd>${p?`${esc(p.servicio)} · ${plural(p.visitas,"visita","visitas")}${p.has_an?" (los animales necesitan una al día)":""}`:""} · franja de ${FR[W.franja].toLowerCase()}</dd>
      <dt>Precisión</dt><dd>${Object.entries(W.opt).filter(([k,v])=>v).map(([k])=>CAT.opcionales[k]).join(" · ")||"Solo los requisitos obligatorios"}</dd>
      ${W.habitada?`<dt>Complemento</dt><dd>Casa habitada</dd>`:""}</dl></div>
    <div class="field"><label for="w-nota">¿Algo más que quieras contar? <small>· opcional</small></label><textarea class="input" id="w-nota" data-w="nota" maxlength="400" placeholder="Por ejemplo: Lola es tímida al principio; dale unos minutos.">${esc(W.nota)}</textarea></div>
    <div class="info">${I.info}<span>Los cuidadores ven tu barrio y las instrucciones resumidas. Tu dirección exacta solo la verá la persona con quien confirmes la reserva.</span></div>
    <div id="pub-err"></div>`;
  }
  const titles=["¿Qué y cuándo?","¿Cuánta precisión quieres?","Revisa y publica"];
  const disabled=(step===1&&Object.keys(errs).length)||(step===2&&!n);
  return head(titles[step-1],"",`Paso ${step} de 3`)+`
  <div class="wiz"><section class="card"><div class="steps" aria-hidden="true">${[1,2,3].map(i=>`<i class="${i<=step?"on":""}"></i>`).join("")}</div>
    <form class="form" id="f-wiz" novalidate style="margin-top:16px">${body}
      <div class="actions">${step>1?`<button type="button" class="link" data-act="w-back">← Atrás</button>`:`<a class="link" href="#/inicio">Cancelar</a>`}
      ${step<3?`<button type="submit" class="btn primary" ${disabled?"disabled":""}>Siguiente →</button>`:`<button type="submit" class="btn primary" ${!n?"disabled":""}>Publicar y avisar a ${plural(Math.min(n||0,15),"cuidador","cuidadores")}</button>`}</div>
    </form></section>
  <aside class="aside" aria-live="polite">
    <span class="tag">${step===2?"En vivo":"Estimación"}</span>
    <div class="big m" id="big-n">${n==null?"…":"≈ "+n}</div>
    <p class="sub">${n===1?"cuidador idóneo":"cuidadores idóneos"} en ${esc(ME.barrio)}. Solo ellos reciben el aviso${n>15?" (máximo 15 por tanda)":""}.</p>
    ${r.nuevos?`<p class="sub" style="font-size:13px">Incluye ${plural(r.nuevos,"cuidador nuevo","cuidadores nuevos")}: reservamos al menos el 20 % de cada tanda para quien empieza.</p>`:""}
    ${p?`<hr><div class="line"><span>${esc(p.servicio)}</span><b class="m">${eur(p.por_visita)} / ${p.unidad}</b></div>
    <div class="line"><span>${plural(p.visitas,"visita","visitas")}${p.extra?" + casa habitada":""}</span><b class="m">× ${p.visitas}</b></div>
    <div class="line" style="align-items:baseline"><span>Total</span><span class="tot">${eur(Math.round(p.total))}</span></div>
    <p class="sub" style="font-size:13px">Precio orientativo: el final depende de la tarifa de cada cuidador.${p.delicadas&&p.servicio==="Cuidado combinado"?" Incluye +2 € por plantas delicadas.":""}</p>`:""}
    <div class="warn">${I.warn}<span>Seguro <span class="status st-pend" style="margin-left:4px">${esc(ME.seguro||"En contratación")}</span><br>En esta prueba el pago es simulado.</span></div>
  </aside></div>`;
}

/* ----- anuncio (dueño) ----- */
async function vAnuncioD(id){
  if(!id){
    const list=await api("/anuncios/mios");
    const act=list.find(a=>["abierto","asignado","reservado","en_curso"].includes(a.estado));
    if(act){location.replace("#/anuncio/"+act.id);return '<div class="loading"></div>'}
    return head("Mis anuncios")+(list.length?`<div class="stack">${list.map(a=>`<a class="sol" href="#/${a.estado==="completado"?"reserva":"anuncio"}/${a.id}"><div class="top"><div><h3>${esc(a.plan.servicio)} · ${fmtD(a.inicio)} – ${fmtD(a.fin)}</h3><div class="chips" style="margin-top:6px">${a.seres.map(serChip).join("")}</div></div>${estadoBadge(a)}</div></a>`).join("")}</div><a class="btn primary" href="#/publicar" style="margin-top:16px">Publicar otro anuncio</a>`
      :`<section class="empty"><h2>Aún no has publicado ningún anuncio.</h2><p>Tarda un par de minutos y usa la ficha de tu casa.</p><a class="btn" href="#/publicar">Publicar un anuncio →</a></section>`);
  }
  const a=await api("/anuncio/"+id);
  const p=a.plan;
  const cands=a.candidaturas.filter(k=>k.estado!=="retirada");
  cands.sort((x,y)=>(y.estado==="elegida")-(x.estado==="elegida"));
  let extra="";
  if(a.estado!=="abierto"&&a.estado!=="cancelado"&&a.elegido){
    extra=`<section class="card ad-head"><div class="ad-top"><div style="display:flex;gap:12px;align-items:center">${avatar(a.elegido,true)}<div><p class="lbl">Has elegido a</p><h2 style="font-size:24px">${esc(a.elegido.nombre)}</h2></div></div>${estadoBadge(a)}</div>
      <p>${a.estado==="asignado"?(a.encuentro&&a.encuentro.elegido?`Encuentro previo el <b>${fmtDL(new Date(a.encuentro.elegido))} · ${hhmm(a.encuentro.elegido)}</b> en tu casa.`:`Has propuesto ${plural(a.encuentro.huecos.length,"hueco","huecos")}. ${esc(a.elegido.nombre)} elegirá uno.`):a.estado==="completado"?"El servicio ha terminado.":"Reserva confirmada · pago simulado."}</p>
      <a class="btn primary" style="justify-self:start" href="#/reserva/${a.id}">${a.estado==="asignado"?"Ver el encuentro":a.estado==="completado"?"Ver partes y valorar":"Ver la reserva y los partes"}</a></section>`;
  }
  const OPT=Object.entries(CAT.opcionales);
  const relax=a.estado==="abierto"?`<details class="card" ${a.sin_respuesta?"open":""}><summary style="cursor:pointer;font-weight:600">Ajustar la precisión del anuncio</summary>
      ${a.sin_respuesta?`<div class="warn" style="margin-top:12px">${I.warn}<span>Aún nadie se ha presentado. Si quitas algún requisito, avisaremos a más cuidadores. Nunca los quitamos sin preguntarte.</span></div>`:""}
      <form id="f-relax" style="display:grid;gap:8px;margin-top:12px"><ul class="req" style="margin:0;padding:0">${OPT.map(([k,t])=>`<li class="opt"><label for="r-${k}">${esc(t)}</label><span class="switch"><input type="checkbox" role="switch" id="r-${k}" data-ropt="${k}" ${a.opt[k]?"checked":""}><span></span></span></li>`).join("")}</ul>
      <p class="muted" style="font-size:14px">Ahora mismo hay ≈ ${a.idoneos_ahora} idóneos con estos requisitos; ya hemos avisado a ${a.avisados}.</p>
      <button class="btn ghost small" type="submit" style="justify-self:start">Guardar y avisar a quien encaje</button></form></details>`:"";
  return head(`${esc(p.servicio)} · ${fmtD(a.inicio)} – ${fmtD(a.fin)}`,"","Mi anuncio",estadoBadge(a))+`
  <div class="stack">
    <section class="card ad-head">${track5(a)}
      <div class="chips">${a.seres.map(serChip).join("")}<span class="chip ne">${plural(p.visitas,"visita","visitas")} · ${FR[a.franja].toLowerCase()}</span>${a.urgente?`<span class="status st-pend">Urgente</span>`:""}</div>
      <div class="stats"><div><b>${a.avisados}</b><span>cuidadores avisados</span></div><div><b>${a.n_cands}</b><span>candidaturas</span></div><div><b class="m">${eur(Math.round(p.total))}</b><span>orientativo</span></div></div>
      <p class="muted" style="font-size:14px">Publicado el ${cuando(a.creado)}${["abierto","asignado"].includes(a.estado)?` · <button type="button" class="link" data-act="cancel-ad" data-id="${a.id}" style="padding:0">Cancelar anuncio (sin coste)</button>`:""}</p>
    </section>
    ${extra}${relax}
    <h2 style="font-size:24px;margin-top:8px">Candidaturas ${cands.length?`<span class="muted m" style="font-size:18px">(${cands.length})</span>`:""}</h2>
    ${!cands.length&&a.estado==="abierto"?`<div class="waiting" role="status"><span class="pulse" aria-hidden="true"></span><span>Hemos avisado a ${plural(a.avisados,"cuidador idóneo","cuidadores idóneos")}. Te avisamos en cuanto alguien se presente.</span></div>`:""}
    <div class="cands">${cands.map(k=>candCard(k,a)).join("")}</div>
  </div>`;
}
function candCard(k,a){
  const c=k.cuidador;const nuevo=c.n_serv<=2;const chosen=k.estado==="elegida";const closed=["descartada","cerrada"].includes(k.estado);
  const fresh=Date.now()-k.creado<4000;
  return `<article class="cand ${fresh?"fresh":""} ${chosen?"chosen":""} ${closed?"closed":""}" aria-labelledby="cn-${k.id}">
    ${avatar(c,true)}
    <div>
      <h3 id="cn-${k.id}">${esc(c.nombre)}${nuevo?`<span class="status st-pilot">Nueva</span>`:""}${chosen?`<span class="status st-ok">Elegida</span>`:""}${closed?`<span class="status st-off">Cerrada</span>`:""}</h3>
      <p class="where">${esc(c.barrio)} · a <span class="m">${km(c.km)} km</span>${c.edad?" · "+c.edad+" años":""} · <span class="status st-ok" style="padding:3px 8px;font-size:10.5px">Identidad verificada</span></p>
      ${c.coinciden&&c.coinciden.length?`<div class="facts"><span class="match">Ha cuidado ${c.coinciden.map(e=>e==="Gato"?"gatos":e.toLowerCase()).join(" y ")}</span></div>`:""}
      <div class="facts"><span>${c.rating?`<b class="m">★ ${String(c.rating.toFixed(1)).replace(".",",")}</b> · ${plural(c.n_res,"reseña","reseñas")}`:"Sin reseñas aún"}</span><span><b class="m">${c.n_serv}</b> servicios</span></div>
      <div class="ins"><div>${c.insignias.map(i=>`<span class="chip ${/Plantas/.test(i.t)&&!/Animales/.test(i.t)?"pl":"an"}">${esc(i.t)}</span>`).join("")}</div>
        <small>Aval: ${[...new Set(c.insignias.map(i=>i.aval.toLowerCase()))].join(" y ")} · <span class="status st-pilot" style="padding:2px 7px;font-size:10px">En piloto</span></small></div>
      ${c.bio?`<p class="muted" style="font-size:14.5px;margin-top:10px">${esc(c.bio)}</p>`:""}
      ${k.mensaje?`<p class="msg">«${relTexto(esc(k.mensaje))}»</p>`:""}
    </div>
    <div class="cand-side"><p class="price">${eur(c.precio)}<small>total · orientativo</small></p>
      <div class="btns" style="display:grid;gap:8px">
        <a class="btn ghost small" href="#/mensajes/${k.id}">${k.no_leidos?"Leer mensaje nuevo":"Hablar con "+esc(c.nombre)}</a>
        ${a.estado==="abierto"&&k.estado==="enviada"?`<button type="button" class="btn primary small" data-choose='${esc(JSON.stringify({cand:k.id,nombre:c.nombre,inicio:a.inicio}))}'>Elegir a ${esc(c.nombre)}</button>`:""}
      </div></div>
  </article>`;
}

/* ----- ficha de la casa ----- */
async function vCasa(){
  const {casa,seres}=await api("/casa");
  const esp=CAT.especies;
  return head("Lo que vive en tu casa","Estas instrucciones se convierten en tareas en cada visita. Solo se escriben una vez.","Ficha de la casa")+`
  <div class="grid2"><div class="stack">
    <section class="card">${seres.length?seres.map(s=>`${serRow(s,`<button type="button" class="link" data-act="ser-del" data-id="${s.id}" aria-label="Quitar ${esc(s.nombre)}">Quitar</button>`)}${s.instr?`<p class="muted" style="font-size:14px;margin:-4px 0 10px 56px">${esc(s.instr)}</p>`:""}`).join(""):`<p class="muted">Aún no hay nada. Añade al menos un animal o planta.</p>`}</section>
    <section class="card"><h2 style="font-size:22px;margin-bottom:14px">Añadir a tu casa</h2>
      <form id="f-ser" class="form ser-form" data-tipo="an" novalidate style="gap:16px"><div id="ser-err"></div>
        <fieldset class="field" style="border:0;padding:0;margin:0"><legend class="sr">Qué quieres añadir</legend>
          <div class="seg seg2"><label><input type="radio" name="s-tipo" value="an" checked><span><i class="seg-ic" aria-hidden="true">${I.cat}</i>Animal</span></label><label><input type="radio" name="s-tipo" value="pl"><span><i class="seg-ic" aria-hidden="true">${I.plant}</i>Planta</span></label></div></fieldset>
        <fieldset class="field" data-solo="an" style="border:0;padding:0;margin:0"><legend class="flabel" style="margin-bottom:8px">Especie</legend><div class="chipsel">${esp.filter(e=>e.cat!=="pl").sort((a,b)=>(a.cat>b.cat)-(a.cat<b.cat)||b.activa-a.activa).map(e=>`<label><input type="radio" name="s-esp-an" value="${e.id}"><span>${esc(e.nombre)}${e.cat==="ex"?`<small class="chip-x">exótico</small>`:""}${e.activa?"":`<small class="chip-x">aún no</small>`}</span></label>`).join("")}</div></fieldset>
        <fieldset class="field" data-solo="pl" style="border:0;padding:0;margin:0"><legend class="flabel" style="margin-bottom:8px">Especie</legend><div class="chipsel">${esp.filter(e=>e.cat==="pl").map(e=>`<label><input type="radio" class="pl" name="s-esp-pl" value="${e.id}"><span>${esc(e.nombre)}</span></label>`).join("")}</div></fieldset>
        <p class="ser-info" id="s-info" aria-live="polite" hidden></p>
        <div class="row2"><div class="field"><label for="s-nom">Nombre <small>· opcional</small></label><input class="input" id="s-nom" placeholder="Lola, Kiwi…"></div><div class="field"><label for="s-cant">Cantidad</label><input class="input" id="s-cant" type="number" min="1" max="99" value="1"></div></div>
        <div class="field"><label for="s-instr"><span data-solo="an">Comida y rutina</span><span data-solo="pl">Riego y luz</span> <small>· opcional</small></label><textarea class="input" id="s-instr" placeholder="Cuánta comida, dónde está, el arenero, cada cuánto…"></textarea></div>
        <div class="field"><label for="s-alarma">Señales de alarma <small>· opcional</small></label><input class="input" id="s-alarma" placeholder="Si no come o se esconde, avísame"></div>
        <label class="checkline" data-solo="an"><input type="checkbox" id="s-med"><span><b>Necesita medicación</b><small>Solo te avisaremos a cuidadores con experiencia en medicación.</small></span></label>
        <button class="btn primary" type="submit" style="justify-self:start">Añadir a la ficha</button></form></section>
  </div>
  <section class="card"><h2 style="font-size:22px;margin-bottom:6px">Datos de la casa</h2><p class="muted" style="font-size:14px;margin-bottom:14px">La dirección y el acceso solo los ve tu cuidador con la reserva confirmada.</p>
    <form id="f-casa" class="form" novalidate style="gap:14px">
      <div class="field"><label for="c-dir">Dirección</label><input class="input" id="c-dir" value="${esc(casa.direccion||"")}"></div>
      <div class="field"><label for="c-acc">Cómo se entra</label><select class="input" id="c-acc">${["Llaves en mano","Portero","Caja de llaves"].map(o=>`<option ${casa.acceso===o?"selected":""}>${o}</option>`).join("")}</select></div>
      <div class="field"><label for="c-instr">Instrucciones de acceso</label><textarea class="input" id="c-instr">${esc(casa.instr_acceso||"")}</textarea></div>
      <div class="field"><label for="c-vet">Veterinario de referencia <small>· obligatorio con animales</small></label><input class="input" id="c-vet" value="${esc(casa.veterinario||"")}"></div>
      <div class="field"><label for="c-em">Contacto de emergencia</label><input class="input" id="c-em" value="${esc(casa.emergencia||"")}"></div>
      <button class="btn ghost small" type="submit" style="justify-self:start">Guardar</button></form></section></div>`;
}

/* ================================================================ CUIDADOR */
function bannerPerfil(){
  const p=ME.perfil;
  if(!p.verificado)return `<div class="warn" style="margin-bottom:16px">${I.info}<span><b>Tu identidad está en revisión.</b> Hasta verificarla no recibes avisos de solicitudes. <span class="status st-pend" style="margin-left:4px">En revisión</span></span></div>`;
  if(!p.zonas.length||!p.disponibilidad.length)return `<div class="warn" style="margin-bottom:16px">${I.info}<span>Marca tus barrios y tu disponibilidad para recibir avisos. <a href="#/perfil">Ir a mi perfil</a></span></div>`;
  return "";
}
async function vSolicitudes(){
  const list=await api("/solicitudes");
  const abiertas=list.filter(s=>s.estado==="abierto"&&!s.candidatura);
  const resto=list.filter(s=>!(s.estado==="abierto"&&!s.candidatura));
  const card=s=>{
    const off=s.estado!=="abierto"&&!s.elegido_yo&&!(s.candidatura&&s.candidatura.estado==="elegida");
    const k=s.candidatura;
    const est=s.elegido_yo?`<span class="status st-ok">Te ha elegido</span>`:k?(k.estado==="enviada"?`<span class="status st-pilot">Te has presentado</span>`:`<span class="status st-off">Cerrada</span>`):off?`<span class="status st-off">Ya no está disponible</span>`:!s.visto?`<span class="status st-pilot">Nueva</span>`:"";
    return `<a class="sol ${!s.visto&&!off?"new":""} ${off?"off":""}" href="#/solicitud/${s.id}"><div class="top"><div><p class="lbl">${esc(s.barrio)} · ${esc(s.dueno)}</p><h3>${esc(s.servicio)} · ${fmtD(s.inicio)} – ${fmtD(s.fin)}</h3></div><p class="money">${eur(s.cobras)}<small>cobras · orientativo</small></p></div>
      <div class="chips">${s.seres.map(serChip).join("")}<span class="chip ne">${plural(s.visitas,"visita","visitas")}</span>${s.urgente?`<span class="status st-pend">Urgente</span>`:""}</div>${est?`<div>${est}</div>`:""}</a>`;
  };
  return head("Solicitudes para ti","Solo te avisamos de casas que encajan con tu perfil, tus barrios y tu disponibilidad.")+bannerPerfil()+avisoNavegador()+`
   <div class="stack">${abiertas.length?`<div class="reqlist">${abiertas.map(card).join("")}</div>`:`<div class="waiting">${ME.perfil.verificado?"Aún no hay solicitudes nuevas que encajen contigo. Te avisamos en cuanto llegue una.":"Cuando verifiquemos tu identidad empezarás a recibir avisos."}</div>`}
   ${resto.length?`<h2 style="font-size:22px;margin-top:12px">Anteriores</h2><div class="reqlist">${resto.map(card).join("")}</div>`:""}</div>`;
}
async function vSolicitud(id){
  const a=await api("/anuncio/"+id);
  const k=a.candidatura;const p=a.plan;
  let action;
  if(a.estado!=="abierto"&&!(k&&k.estado==="elegida")){action=`<div class="info">${I.info}<span>Esta solicitud ya no está disponible.</span></div>`}
  else if(k&&k.estado==="elegida"){action=`<a class="btn primary" href="#/reserva/${a.id}">${esc(a.dueno.nombre)} te ha elegido · Ver siguiente paso</a>`}
  else if(k){action=`<div class="stack"><div class="info">${I.info}<span>Te has presentado el ${cuando(k.creado)}. ${esc(a.dueno.nombre)} está viendo candidaturas.</span></div><div style="display:flex;gap:10px;flex-wrap:wrap"><a class="btn primary" href="#/mensajes/${k.id}">Ir a la conversación</a>${k.estado==="enviada"?`<button type="button" class="link" data-act="retirar" data-id="${k.id}">Retirar mi candidatura</button>`:""}</div></div>`}
  else{action=`<form id="f-cand" data-id="${a.id}" class="form" style="gap:12px"><div id="cand-err"></div><div class="field"><label for="cand-msg">Mensaje para ${esc(a.dueno.nombre)} <small>· opcional</small></label><textarea class="input" id="cand-msg" data-draft="cand-${a.id}" maxlength="600" placeholder="Cuéntale por qué encajas: experiencia con sus especies, cercanía, horario…">${esc(DR["cand-"+a.id]||"")}</textarea><small>Los teléfonos y correos se ocultan hasta confirmar la reserva.</small></div><button class="btn primary" type="submit" style="justify-self:start">Me interesa</button></form>`}
  return head(`${esc(p.servicio)} · ${fmtD(a.inicio)} – ${fmtD(a.fin)}`,"",`Solicitud de ${esc(a.dueno.nombre)} · ${esc(a.barrio)}`)+`
  <div class="grid2"><div class="stack">
    <section class="card stack">
      <dl class="kv"><dt>Dónde</dt><dd>${esc(a.barrio)} · a unos ${km(a.km)} km de ti <small class="muted">(la dirección exacta, al confirmar la reserva)</small></dd>
      <dt>Fechas</dt><dd>${fmtDL(parseD(a.inicio))} – ${fmtDL(parseD(a.fin))} · ${plural(p.visitas,"visita","visitas")}</dd>
      <dt>Franja</dt><dd>${FR[a.franja]}</dd>${a.habitada?`<dt>Además</dt><dd>Casa habitada: persianas, correo y luces</dd>`:""}</dl>
      ${a.nota?`<p class="msg">«${esc(a.nota)}»</p>`:""}
    </section>
    <section class="card"><h2 style="font-size:22px;margin-bottom:6px">Qué hay que cuidar</h2>${a.seres.map(s=>`${serRow(s)}${s.instr?`<p class="muted" style="font-size:14px;margin:-4px 0 10px 56px">${esc(s.instr)}</p>`:""}`).join("")}</section>
  </div>
  <div class="stack"><section class="netbox"><span class="lbl">Lo que cobras</span><b>${eur(a.cobras)}</b><span style="font-size:14px">de ${eur(a.total_cuidador)} · la comisión es del 15 % · orientativo</span></section>
    <section class="card">${action}</section></div></div>`;
}
async function vServicios(){
  const list=await api("/servicios");
  const grp={act:[],env:[],cer:[]};
  list.forEach(x=>{const e=x.cand.estado,s=x.anuncio.estado;if(e==="elegida"&&s!=="abierto"&&s!=="cancelado")grp.act.push(x);else if(e==="enviada"&&s==="abierto")grp.env.push(x);else grp.cer.push(x)});
  const lab={asignado:"Encuentro previo",reservado:"Reservado",en_curso:"En curso",completado:"Terminado"};
  const card=(x,href)=>`<a class="sol" href="${href}"><div class="top"><div><p class="lbl">${esc(x.anuncio.barrio)} · ${esc(x.anuncio.dueno)}</p><h3>${esc(x.anuncio.servicio)} · ${fmtD(x.anuncio.inicio)} – ${fmtD(x.anuncio.fin)}</h3></div>${x.cand.estado==="elegida"?`<span class="status ${x.anuncio.estado==="completado"?"st-off":"st-ok"}">${lab[x.anuncio.estado]||""}</span>`:x.cand.estado==="enviada"?`<span class="status st-pilot">Esperando respuesta</span>`:`<span class="status st-off">${x.cand.estado==="retirada"?"Retirada":"No elegida"}</span>`}</div><div class="chips">${x.anuncio.seres.map(serChip).join("")}</div></a>`;
  return head("Mis servicios","Tus reservas y las solicitudes a las que te has presentado.")+`<div class="stack">
    <h2 style="font-size:22px">Reservas</h2>${grp.act.length?`<div class="reqlist">${grp.act.map(x=>card(x,"#/reserva/"+x.anuncio.id)).join("")}</div>`:`<p class="muted">Aún no tienes reservas.</p>`}
    <h2 style="font-size:22px;margin-top:8px">Candidaturas enviadas</h2>${grp.env.length?`<div class="reqlist">${grp.env.map(x=>card(x,"#/mensajes/"+x.cand.id)).join("")}</div>`:`<p class="muted">Ninguna abierta. <a href="#/inicio">Ver solicitudes</a></p>`}
    ${grp.cer.length?`<h2 style="font-size:22px;margin-top:8px">Cerradas</h2><div class="reqlist">${grp.cer.map(x=>card(x,"#/mensajes/"+x.cand.id)).join("")}</div>`:""}</div>`;
}
async function vPerfil(){
  ME=await api("/yo");const p=ME.perfil;
  const zonas=Object.entries(CAT.zonas).filter(([cp],i,arr)=>arr.findIndex(x=>x[1]===CAT.zonas[cp])===i||true);
  const esp=CAT.especies.filter(e=>e.activa);
  return head("Tu perfil","Así te ven los dueños cuando te presentas.")+`
  <div class="grid2"><div class="stack">
    <section class="card stack"><div style="display:flex;gap:14px;align-items:center">${avatar(ME,true)}<div><h2 style="font-size:24px">${esc(ME.nombre)}</h2><p class="muted">${esc(ME.barrio)} · ${p.n_serv} servicios${p.rating?" · ★ "+String(p.rating.toFixed(1)).replace(".",","):""}</p></div></div>
      <div class="chips">${p.verificado?`<span class="status st-ok">Identidad verificada</span>`:`<span class="status st-pend">Identidad en revisión</span>`}${p.insignias.map(i=>`<span class="chip ${/Plantas/.test(i.t)&&!/Animales/.test(i.t)?"pl":"an"}">${esc(i.t)}</span>`).join("")}</div>
      <p class="muted" style="font-size:13.5px">Las insignias las concede operaciones con aval externo (vivero socio o veterinario). <span class="status st-pilot" style="padding:2px 7px;font-size:10px">En piloto</span></p></section>
    <section class="card"><h2 style="font-size:22px;margin-bottom:12px">Disponibilidad</h2>
      <div class="dispo"><ul>${p.disponibilidad.map(d=>`<li><span class="m">${fmtD(d.inicio)} – ${fmtD(d.fin)}</span><button type="button" class="link" data-act="dispo-del" data-id="${d.id}">Quitar</button></li>`).join("")||`<li class="muted">Sin fechas marcadas.</li>`}</ul>
      <form id="f-dispo" class="row2" style="align-items:end;margin-top:8px"><div class="field"><label for="d-i">Desde</label><input class="input" type="date" id="d-i" min="${iso(today())}"></div><div class="field"><label for="d-f">Hasta</label><input class="input" type="date" id="d-f" min="${iso(today())}"></div><button class="btn ghost small" type="submit">Añadir fechas</button></form></div></section>
  </div>
  <section class="card"><form id="f-perfil" class="form" novalidate style="gap:18px">
    <div class="field"><label for="p-bio">Presentación</label><textarea class="input" id="p-bio" maxlength="400">${esc(p.bio||"")}</textarea></div>
    <fieldset class="field" style="border:0;padding:0;margin:0"><legend class="flabel" style="margin-bottom:6px">Qué aceptas</legend><div class="chipsel">
      <label><input type="checkbox" id="p-an" ${p.acepta_an?"checked":""}><span>Animales</span></label><label><input type="checkbox" class="pl" id="p-pl" ${p.acepta_pl?"checked":""}><span>Plantas</span></label><label><input type="checkbox" id="p-med" ${p.medicacion?"checked":""}><span>Medicación</span></label></div></fieldset>
    <fieldset class="field" style="border:0;padding:0;margin:0"><legend class="flabel" style="margin-bottom:6px">Barrios donde trabajas</legend><div class="chipsel">${zonas.map(([cp,b])=>`<label><input type="checkbox" data-zona="${cp}" ${p.zonas.includes(cp)?"checked":""}><span>${esc(b)} · ${cp}</span></label>`).join("")}</div></fieldset>
    <fieldset class="field" style="border:0;padding:0;margin:0"><legend class="flabel" style="margin-bottom:6px">Franjas</legend><div class="chipsel">${Object.entries(FR).map(([k,t])=>`<label><input type="checkbox" data-fr="${k}" ${(p.franjas||"").includes(k)?"checked":""}><span>${t}</span></label>`).join("")}</div></fieldset>
    <fieldset class="field" style="border:0;padding:0;margin:0"><legend class="flabel" style="margin-bottom:6px">Especies que ya has cuidado</legend><div class="chipsel">${esp.map(e=>`<label><input type="checkbox" class="${e.cat==="pl"?"pl":""}" data-esp="${esc(e.nombre)}" ${p.especies.includes(e.nombre)?"checked":""}><span>${esc(e.nombre)}</span></label>`).join("")}</div></fieldset>
    <div id="perfil-ok"></div>
    <button class="btn primary" type="submit" style="justify-self:start">Guardar perfil</button></form></section></div>`;
}

/* ================================================================ COMPARTIDO */
async function vReserva(id){
  const r=await api("/reserva/"+id);
  const d=r.soy_dueno;const p=r.plan;const e=r.encuentro;
  const otro=d?r.elegido:r.dueno;
  const yoSi=e?(d?e.si_dueno:e.si_cuidador):null,otroSi=e?(d?e.si_cuidador:e.si_dueno):null;
  let main="";
  const ini=parseD(r.inicio);
  if(!r.elegido||(!d&&r.elegido_id!==ME.id)){
    return head("Reserva")+`<div class="info">${I.info}<span>Esta reserva ya no está activa.</span></div>`;
  }
  /* --- encuentro previo --- */
  if(r.estado==="asignado"){
    if(!e.elegido){
      main=d?`<section class="card stack"><h2 style="font-size:22px">Esperando a ${esc(otro.nombre)}</h2><p>Has propuesto estos huecos para conoceros en tu casa:</p><div class="chips">${e.huecos.map(h=>`<span class="chip ne m">${fmtDL(new Date(h))} · ${hhmm(h)}</span>`).join("")}</div><p class="muted" style="font-size:14px">Te avisamos cuando elija uno.</p></section>`
        :`<section class="card stack"><h2 style="font-size:22px">${esc(otro.nombre)} te ha elegido</h2><p>Elige cuándo os conocéis en su casa (${esc(r.barrio)}). Es gratis, de 15 a 30 minutos, para conocer a ${r.seres.filter(s=>s.cat!=="pl").map(s=>esc(s.nombre)).join(" y ")||"sus plantas"} y acordar las tareas.</p>
          <div class="slots" role="group" aria-label="Huecos propuestos">${e.huecos.map(h=>`<button type="button" class="btn ghost" style="height:auto;padding:12px;display:grid;gap:2px" data-hueco="${h}" data-id="${r.id}"><b class="m">${fmtDL(new Date(h))}</b>${hhmm(h)}</button>`).join("")}</div>
          <button type="button" class="link" data-act="cancelar-cuid" data-id="${r.id}" style="justify-self:start">No puedo hacerme cargo</button></section>`;
    }else{
      const fecha=`${fmtDL(new Date(e.elegido))} · ${hhmm(e.elegido)}`;
      let q;
      if(yoSi==null)q=`<div class="stack"><p><b>¿Seguimos adelante?</b> Después de conoceros, contestáis los dos. La reserva solo se confirma con el sí de ambos.</p><p class="hint">En esta prueba puedes contestar ya, sin esperar al encuentro.</p><div style="display:flex;gap:10px;flex-wrap:wrap"><button class="btn primary" type="button" data-seguimos="1" data-id="${r.id}">Sí, seguimos adelante</button><button class="btn ghost" type="button" data-seguimos="0" data-id="${r.id}">Prefiero no seguir</button></div><p class="muted" style="font-size:13.5px">Si alguien dice que no, ${d?"el anuncio vuelve a abrirse":"la solicitud vuelve a abrirse"} sin coste y sin mostrar el motivo.</p></div>`;
      else q=`<div class="waiting" role="status"><span class="pulse" aria-hidden="true"></span><span>Has dicho que sí. Falta la respuesta de ${esc(otro.nombre)}.</span></div>`;
      main=`<section class="card stack"><p class="lbl">Encuentro previo</p><h2 style="font-size:24px">${fecha}</h2><p>${d?"En tu casa":"En casa de "+esc(otro.nombre)+" · "+esc(r.barrio)} · gratis · 15-30 min</p>${q}${!d?`<button type="button" class="link" data-act="cancelar-cuid" data-id="${r.id}" style="justify-self:start">No puedo hacerme cargo</button>`:""}</section>`;
    }
  }
  /* --- reserva en marcha --- */
  if(["reservado","en_curso","completado"].includes(r.estado)){
    const visitas=r.visitas.filter(v=>!v.extra);
    const abierta=r.visitas.find(v=>!v.salida);
    const hechas=new Set(visitas.map(v=>v.dia));
    const pendientes=p.dias_visita.filter(x=>!hechas.has(x));
    const extraAc=r.extras.find(x=>x.estado==="aceptada");
    const extraHecha=r.visitas.some(v=>v.extra);
    let heat="";
    if(r.calor&&r.calor_sens.length&&r.estado!=="completado"){
      const x=r.extras[0];
      const dia=fmtDL(parseD(r.calor));
      if(d)heat=`<section class="heat-card" role="status"><h3>${I.sun}Ola de calor el ${dia}</h3><p>Previsión de 38 °C. Tus ${r.calor_sens.map(n=>esc(n.toLowerCase())).join(" y ")} lo van a notar: conviene una visita extra ese día.</p>
        ${!x?`<div style="display:flex;gap:12px;align-items:center;flex-wrap:wrap"><button class="btn primary" type="button" data-act="pedir-extra" data-id="${r.id}">Pedir visita extra</button><span class="m">unos 12 € · orientativo</span></div><p style="font-size:13.5px">Se lo pedimos primero a ${esc(otro.nombre)}. Si no puede, a otros cuidadores idóneos. Si nadie puede, no se te cobra.</p>`
          :x.estado==="pedida"?`<p><span class="status st-pend">Pedida</span> Esperando a que ${esc(otro.nombre)} la acepte.</p>`:x.estado==="aceptada"?`<p><span class="status st-ok">Aceptada</span> ${esc(otro.nombre)} hará la visita extra${extraHecha?" · hecha":""}.</p>`:`<p><span class="status st-off">No disponible</span> Buscamos a otra persona; si no, no se te cobra.</p>`}</section>`;
      else if(x&&x.estado==="pedida")heat=`<section class="heat-card"><h3>${I.sun}${esc(otro.nombre)} pide una visita extra</h3><p>Ola de calor el ${dia}. Una visita extra para ${r.calor_sens.map(n=>esc(n.toLowerCase())).join(" y ")}: unos 12 € (cobras ${eur(12*0.85)}).</p><div style="display:flex;gap:10px;flex-wrap:wrap"><button class="btn primary" type="button" data-extra="1" data-id="${x.id}">Aceptar visita extra</button><button class="btn ghost" type="button" data-extra="0" data-id="${x.id}">No puedo</button></div></section>`;
    }
    const lista=p.dias_visita.map((dia,i)=>{
      const v=visitas.find(v=>v.dia===dia);const fecha=fmtDL(addDays(ini,dia));
      if(v&&v.salida)return parteHTML(v,`Día ${i+1} · ${fecha}`,otro,d);
      if(v&&!v.salida)return d?`<section class="visit"><div class="visit-head"><h3>Día ${i+1} · ${fecha}</h3><span class="status st-ok">${esc(otro.nombre)} está en casa · ${hhmm(v.llegada)}</span></div></section>`:visitaEditor(v,`Día ${i+1} · ${fecha}`);
      const next=!d&&!abierta&&r.estado!=="completado"&&pendientes[0]===dia;
      return `<section class="visit" style="${next?"":"opacity:.75"}"><div class="visit-head"><h3>Día ${i+1} · ${fecha}</h3>${next?`<button class="btn primary small" type="button" data-llegada="${dia}" data-id="${r.id}">He llegado</button>`:`<span class="status st-off">Pendiente</span>`}</div>${next?`<p class="muted" style="font-size:14px">${tareasPrevias(r.seres,dia)}</p>`:""}</section>`;
    }).join("");
    const extraV=r.visitas.find(v=>v.extra);
    const extraBlock=extraV?(extraV.salida?parteHTML(extraV,"Visita extra por calor",otro,d):d?"":visitaEditor(extraV,"Visita extra por calor")):(!d&&extraAc&&!abierta?`<section class="visit"><div class="visit-head"><h3>Visita extra por calor</h3><button class="btn primary small" type="button" data-llegada="0" data-extra="1" data-id="${r.id}">He llegado</button></div></section>`:"");
    const casa=r.casa||{};
    const acceso=!d&&r.estado!=="completado"?`<section class="card"><p class="lbl">Solo durante tu reserva</p><h2 style="font-size:22px;margin:4px 0 10px">Cómo entrar</h2><dl class="kv"><dt>Dirección</dt><dd>${esc(casa.direccion||"—")}</dd><dt>Acceso</dt><dd>${esc(casa.acceso||"—")}${casa.instr_acceso?" · "+esc(casa.instr_acceso):""}</dd><dt>Veterinario</dt><dd>${esc(casa.veterinario||"—")}</dd><dt>Emergencia</dt><dd>${esc(casa.emergencia||"—")}</dd></dl></section>`:"";
    let fin="";
    if(r.estado==="completado")fin=resenaHTML(r,otro,d);
    main=`${heat}${fin}${acceso}<h2 style="font-size:22px;margin-top:4px">${d?"Partes del día":"Tus visitas"}</h2>${extraBlock}${lista}`;
  }
  if(r.estado==="abierto"||r.estado==="cancelado")main=`<div class="info">${I.info}<span>${d?"El anuncio vuelve a estar abierto.":"Esta reserva ya no está activa."}</span></div>`;
  const total=d?`<b class="m">${eur(r.total_cuidador)}</b><span>total · pago simulado</span>`:`<b class="m">${eur(r.cobras)}</b><span>cobras de ${eur(r.total_cuidador)}${r.estado==="completado"?" · se libera en 48 h":""}</span>`;
  return head(`${esc(p.servicio)} · ${fmtD(r.inicio)} – ${fmtD(r.fin)}`,"",d?"Tu reserva con "+esc(otro.nombre):"Casa de "+esc(otro.nombre)+" · "+esc(r.barrio),estadoBadge(r))+`
  <div class="grid2"><div class="stack">${main}</div>
  <div class="stack"><section class="card stack"><div style="display:flex;gap:12px;align-items:center">${avatar(otro,true)}<div><b style="font-size:18px">${esc(otro.nombre)}</b><p class="muted" style="font-size:14px">${esc(otro.barrio||"")}</p></div></div>
    <div class="stats">${total}</div>
    ${r.cand?`<a class="btn ghost small" href="#/mensajes/${r.cand.id}" style="justify-self:start">Abrir conversación</a>`:""}
    ${["reservado","en_curso"].includes(r.estado)?`<p class="muted" style="font-size:13.5px">Seguro <span class="status st-pend" style="padding:3px 8px;font-size:10px">${esc(r.seguro||"En contratación")}</span> · en el piloto, la reserva espera a tenerlo.</p>`:""}
    ${!d&&r.estado==="reservado"?`<button type="button" class="link" data-act="cancelar-cuid" data-id="${r.id}" style="justify-self:start">No puedo ir</button>`:""}</section>
    <section class="card"><h2 style="font-size:20px;margin-bottom:6px">${d?"Lo que se cuida":"Instrucciones"}</h2>${r.seres.map(s=>`${serRow(s)}${!d&&s.instr?`<p class="muted" style="font-size:14px;margin:-4px 0 10px 56px">${esc(s.instr)}${s.alarma?`<br><b>Alarma:</b> ${esc(s.alarma)}`:""}</p>`:""}`).join("")}</section></div></div>`;
}
function tareasPrevias(seres,dia){
  const t=seres.map(s=>({s,toca:s.cat!=="pl"||dia%Math.max(1,s.cada)===0}));
  const si=t.filter(x=>x.toca).map(x=>x.s.nombre),no=t.filter(x=>!x.toca).map(x=>x.s.nombre);
  return `Hoy toca: ${si.map(esc).join(", ")||"revisar la casa"}.${no.length?` No necesitan nada hoy: ${no.map(esc).join(", ")}.`:""}`;
}
function visitaEditor(v,titulo){
  const listas=v.tareas;const todas=listas.every(t=>t.estado);
  return `<section class="visit" aria-labelledby="vh-${v.id}"><div class="visit-head"><h3 id="vh-${v.id}">${titulo}</h3><span class="status st-ok">Llegada · ${hhmm(v.llegada)}</span></div>
    <p class="muted" style="font-size:14px">Marca cada tarea. Al terminar, ${"la dueña"} recibe el parte con las fotos.</p>
    <div>${listas.map(t=>`<div class="task"><div class="tt"><span class="sic ${t.cat}">${icoCat(t.cat)}</span><div><b>${t.cant>1?t.cant+" ":""}${esc(t.nombre)}</b><small>${esc(t.instr||t.especie)}</small></div></div>
      ${t.toca?`<div class="tri" role="group" aria-label="Estado de ${esc(t.nombre)}"><button type="button" class="ok" aria-pressed="${t.estado==="hecha"}" data-tarea='${JSON.stringify({v:v.id,s:t.ser_id,e:"hecha"})}'>Hecha</button><button type="button" class="no" aria-pressed="${t.estado==="no_hoy"}" data-tarea='${JSON.stringify({v:v.id,s:t.ser_id,e:"no_hoy"})}'>No hacía falta</button><button type="button" class="bad" aria-pressed="${t.estado==="no_pude"}" data-tarea='${JSON.stringify({v:v.id,s:t.ser_id,e:"no_pude"})}'>No he podido</button></div>
        ${t.estado==="no_pude"||t.estado==="no_hoy"?`<input class="input" id="mot-${v.id}-${t.ser_id}" data-motivo='${JSON.stringify({v:v.id,s:t.ser_id,e:t.estado})}' placeholder="${t.estado==="no_pude"?"¿Qué ha pasado? (se avisa a la dueña)":"Motivo breve"}" value="${esc(t.motivo||"")}">`:""}`
        :`<small class="muted">${esc(t.motivo)}</small>`}</div>`).join("")}</div>
    <div class="field"><span class="flabel">Fotos <small>· mínimo 1, máximo 10</small></span><div class="photos">${(v.fotos||[]).map(f=>`<figure><img src="${esc(fotoURL(f.archivo))}" alt="Foto de la visita"><button type="button" aria-label="Quitar foto" data-delfoto='${JSON.stringify({v:v.id,id:f.id})}'>${I.x}</button></figure>`).join("")}
      ${(v.fotos||[]).length<10?`<label class="addph">${I.cam}<span>Añadir foto</span><input type="file" accept="image/*" capture="environment" class="sr" data-foto="${v.id}"></label>`:""}</div>
      <small class="muted">Las fotos se comprimen en tu móvil y no guardan la ubicación.</small></div>
    <div class="field"><label for="nota-${v.id}">Nota para el parte <small>· opcional</small></label><input class="input" id="nota-${v.id}" data-draft="nota-${v.id}" value="${esc(DR["nota-"+v.id]||"")}" placeholder="Por ejemplo: 27 °C en el terrario de Kiwi"></div>
    <div id="sal-err-${v.id}"></div>
    <button class="btn primary" type="button" data-salida="${v.id}" ${todas&&(v.fotos||[]).length?"":"aria-disabled=\"true\""}>He terminado · enviar parte</button>
    ${!todas||!(v.fotos||[]).length?`<p class="muted" style="font-size:13.5px">${!todas?"Faltan tareas por marcar. ":""}${!(v.fotos||[]).length?"Falta al menos una foto.":""}</p>`:""}</section>`;
}
function parteHTML(v,titulo,otro,d){
  return `<section class="parte"><div class="visit-head"><h3 style="font-size:18px">${titulo}</h3><span class="m" style="font-size:13.5px">${hhmm(v.llegada)} – ${hhmm(v.salida)}</span></div>
    <p><b>${esc(v.resumen)}</b></p>
    ${v.fotos.length?`<div class="ph">${v.fotos.map(f=>`<img src="${esc(fotoURL(f.archivo))}" alt="Foto del parte">`).join("")}</div>${v.fotos.some(f=>f.ejemplo)?`<p class="ph-note">Fotos de ejemplo · imágenes creadas con IA</p>`:""}`:""}
    <ul>${v.tareas.map(t=>`<li><i>${t.estado==="hecha"?"✓":t.estado==="no_pude"?"!":"–"}</i><span>${esc(t.nombre)} · ${t.estado==="hecha"?"hecho":t.estado==="no_pude"?"no se ha podido":"no hacía falta"}${t.motivo?` <span class="muted">(${esc(t.motivo)})</span>`:""}</span></li>`).join("")}</ul>
    ${v.nota?`<p class="msg">«${esc(v.nota)}»</p>`:""}</section>`;
}
const ASPECTOS_D=["Fotos y actualizaciones","Sabe de plantas","Sabe de exóticos","Puntualidad","Trato con los animales","Casa impecable"];
const ASPECTOS_C=["Instrucciones claras","Casa bien preparada","Comunicación fácil","Puntual con el pago"];
function resenaHTML(r,otro,d){
  if(r.resena_mia){
    return `<section class="card stack"><h2 style="font-size:22px">Tu valoración</h2><p class="m">${"★".repeat(r.resena_mia.puntos)}${"☆".repeat(5-r.resena_mia.puntos)}</p>${r.resena_mia.texto?`<p>«${esc(r.resena_mia.texto)}»</p>`:""}
      ${r.resena_otra?`<hr style="border:0;border-top:1px solid var(--line);width:100%"><h3 style="font-size:18px">${esc(otro.nombre)} te ha valorado</h3><p class="m">${"★".repeat(r.resena_otra.puntos)}${"☆".repeat(5-r.resena_otra.puntos)}</p>${r.resena_otra.texto?`<p>«${esc(r.resena_otra.texto)}»</p>`:""}${r.resena_otra.aspecto?`<span class="chip an">${esc(r.resena_otra.aspecto)}</span>`:""}`
        :`<p class="muted">Verás la valoración de ${esc(otro.nombre)} cuando la escriba (o a los 14 días).</p>`}
      ${d&&r.confianza?`<p><span class="status st-ok">Cuidadora de confianza</span> Tus próximas solicitudes le llegarán primero.</p>`:""}</section>`;
  }
  const asp=d?ASPECTOS_D:ASPECTOS_C;
  return `<section class="card"><form id="f-resena" data-id="${r.id}" class="form" style="gap:16px"><div><p class="lbl">Servicio terminado</p><h2 style="font-size:24px">¿Qué tal con ${esc(otro.nombre)}?</h2>${r.resena_otra_existe?`<p class="muted" style="font-size:14px">${esc(otro.nombre)} ya te ha valorado. La verás al enviar la tuya.</p>`:`<p class="muted" style="font-size:14px">Las reseñas se publican cuando escribís los dos.</p>`}</div>
    <div id="res-err"></div>
    <fieldset class="field" style="border:0;padding:0;margin:0"><legend class="flabel" style="margin-bottom:6px">Puntuación <small>· obligatorio</small></legend><div class="stars">${[1,2,3,4,5].map(n=>`<button type="button" data-star="${n}" aria-pressed="${(DR.star||0)>=n}" aria-label="${n} de 5">★</button>`).join("")}</div></fieldset>
    <fieldset class="field" style="border:0;padding:0;margin:0"><legend class="flabel" style="margin-bottom:6px">Lo que más destacarías <small>· opcional</small></legend><div class="chipsel">${asp.map(a=>`<label><input type="radio" name="asp" value="${esc(a)}" ${DR.asp===a?"checked":""}><span>${esc(a)}</span></label>`).join("")}</div></fieldset>
    <div class="field"><label for="res-t">Comentario <small>· opcional</small></label><textarea class="input" id="res-t" data-draft="res-t">${esc(DR["res-t"]||"")}</textarea></div>
    ${d?`<label class="checkline"><input type="checkbox" id="res-conf" checked><span><b>Marcar a ${esc(otro.nombre)} como cuidadora de confianza</b><small>Tus próximas solicitudes le llegarán primero.</small></span></label>`:""}
    <button class="btn primary" type="submit" style="justify-self:start">Enviar valoración</button></form></section>`;
}

/* ----- mensajes ----- */
async function vMensajes(kid){
  const list=await api("/chats");
  if(!list.length)return head("Mensajes")+`<div class="card nochat" style="min-height:240px"><p>${ME.rol==="dueno"?"Cuando un cuidador se presente a tu anuncio, podréis hablar aquí.":"Cuando te presentes a una solicitud, podrás hablar aquí con la dueña o el dueño."}</p></div>`;
  let ch=null;
  if(kid){try{ch=await api("/chat/"+kid);ME.no_leidos=(await api("/yo")).no_leidos}catch(e){ch=null}}
  const convs=list.map(c=>{const u=c.ultimo;return `<a class="conv" href="#/mensajes/${c.id}" ${String(c.id)===String(kid)?'aria-current="true"':""}>${avatar(c.otro)}<span><b>${esc(c.otro.nombre)}</b><small>${u?esc((u.autor_id===ME.id&&!u.sistema?"Tú: ":"")+u.texto):""}</small></span>${c.no_leidos&&String(c.id)!==String(kid)?`<span class="unr" aria-label="sin leer"></span>`:""}</a>`}).join("");
  let thread=`<div class="thread"><div class="nochat" style="grid-row:1/-1"><p>Elige una conversación.</p></div></div>`;
  if(ch){
    const o=ch.otro;const a=ch.anuncio;const k=ch.cand;
    const typing=TYPING[k.id]&&TYPING[k.id]>Date.now();
    const msgs=ch.mensajes.map(m=>{
      if(m.sistema)return `<p class="bub sys">${esc(m.texto)} · <span class="m">${cuando(m.creado)}</span></p>`;
      const mine=m.autor_id===ME.id;
      return `<div class="bub ${mine?"me":"them"} ${Date.now()-m.creado<1500?"fresh":""}">${relTexto(esc(m.texto))}<span class="t">${hhmm(m.creado)}${mine?(m.leido?" · leído":" · enviado"):""}</span></div>${m.oculto?`<p class="flag">${I.lock.replace("<svg",'<svg width="14" height="14"')}Los datos de contacto se comparten al confirmar la reserva.</p>`:""}`;
    }).join("");
    const cerrada=["descartada","cerrada","retirada"].includes(k.estado)&&!ch.contacto_visible;
    let accion="";
    if(ch.soy_dueno){
      accion=a.estado==="abierto"&&k.estado==="enviada"?`<button type="button" class="btn primary small" data-choose='${esc(JSON.stringify({cand:k.id,nombre:o.nombre,inicio:a.inicio}))}'>Elegir a ${esc(o.nombre)}</button>`:k.estado==="elegida"?`<a class="btn ghost small" href="#/reserva/${a.id}">Ver reserva</a>`:`<span class="status st-off">Cerrada</span>`;
    }else{
      accion=k.estado==="elegida"?`<a class="btn primary small" href="#/reserva/${a.id}">Ver reserva</a>`:k.estado==="enviada"?`<span class="status st-pilot">Candidatura enviada</span>`:`<span class="status st-off">Cerrada</span>`;
    }
    const quick=ch.soy_dueno?["¿Cómo cuidarías mis plantas delicadas?","¿A qué hora podrías ir?","¿Cuándo podemos conocernos?"]:["¡Hola! Encantada de conocerte.","¿Hay algo que deba saber de la casa?","¿Te viene bien que nos conozcamos esta semana?"];
    thread=`<div class="thread">
      <div class="th-head"><a class="iconbtn back" href="#/mensajes" aria-label="Volver a las conversaciones">${I.back}</a>${avatar(o)}<div class="who"><b>${esc(o.nombre)}</b><small>${esc(o.barrio||"")}${o.rating?" · ★ "+String(o.rating.toFixed(1)).replace(".",","):""}${o.del?" · Plantas delicadas":""}</small></div>${accion}</div>
      <p class="privacy">${I.lock}${ch.contacto_visible?"Reserva confirmada: ya podéis compartir datos de contacto.":"La dirección y el teléfono se comparten solo al confirmar la reserva."}</p>
      <div class="msgs" id="msgs" aria-live="polite">${msgs}${typing?`<div class="typing" aria-label="${esc(o.nombre)} está escribiendo"><i></i><i></i><i></i></div>`:""}</div>
      ${cerrada?`<p class="privacy">Esta conversación está cerrada.</p><div></div>`:`<div class="quick" aria-label="Sugerencias">${quick.map(q=>`<button type="button" data-quick="${esc(q)}">${esc(q)}</button>`).join("")}</div>
      <form class="composer" id="f-chat" data-cid="${k.id}"><label class="sr" for="chat-in">Escribe a ${esc(o.nombre)}</label><input id="chat-in" autocomplete="off" data-draft="chat-${k.id}" placeholder="Escribe a ${esc(o.nombre)}…" value="${esc(DR["chat-"+k.id]||"")}"><button class="send" type="submit" aria-label="Enviar">${I.send}</button></form>`}
    </div>`;
  }
  return head("Mensajes",ME.rol==="dueno"?"Habla con quien se ha presentado antes de elegir.":"Habla con las personas cuyas casas quieres cuidar.")+`<div class="chat ${ch?"has-thread":""}"><nav class="convs" aria-label="Conversaciones">${convs}</nav>${thread}</div>`;
}
async function vAvisos(){
  const list=await api("/notifs");
  if(list.some(n=>!n.leida)){api("/notifs/leidas",{}).then(()=>api("/yo")).then(m=>{ME=m;paintBadges()}).catch(()=>{})}
  return head("Avisos","Te escribimos solo cuando pasa algo real.")+avisoNavegador()+`<section class="card">${notifList(list)}</section>`;
}

const RD={inicio:vInicioD,publicar:vPublicar,anuncio:vAnuncioD,casa:vCasa,reserva:vReserva,mensajes:vMensajes,avisos:vAvisos};
const RC={inicio:vSolicitudes,solicitud:vSolicitud,servicios:vServicios,perfil:vPerfil,reserva:vReserva,mensajes:vMensajes,avisos:vAvisos};

/* ================================================================ MODALES */
function modalElegir(o){
  const ini=parseD(o.inicio);const opts=[];
  for(let i=4;i>=1;i--){const d=addDays(ini,-i);if(d<=today())continue;[19,20].forEach(h=>{const x=new Date(d);x.setHours(h,0,0,0);opts.push(x.getTime())})}
  if(!opts.length){const x=addDays(today(),1);x.setHours(19,0,0,0);opts.push(x.getTime())}
  $("#layer").innerHTML=`<div class="scrim" data-act="close-modal"><div class="modal" role="dialog" aria-modal="true" aria-labelledby="m-t">
    <div><p class="lbl">Elegir</p><h2 id="m-t">Proponle a ${esc(o.nombre)} cuándo conoceros</h2></div>
    <p>El encuentro previo es gratis y en tu casa: 15-30 minutos para que conozca lo que vive en ella. Propón hasta 3 huecos; ${esc(o.nombre)} elige uno.</p>
    <form id="f-slots" novalidate><fieldset style="border:0;padding:0;margin:0"><legend class="sr">Huecos para el encuentro</legend>
      <div class="slots">${opts.map((t,i)=>`<label><input type="checkbox" name="slot" value="${t}" ${i<2?"checked":""}><span><b>${fmtDL(new Date(t))}</b>${hhmm(t)}</span></label>`).join("")}</div></fieldset>
      <p class="error" id="e-slots" hidden style="margin-top:10px">Elige entre 1 y 3 huecos.</p>
      <div class="info" style="margin-top:16px">${I.info}<span>Al elegir, el resto de candidatos recibe: «Ha elegido a otra persona. Gracias por presentarte».</span></div>
      <div id="m-err"></div>
      <div class="actions" style="margin-top:18px"><button type="button" class="link" data-act="close-modal">Seguir mirando</button><button type="submit" class="btn primary">Elegir y proponer</button></div>
    </form></div></div>`;
  const f=$("#f-slots");
  f.addEventListener("change",()=>{const n=f.querySelectorAll("input:checked").length;f.querySelectorAll("input:not(:checked)").forEach(i=>i.disabled=n>=3)});
  f.dispatchEvent(new Event("change"));
  f.querySelector("input").focus();
  f.onsubmit=async e=>{e.preventDefault();const sel=[...f.querySelectorAll("input:checked")].map(i=>+i.value);
    if(!sel.length||sel.length>3){$("#e-slots").hidden=false;return}
    try{await api("/elegir",{cand:o.cand,huecos:sel});closeModal();flash("Has elegido a "+o.nombre);location.hash="#/reserva/"+(await api("/chat/"+o.cand)).anuncio.id}catch(err){$("#m-err").innerHTML=errBox(err.message)}};
}
function pedirSeq(m){
  DR.seq=0;
  $("#layer").innerHTML=`<div class="scrim"><div class="modal" role="dialog" aria-modal="true" aria-labelledby="q-t">
    <div><p class="lbl">Una pregunta rápida</p><h2 id="q-t">${esc(m.titulo||"¿Qué tal ha ido?")}</h2></div>
    <form id="f-seq" data-tarea="${esc(m.tarea||"")}" class="form" style="gap:16px">
      <fieldset class="field" style="border:0;padding:0;margin:0"><legend class="flabel" style="margin-bottom:8px">¿Qué tan fácil te ha resultado?</legend>
        <div class="seq">${[1,2,3,4,5,6,7].map(n=>`<button type="button" data-seqv="${n}" aria-pressed="false">${n}</button>`).join("")}</div><div class="seq-ends"><span>Muy difícil</span><span>Muy fácil</span></div></fieldset>
      <div class="field"><label for="seq-t">¿Qué esperabas que pasara? <small>· opcional</small></label><textarea class="input" id="seq-t"></textarea></div>
      <div class="actions"><button type="button" class="link" data-act="close-modal">Ahora no</button><button class="btn primary" type="submit">Enviar</button></div></form></div></div>`;
}
function closeModal(){$("#layer").innerHTML=""}

/* ================================================================ FOTOS */
async function comprimir(file){
  const url=URL.createObjectURL(file);
  try{
    const img=await new Promise((ok,ko)=>{const i=new Image();i.onload=()=>ok(i);i.onerror=ko;i.src=url});
    const max=1280,s=Math.min(1,max/Math.max(img.width,img.height));
    const c=document.createElement("canvas");c.width=Math.round(img.width*s);c.height=Math.round(img.height*s);
    c.getContext("2d").drawImage(img,0,0,c.width,c.height);
    return c.toDataURL("image/jpeg",.8); // el lienzo no conserva metadatos: la foto sale sin ubicación (VIS-03)
  }finally{URL.revokeObjectURL(url)}
}

/* ================================================================ EVENTOS */
document.addEventListener("click",async e=>{
  const t=e.target.closest("[data-act],[data-choose],[data-notif],[data-quick],[data-quick-login],[data-hueco],[data-seguimos],[data-llegada],[data-tarea],[data-salida],[data-delfoto],[data-extra],[data-star],[data-seqv]");
  if(!t)return;
  try{
    if(t.dataset.quickLogin){const j=await api("/test/entrar",{correo:t.dataset.quickLogin});setToken(j.token);await cargarYo();conectarStream();location.hash="#/inicio";route();return}
    if(t.dataset.choose){modalElegir(JSON.parse(t.dataset.choose));return}
    if(t.dataset.notif){abrirNotif(JSON.parse(t.dataset.notif));return}
    if(t.dataset.quick){const f=$("#f-chat");if(f)enviarChat(f.dataset.cid,t.dataset.quick);track("sugerencia_chat",{});return}
    if(t.dataset.hueco){await api(`/encuentro/${t.dataset.id}/hueco`,{ts:+t.dataset.hueco});flash("Encuentro acordado");return route(true)}
    if(t.dataset.seguimos){const si=t.dataset.seguimos==="1";if(!si&&!confirm("¿Seguro que no quieres seguir? Se cancela sin coste y no se muestra el motivo."))return;await api(`/encuentro/${t.dataset.id}/seguimos`,{si});return route(true)}
    if(t.dataset.llegada!==undefined&&t.dataset.id){await api(`/visita/${t.dataset.id}/llegada`,{dia:+t.dataset.llegada,extra:t.dataset.extra==="1"});return route(true)}
    if(t.dataset.tarea){const x=JSON.parse(t.dataset.tarea);await api(`/visita/${x.v}/tareas`,{tareas:[{ser_id:x.s,estado:x.e,motivo:""}]});return route(true)}
    if(t.dataset.delfoto){const x=JSON.parse(t.dataset.delfoto);await api(`/visita/${x.v}/foto/borrar`,{id:x.id});return route(true)}
    if(t.dataset.salida){const v=t.dataset.salida;try{await api(`/visita/${v}/salida`,{nota:DR["nota-"+v]||""});delete DR["nota-"+v];flash("Parte enviado");route(true)}catch(err){const b=$("#sal-err-"+v);if(b)b.innerHTML=errBox(err.message)}return}
    if(t.dataset.extra!==undefined&&t.dataset.id&&t.dataset.llegada===undefined){await api(`/extra/${t.dataset.id}/responder`,{si:t.dataset.extra==="1"});return route(true)}
    if(t.dataset.star){DR.star=+t.dataset.star;document.querySelectorAll("[data-star]").forEach(b=>b.setAttribute("aria-pressed",+b.dataset.star<=DR.star));return}
    if(t.dataset.seqv){DR.seq=+t.dataset.seqv;document.querySelectorAll("[data-seqv]").forEach(b=>b.setAttribute("aria-pressed",b===t));return}
    const a=t.dataset.act;
    if(a==="close-modal"){if(e.target===t||t.tagName==="BUTTON")closeModal();return}
    if(a==="theme"){const r=document.documentElement;const dark=r.dataset.theme?r.dataset.theme==="dark":matchMedia("(prefers-color-scheme: dark)").matches;r.dataset.theme=dark?"light":"dark";try{localStorage.setItem("tsv-theme",r.dataset.theme)}catch(_){}return}
    if(a==="logout"){try{await api("/salir",{})}catch(_){}setToken(null);ME=null;W=null;if(ES)ES.close();location.hash="#/entrar";route();return}
    if(a==="notif-perm"){const r=await Notification.requestPermission();track("permiso_notificaciones",{r});route(true);return}
    if(a==="w-back"){W.step--;wSave();route(true);return}
    if(a==="w-relax"){W.opt[t.dataset.k]=false;track("sugerencia_precision",{k:t.dataset.k});wSave();W.res=null;wCount(true);route(true);return}
    if(a==="cancel-ad"){if(!confirm("¿Cancelar el anuncio? No tiene coste."))return;await api(`/anuncio/${t.dataset.id}/cancelar`,{});location.hash="#/inicio";return}
    if(a==="ser-del"){await api("/seres/borrar",{id:+t.dataset.id});W=null;return route(true).then(()=>route())}
    if(a==="dispo-del"){await api("/disponibilidad",{borrar:+t.dataset.id});return route()}
    if(a==="retirar"){if(!confirm("¿Retirar tu candidatura?"))return;await api(`/candidaturas/${t.dataset.id}/retirar`,{});return route()}
    if(a==="pedir-extra"){await api(`/extra/${t.dataset.id}`,{});flash("Visita extra pedida");return route(true)}
    if(a==="cancelar-cuid"){if(!confirm("¿Seguro que no puedes? Avisaremos a la dueña y buscaremos sustituto."))return;await api(`/reserva/${t.dataset.id}/cancelar`,{});location.hash="#/servicios";return}
  }catch(err){flash(err.message)}
});
document.addEventListener("input",e=>{
  const t=e.target;
  if(t.dataset.draft){DR[t.dataset.draft]=t.value;if(t.id==="chat-in")escribiendo(t.closest("form").dataset.cid);return}
  if(t.dataset.w==="nota"){W.nota=t.value;wSave()}
});
let escT=0;function escribiendo(cid){if(Date.now()-escT<2500)return;escT=Date.now();api("/escribiendo",{cand:+cid}).catch(()=>{})}
document.addEventListener("change",async e=>{
  const t=e.target;
  if(t.dataset.w&&t.dataset.w!=="nota"){W[t.dataset.w]=t.value;if(t.dataset.w==="inicio"&&W.fin&&parseD(W.fin)<=parseD(W.inicio))W.fin=iso(addDays(parseD(W.inicio),5));W.res=null;wSave();wCount(true);route(true);return}
  if(t.dataset.wser){const id=+t.dataset.wser;W.seres=t.checked?[...new Set([...W.seres,id])]:W.seres.filter(x=>x!==id);W.opt=null;W.res=null;wSave();route(true);return}
  if("wfr" in t.dataset){W.franja=t.value;W.res=null;wSave();wCount(true);return}
  if(t.dataset.wcheck){W[t.dataset.wcheck]=t.checked;W.res=null;wSave();wCount(true);return}
  if(t.dataset.wopt){W.opt[t.dataset.wopt]=t.checked;track("precision_cambiada",{k:t.dataset.wopt,on:t.checked});wSave();wCount();return}
  if(t.dataset.motivo){const x=JSON.parse(t.dataset.motivo);try{await api(`/visita/${x.v}/tareas`,{tareas:[{ser_id:x.s,estado:x.e,motivo:t.value}]})}catch(err){flash(err.message)}return}
  if(t.dataset.foto){const f=t.files&&t.files[0];if(!f)return;try{const data=await comprimir(f);await api(`/visita/${t.dataset.foto}/foto`,{data});route(true)}catch(err){flash(err.message||"No se ha podido subir la foto")}return}
  if(t.name==="asp"){DR.asp=t.value}
  if(t.name==="s-tipo"){const f=t.form,pl=t.value==="pl";f.dataset.tipo=t.value;f.querySelectorAll('input[name^="s-esp-"]').forEach(i=>i.checked=false);if(pl)$("#s-med").checked=false;
    $("#s-nom").placeholder=pl?"Calatheas del salón, Potus de la entrada…":"Lola, Kiwi…";
    $("#s-instr").placeholder=pl?"Cuánta agua, si pulverizar, dónde tiene luz, sin sol directo…":"Cuánta comida, dónde está, el arenero, cada cuánto…";
    $("#s-alarma").placeholder=pl?"Hojas amarillas o caídas, tierra encharcada…":"Si no come o se esconde, avísame";serInfo(f);return}
  if(t.name&&t.name.indexOf("s-esp-")===0){serInfo(t.form);return}
});
function serInfo(f){
  const el=$("#s-info");if(!el)return;const i=f.querySelector('input[name="s-esp-'+f.dataset.tipo+'"]:checked');
  const e=i&&CAT.especies.find(x=>x.id===+i.value);if(!e){el.hidden=true;return}
  let t;
  if(!e.activa)t="De momento no cuidamos "+e.nombre.toLowerCase()+"s. Te avisaremos cuando empecemos.";
  else if(e.cat==="pl")t="Riego cada "+plural(e.cada,"día","días")+" · dificultad "+e.dif+" de 5"+(e.formacion?" · solo te avisaremos a cuidadores con la insignia «Plantas delicadas».":".");
  else if(e.cat==="ex")t="Exótico · solo te avisaremos a cuidadores certificados en "+(e.grupo==="ave"?"aves":"reptiles")+".";
  else t=e.cada>1?"Visita cada "+plural(e.cada,"día","días")+".":"Visita diaria.";
  el.textContent=t;el.hidden=false;
}
document.addEventListener("submit",async e=>{
  const f=e.target;e.preventDefault();
  try{
    if(f.id==="f-login"){
      try{const j=await api("/entrar",{correo:$("#l-mail").value,clave:$("#l-pass").value});setToken(j.token);await cargarYo();conectarStream();location.hash="#/inicio";route()}catch(err){$("#login-err").innerHTML=errBox(err.message)}return;
    }
    if(f.id==="f-reg"){
      const b={rol:f.querySelector("input[name=rol]:checked").value,nombre:$("#r-nombre").value,correo:$("#r-correo").value,clave:$("#r-clave").value,cp:$("#r-cp").value};
      const j=await api("/registro",b);
      ["nombre","correo","clave","cp"].forEach(k=>{const el=$("#r-"+k),er=$("#e-"+k);const m=j.errores&&j.errores[k];el.setAttribute("aria-invalid",!!m);if(m){el.setAttribute("aria-describedby","e-"+k)}er.hidden=!m;er.textContent=m||""});
      if(j.errores){const k=Object.keys(j.errores)[0];const el=$("#r-"+k);if(el)el.focus();return}
      setToken(j.token);await cargarYo();conectarStream();location.hash=ME.rol==="dueno"?"#/casa":"#/perfil";route();return;
    }
    if(f.id==="f-wiz"){
      if(W.step===1&&Object.keys(wValid()).length)return;
      if(W.step===2&&!(W.res&&W.res.n))return;
      if(W.step<3){W.step++;track("wizard_paso",{paso:W.step});wSave();route(true);return}
      try{const j=await api("/anuncios",W);const kk="tsv-wiz-"+FRAME+"-"+ME.id;W=null;try{localStorage.removeItem(kk)}catch(_){}location.hash="#/anuncio/"+j.id}catch(err){$("#pub-err").innerHTML=errBox(err.message)}return;
    }
    if(f.id==="f-chat"){enviarChat(f.dataset.cid,$("#chat-in").value);return}
    if(f.id==="f-cand"){try{const j=await api("/candidaturas",{anuncio:+f.dataset.id,mensaje:$("#cand-msg").value});delete DR["cand-"+f.dataset.id];flash("Te has presentado");location.hash="#/mensajes/"+j.id}catch(err){$("#cand-err").innerHTML=errBox(err.message)}return}
    if(f.id==="f-relax"){const opt={};f.querySelectorAll("[data-ropt]").forEach(i=>opt[i.dataset.ropt]=i.checked);const j=await api(`/anuncio/${location.hash.split("/")[2]}/precision`,{opt});flash(j.nuevos?`Hemos avisado a ${plural(j.nuevos,"cuidador más","cuidadores más")}`:"Guardado. No hay cuidadores nuevos con estos requisitos");route(true);return}
    if(f.id==="f-ser"){const sel=f.querySelector('input[name="s-esp-'+f.dataset.tipo+'"]:checked');if(!sel){$("#ser-err").innerHTML=errBox(f.dataset.tipo==="pl"?"Elige qué planta es.":"Elige qué animal es.");return}try{await api("/seres",{especie_id:sel.value,nombre:$("#s-nom").value,cantidad:$("#s-cant").value,instr:$("#s-instr").value,alarma:$("#s-alarma").value,medicacion:f.dataset.tipo==="an"&&$("#s-med").checked});W=null;flash("Añadido a tu ficha");route()}catch(err){$("#ser-err").innerHTML=errBox(err.message)}return}
    if(f.id==="f-casa"){await api("/casa",{direccion:$("#c-dir").value,acceso:$("#c-acc").value,instr_acceso:$("#c-instr").value,veterinario:$("#c-vet").value,emergencia:$("#c-em").value});flash("Datos de la casa guardados");return}
    if(f.id==="f-dispo"){const j=await api("/disponibilidad",{inicio:$("#d-i").value,fin:$("#d-f").value});flash(j.nuevos_avisos?`Hay ${plural(j.nuevos_avisos,"solicitud nueva","solicitudes nuevas")} para ti`:"Disponibilidad guardada");route();return}
    if(f.id==="f-perfil"){
      const j=await api("/perfil",{bio:$("#p-bio").value,acepta_an:$("#p-an").checked,acepta_pl:$("#p-pl").checked,medicacion:$("#p-med").checked,
        zonas:[...f.querySelectorAll("[data-zona]:checked")].map(i=>i.dataset.zona),franjas:[...f.querySelectorAll("[data-fr]:checked")].map(i=>i.dataset.fr).join(""),
        especies:[...f.querySelectorAll("[data-esp]:checked")].map(i=>i.dataset.esp)});
      flash(j.nuevos_avisos?`Perfil guardado. Hay ${plural(j.nuevos_avisos,"solicitud nueva","solicitudes nuevas")} para ti`:"Perfil guardado");ME=await api("/yo");return;
    }
    if(f.id==="f-resena"){if(!DR.star){$("#res-err").innerHTML=errBox("Elige de 1 a 5 estrellas");return}await api("/resena",{anuncio:+f.dataset.id,puntos:DR.star,texto:DR["res-t"]||"",aspecto:DR.asp||"",confianza:!!($("#res-conf")&&$("#res-conf").checked)});DR.star=0;DR.asp="";DR["res-t"]="";flash("Gracias por tu valoración");route(true);return}
    if(f.id==="f-seq"){await api("/seq",{tarea:f.dataset.tarea,seq:DR.seq,esperaba:$("#seq-t").value});closeModal();flash("¡Gracias!");return}
  }catch(err){flash(err.message)}
});
async function enviarChat(cid,texto){
  texto=(texto||"").trim();if(!texto)return;
  DR["chat-"+cid]="";const i=$("#chat-in");if(i)i.value="";
  try{await api("/chat/"+cid,{texto});route(true)}catch(err){DR["chat-"+cid]=texto;flash(err.message);route(true)}
}
document.addEventListener("keydown",e=>{if(e.key==="Escape"&&$("#layer").innerHTML)closeModal()});
window.addEventListener("hashchange",()=>route());
try{const th=localStorage.getItem("tsv-theme");if(th)document.documentElement.dataset.theme=th}catch(e){}
route();
})();
