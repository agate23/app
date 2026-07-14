const $ = (id) => document.getElementById(id);
let token = localStorage.getItem('agateToken') || '';
let socket = null;
let peer = null;
let profiles = [];
let currentProfile = 0;
let installPrompt = null;

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData)) headers.set('Content-Type', 'application/json');
  const response = await fetch(path, {...options, headers});
  if (response.status === 401) logout();
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || `Erro ${response.status}`);
  }
  return response;
}

async function pair() {
  $('pairError').textContent = '';
  try {
    const response = await api('/api/pair', {method:'POST', body:JSON.stringify({pin:$('pinInput').value.trim()})});
    const data = await response.json();
    token = data.token;
    localStorage.setItem('agateToken', token);
    await enterApp();
  } catch (error) { $('pairError').textContent = error.message; }
}

function logout() {
  localStorage.removeItem('agateToken');
  token = '';
  if (socket) socket.close();
  if (peer) peer.close();
  $('appView').hidden = true;
  $('pairView').hidden = false;
}

async function enterApp() {
  try { await (await api('/api/status')).json(); }
  catch (_) { logout(); return; }
  $('pairView').hidden = true;
  $('appView').hidden = false;
  connectSocket();
  await Promise.all([loadInfo(), loadProfiles(), refreshFiles(), refreshStatus()]);
  setInterval(refreshStatus, 4000);
}

function connectSocket() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  socket = new WebSocket(`${protocol}//${location.host}/ws/control?token=${encodeURIComponent(token)}`);
  socket.onopen = () => { $('connectionBadge').textContent='Online'; $('connectionBadge').classList.add('online'); };
  socket.onclose = () => { $('connectionBadge').textContent='Reconectando'; $('connectionBadge').classList.remove('online'); setTimeout(() => token && connectSocket(), 1500); };
}

function send(message) {
  if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message));
}

async function loadInfo() {
  const data = await (await api('/api/info')).json();
  $('computerName').textContent = data.computer;
  $('serverInfo').innerHTML = `<b>${data.computer}</b><br>Versão ${data.version}<br>${data.urls.map(value=>`<code>${value}</code>`).join('<br>')}<br>Tailscale: ${data.tailscale?'detectado':'não detectado'}`;
}

async function refreshStatus() {
  if (!token) return;
  try {
    const data = await (await api('/api/status')).json();
    $('cpuValue').textContent = Math.round(data.cpu);
    $('memoryValue').textContent = Math.round(data.memory);
    $('batteryValue').textContent = data.battery == null ? 'N/D' : `${data.battery}%`;
  } catch (_) {}
}

function setupTrackpad() {
  const pad = $('trackpad');
  let last = null, moved = false, lastTap = 0;
  pad.addEventListener('pointerdown', (event) => { pad.setPointerCapture(event.pointerId); last={x:event.clientX,y:event.clientY}; moved=false; });
  pad.addEventListener('pointermove', (event) => {
    if (!last) return;
    const dx=(event.clientX-last.x)*1.7, dy=(event.clientY-last.y)*1.7;
    if (Math.abs(dx)+Math.abs(dy)>2) { moved=true; send({action:'mouse_move',dx,dy}); }
    last={x:event.clientX,y:event.clientY};
  });
  pad.addEventListener('pointerup', () => {
    if (!moved) {
      const now=Date.now();
      send({action:'mouse_click',button:'left',clicks:now-lastTap<320?2:1});
      lastTap=now;
    }
    last=null;
  });
}

async function startScreen() {
  if (peer) peer.close();
  peer = new RTCPeerConnection({iceServers:[]});
  peer.addTransceiver('video', {direction:'recvonly'});
  peer.ontrack = (event) => { $('screenVideo').srcObject = event.streams[0]; };
  const offer = await peer.createOffer();
  await peer.setLocalDescription(offer);
  if (peer.iceGatheringState !== 'complete') await new Promise(resolve => {
    const listener = () => { if (peer.iceGatheringState === 'complete') { peer.removeEventListener('icegatheringstatechange', listener); resolve(); } };
    peer.addEventListener('icegatheringstatechange', listener);
    setTimeout(resolve, 3000);
  });
  const response = await api('/api/webrtc/offer', {method:'POST', body:JSON.stringify({
    sdp:peer.localDescription.sdp, type:peer.localDescription.type,
    fps:Number($('fpsSelect').value), quality:Number($('qualitySelect').value)
  })});
  await peer.setRemoteDescription(await response.json());
  $('startScreen').textContent='Reiniciar tela';
}

async function loadProfiles() {
  const data = await (await api('/api/profiles')).json();
  profiles = data.profiles || [];
  currentProfile = Math.min(currentProfile, Math.max(0, profiles.length-1));
  renderProfiles(); renderEditor();
}

function renderProfiles() {
  $('profileTabs').innerHTML='';
  profiles.forEach((profile,index)=>{
    const button=document.createElement('button'); button.textContent=profile.name; button.classList.toggle('active',index===currentProfile);
    button.onclick=()=>{currentProfile=index;renderProfiles();}; $('profileTabs').append(button);
  });
  $('profileActions').innerHTML='';
  (profiles[currentProfile]?.actions||[]).forEach(action=>{
    const button=document.createElement('button'); button.textContent=action.label;
    button.onclick=()=>runProfileAction(action); $('profileActions').append(button);
  });
}

function runProfileAction(action) {
  if (action.type==='key') send({action:'key',key:action.value});
  else if (action.type==='hotkey') send({action:'hotkey',keys:action.value});
  else if (action.type==='media') send({action:'media',value:action.value});
  else if (action.type==='text') send({action:'text',text:action.value});
  else if (action.type==='open_url') send({action:'open_url',url:action.value});
}

function renderEditor() {
  const root=$('editorProfiles'); root.innerHTML='';
  profiles.forEach((profile,pIndex)=>{
    const block=document.createElement('div'); block.className='profile-edit';
    block.innerHTML=`<input value="${escapeHtml(profile.name)}" data-profile-name="${pIndex}"><div data-actions="${pIndex}"></div><div class="button-row"><button data-add-action="${pIndex}">Adicionar ação</button><button class="danger" data-delete-profile="${pIndex}">Excluir perfil</button></div>`;
    root.append(block);
    const actions=block.querySelector(`[data-actions="${pIndex}"]`);
    profile.actions.forEach((action,aIndex)=>{
      const row=document.createElement('div'); row.className='action-edit';
      row.innerHTML=`<input placeholder="Nome" value="${escapeHtml(action.label)}" data-field="label"><select data-field="type">${['key','hotkey','media','text','open_url'].map(t=>`<option ${t===action.type?'selected':''}>${t}</option>`).join('')}</select><input placeholder="Valor" value="${escapeHtml(Array.isArray(action.value)?action.value.join('+'):String(action.value??''))}" data-field="value"><button class="danger">×</button>`;
      row.querySelector('button').onclick=()=>{profile.actions.splice(aIndex,1);renderEditor();}; actions.append(row);
    });
  });
  root.querySelectorAll('[data-profile-name]').forEach(input=>input.oninput=()=>profiles[Number(input.dataset.profileName)].name=input.value);
  root.querySelectorAll('[data-add-action]').forEach(button=>button.onclick=()=>{profiles[Number(button.dataset.addAction)].actions.push({label:'Nova ação',type:'key',value:'enter'});renderEditor();});
  root.querySelectorAll('[data-delete-profile]').forEach(button=>button.onclick=()=>{profiles.splice(Number(button.dataset.deleteProfile),1);renderEditor();renderProfiles();});
}

function collectEditor() {
  document.querySelectorAll('.profile-edit').forEach((block,pIndex)=>{
    block.querySelectorAll('.action-edit').forEach((row,aIndex)=>{
      const type=row.querySelector('[data-field="type"]').value;
      let value=row.querySelector('[data-field="value"]').value;
      if(type==='hotkey') value=value.split('+').map(v=>v.trim()).filter(Boolean);
      profiles[pIndex].actions[aIndex]={label:row.querySelector('[data-field="label"]').value,type,value};
    });
  });
}

async function saveProfileChanges() {
  collectEditor();
  const data = await (await api('/api/profiles',{method:'PUT',body:JSON.stringify({profiles})})).json();
  profiles=data.profiles; renderProfiles();renderEditor(); alert('Perfis salvos.');
}

async function refreshFiles() {
  const data = await (await api('/api/files')).json();
  $('fileList').innerHTML='';
  data.files.forEach(item=>{
    const row=document.createElement('div'); row.className='file-item';
    row.innerHTML=`<div><b>${escapeHtml(item.name)}</b><small>${formatBytes(item.size)} • ${new Date(item.modified*1000).toLocaleString()}</small></div><button>Baixar</button>`;
    row.querySelector('button').onclick=()=>downloadFile(item.name); $('fileList').append(row);
  });
}

async function uploadFile() {
  const file=$('fileInput').files[0]; if(!file) return;
  const form=new FormData(); form.append('file',file);
  $('uploadProgress').hidden=false; $('uploadProgress').value=20;
  try { await api('/api/files/upload',{method:'POST',body:form}); $('uploadProgress').value=100; await refreshFiles(); }
  catch(error){alert(error.message);} finally{setTimeout(()=>$('uploadProgress').hidden=true,700);}
}

async function downloadFile(name) {
  const response=await api(`/api/files/${encodeURIComponent(name)}`);
  const blob=await response.blob(); const url=URL.createObjectURL(blob);
  const anchor=document.createElement('a'); anchor.href=url; anchor.download=name; anchor.click(); URL.revokeObjectURL(url);
}

function escapeHtml(value){return String(value).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
function formatBytes(value){if(value<1024)return `${value} B`;if(value<1048576)return `${(value/1024).toFixed(1)} KB`;return `${(value/1048576).toFixed(1)} MB`;}

function setupStaticControls() {
  $('pairButton').onclick=pair; $('pinInput').onkeydown=e=>e.key==='Enter'&&pair(); $('logoutButton').onclick=logout;
  document.querySelectorAll('[data-tab]').forEach(button=>button.onclick=()=>{
    document.querySelectorAll('.tab').forEach(tab=>tab.classList.remove('active')); document.querySelectorAll('nav button').forEach(item=>item.classList.remove('active'));
    $(`tab-${button.dataset.tab}`).classList.add('active'); button.classList.add('active');
  });
  document.querySelectorAll('[data-click]').forEach(b=>b.onclick=()=>send({action:'mouse_click',button:b.dataset.click,clicks:1}));
  document.querySelectorAll('[data-scroll]').forEach(b=>b.onclick=()=>send({action:'mouse_scroll',amount:Number(b.dataset.scroll)}));
  document.querySelectorAll('[data-action]').forEach(b=>b.onclick=()=>send(JSON.parse(b.dataset.action)));
  $('sendText').onclick=()=>send({action:'text',text:$('textInput').value});
  $('pasteClipboard').onclick=()=>{send({action:'clipboard_get'}); socket?.addEventListener('message',event=>{const d=JSON.parse(event.data);if(d.clipboard)$('textInput').value=d.clipboard;},{once:true});};
  ['Esc','Enter','Tab','Backspace','↑','↓','←','→','Ctrl+S','Ctrl+Z'].forEach(label=>{
    const map={'Esc':'esc','Enter':'enter','Tab':'tab','Backspace':'backspace','↑':'up','↓':'down','←':'left','→':'right'}; const b=document.createElement('button'); b.textContent=label;
    b.onclick=()=>label.includes('+')?send({action:'hotkey',keys:label.toLowerCase().split('+')}):send({action:'key',key:map[label]}); $('specialKeys').append(b);
  });
  [['Anterior','previous'],['Play/Pause','play_pause'],['Próxima','next'],['Volume -','volume_down'],['Mudo','mute'],['Volume +','volume_up']].forEach(([label,value])=>{const b=document.createElement('button');b.textContent=label;b.onclick=()=>send({action:'media',value});$('mediaButtons').append(b);});
  $('startScreen').onclick=()=>startScreen().catch(e=>alert(e.message)); $('toggleEditor').onclick=()=>$('profileEditor').hidden=!$('profileEditor').hidden;
  $('addProfile').onclick=()=>{profiles.push({id:`custom-${Date.now()}`,name:'Novo perfil',icon:'tune',actions:[]});renderEditor();renderProfiles();};
  $('saveProfiles').onclick=()=>saveProfileChanges().catch(e=>alert(e.message)); $('uploadButton').onclick=uploadFile; $('refreshFiles').onclick=refreshFiles;
  $('installPwa').onclick=async()=>{if(installPrompt){installPrompt.prompt();await installPrompt.userChoice;installPrompt=null;}else alert('Use “Adicionar à tela inicial” no menu do navegador.');};
  window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();installPrompt=event;});
}

setupStaticControls(); setupTrackpad();
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(()=>{});
if (token) enterApp();
