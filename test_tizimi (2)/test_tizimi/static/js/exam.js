/* Exam + low-load camera monitoring, v20261012. */
document.addEventListener('DOMContentLoaded',async()=>{
  const $=id=>document.getElementById(id);
  const token=localStorage.getItem('auth_token'),testId=Number(location.pathname.split('/').filter(Boolean).pop());
  if(!token||!testId){location.href='/login';return;}
  let userId;
  try{userId=JSON.parse(atob(token.split('.')[1].replace(/-/g,'+').replace(/_/g,'/'))).sub;}catch{location.href='/login';return;}
  const key=`exam_monitor_v1_${userId}_${testId}`;
  let draft={};try{draft=JSON.parse(localStorage.getItem(key)||'{}');}catch{}
  let questions=[],answers={},index=0,state=null,settings={},camera=null,cameraReady=false;
  let pending=Array.isArray(draft.pending)?draft.pending:[],dirty=!!draft.dirty;
  let remaining=0,anchor=performance.now(),running=false,blocked=false,submitting=false,finished=false;
  let serial=Promise.resolve(),heartbeatTimer=null,timer=null,saveTimer=null,started=false,cameraStatus='waiting';
  let lastWarning=null,closing=false;
  let pendingReload=performance.getEntriesByType('navigation')[0]?.type==='reload';
  function reportReload(){if(pendingReload&&!blocked){pendingReload=false;event('reload','Test sahifasi qayta yuklandi.');}}
  const auth={'Content-Type':'application/json',Authorization:`Bearer ${token}`};
  function persist(){
    try{localStorage.setItem(key,JSON.stringify({answers,pending,dirty,epoch:state?.epoch??draft.epoch,index}));}
    catch{$('monitor-warning').textContent='Mahalliy saqlash ishlamadi. Serverga saqlash holatini tekshiring.';}
  }
  async function request(url,body){
    const c=new AbortController(),t=setTimeout(()=>c.abort(),12000);
    try{
      const res=await fetch(url,{method:body===undefined?'GET':'POST',headers:auth,body:body===undefined?undefined:JSON.stringify(body),signal:c.signal});
      const data=await res.json();if(!res.ok){const e=Error(data.detail||'Server xatosi');e.status=res.status;throw e;}return data;
    }finally{clearTimeout(t);}
  }
  function enqueue(fn){const next=serial.then(fn);serial=next.catch(()=>{});return next;}
  function projected(){return (state?.look_count||0)+pending.filter(e=>e.event_type==='look_away'&&e.epoch===state?.epoch).length;}
  function freezeLocal(){if(running)remaining=Math.max(0,remaining-(performance.now()-anchor)/1000);anchor=performance.now();running=false;}
  function updateLock(){
    const wasBlocked=blocked;
    blocked=state?.status==='BLOCKED'||projected()>=5;
    if(wasBlocked&&!blocked&&!finished){$('anti-cheat-modal').classList.remove('active');if(cameraReady)camera?.resume();}
    const disabled=blocked||submitting||finished||!started||(!cameraReady&&settings.enable_camera&&settings.camera_policy!=='allow_without_camera');
    $('question-card-container').inert=disabled;$('palette-grid').inert=disabled;$('btn-finish').disabled=disabled;
    $('question-card-container').style.opacity=disabled?'0.65':'1';
    $('camera-counter').textContent=`${projected()}/5`;
    if(blocked){
      freezeLocal();camera?.pause();$('anti-cheat-modal').classList.add('active');
      $('modal-warning-title').textContent='TEST TO‘XTATILDI';
      $('modal-warning-text').textContent=state?.block_reason||'5 ta holat qayd etildi. Administrator ruxsatini kuting.';
      $('modal-tab-count').textContent=`${projected()}/5`;
      $('btn-modal-continue').style.display='none';$('modal-blocked-waiting').style.display='block';
    }
  }
  function apply(data){
    const previousEpoch=state?.epoch;state=data;
    if(data.settings)settings=data.settings;
    pending=pending.filter(e=>e.epoch===data.epoch);
    remaining=data.remaining_seconds;anchor=performance.now();running=data.running;
    if(data.status==='FINISHED'){
      finished=true;camera?.stop();freezeLocal();$('monitor-warning').textContent='Test administrator tomonidan yakunlangan. Javoblar saqlangan.';
      $('anti-cheat-modal').classList.remove('active');
    }
    if(previousEpoch!==undefined&&previousEpoch!==data.epoch&&data.status==='ACTIVE'){
      $('anti-cheat-modal').classList.remove('active');lastWarning=null;
      if(settings.enable_camera){cameraReady=false;camera.start();}else cameraReady=true;
    }
    if(data.message&&data.message!==lastWarning){$('monitor-warning').textContent=data.message;lastWarning=data.message;}
    updateLock();persist();
  }
  async function flushEvents(){
    while(pending.length){
      const event=pending[0];
      if(event.epoch!==state.epoch){pending.shift();persist();continue;}
      const data=await request(`/api/camera-monitor/${testId}/event`,event);
      pending=pending.filter(e=>e.event_id!==event.event_id);apply(data);
    }
  }
  function event(type,details){
    if(!state||finished||submitting||blocked)return;
    pending.push({event_type:type,event_id:crypto.randomUUID(),epoch:state.epoch,answers:{...answers},details});
    persist();updateLock();
    enqueue(flushEvents).catch(networkError);
  }
  function networkError(e){
    $('monitor-save').textContent=e.status===403?'Server ruxsati yo‘q':'Aloqa yo‘q — javoblar shu qurilmada saqlanmoqda';
    if(e.status===403){finished=true;freezeLocal();camera?.stop();$('monitor-warning').textContent=e.message;updateLock();}
  }
  async function sync(){
    await flushEvents();
    const sent={...answers};
    const ready=started&&(!settings.enable_camera||cameraReady||settings.camera_policy==='allow_without_camera');
    const data=await request(`/api/camera-monitor/${testId}/sync`,{answers:sent,ready,camera_status:cameraStatus});
    apply(data);
    if(JSON.stringify(sent)===JSON.stringify(answers))dirty=false;
    persist();$('monitor-save').textContent='Javoblar serverda saqlandi';
  }
  function saveSoon(){dirty=true;persist();clearTimeout(saveTimer);saveTimer=setTimeout(()=>enqueue(sync).catch(networkError),600);}
  async function heartbeat(){
    if(closing||finished)return;
    try{await enqueue(sync);}catch(e){networkError(e);}
    if(!closing&&!finished)heartbeatTimer=setTimeout(heartbeat,5000);
  }
  function render(){
    const q=questions[index];if(!q)return;
    $('q-number-display').textContent=`Savol ${index+1} / ${questions.length}`;
    $('q-topic-display').textContent=q.topic_name||'';
    $('q-difficulty-display').textContent=({easy:'Oson',medium:'O‘rta',hard:'Qiyin'})[q.difficulty]||'O‘rta';
    $('q-text-display').textContent=q.question_text;$('options-container').replaceChildren();
    q.options.forEach((opt,i)=>{
      const button=document.createElement('button');button.type='button';button.className='option-btn';
      if(answers[q.id]===opt.id)button.classList.add('selected');
      const badge=document.createElement('span');badge.className='opt-badge';badge.textContent=String.fromCharCode(65+i);
      const text=document.createElement('span');text.className='opt-text';text.textContent=opt.option_text;
      button.append(badge,text);button.onclick=()=>{if(blocked||submitting)return;answers[q.id]=opt.id;saveSoon();render();};
      $('options-container').append(button);
    });
    $('palette-grid').replaceChildren();
    questions.forEach((q,i)=>{const b=document.createElement('button');b.type='button';b.className='palette-item';
      b.textContent=i+1;if(answers[q.id]!==undefined)b.classList.add('answered');if(index===i)b.classList.add('current');
      b.onclick=()=>{index=i;persist();render();};$('palette-grid').append(b);});
    $('count-answered').textContent=Object.keys(answers).length;
    $('count-unanswered').textContent=questions.length-Object.keys(answers).length;
    $('btn-prev').disabled=index===0;$('btn-next').disabled=index===questions.length-1;updateLock();
  }
  function tick(){
    const value=Math.max(0,Math.ceil(remaining-(running?(performance.now()-anchor)/1000:0)));
    $('timer-display').textContent=`${String(Math.floor(value/60)).padStart(2,'0')}:${String(value%60).padStart(2,'0')}`;
    $('timer-box').classList.toggle('warning',value<=300);
    if(value===0&&running&&!blocked&&!submitting&&!finished)submit();
  }
  async function submit(){
    if(submitting||blocked||finished)return;
    submitting=true;updateLock();$('btn-finish').textContent='Saqlanmoqda…';
    try{
      await enqueue(sync);
      if(blocked||finished)return;
      const result=await enqueue(()=>request('/api/student/test/submit',{test_id:testId,answers,tab_switch_count:0,time_spent_seconds:0}));
      finished=true;cleanup();localStorage.removeItem(key);location.href=`/result/${result.session_id}`;
    }catch(e){networkError(e);$('monitor-warning').textContent='Topshirish amalga oshmadi. Javoblar saqlangan; qayta urinib ko‘ring.';}
    finally{submitting=false;$('btn-finish').textContent='Testni yakunlash';updateLock();}
  }
  function cleanup(){closing=true;clearTimeout(heartbeatTimer);clearTimeout(saveTimer);clearInterval(timer);camera?.stop();}
  $('hdr-student-name').textContent=localStorage.getItem('user_full_name')||'O‘quvchi';
  $('hdr-student-group').textContent=localStorage.getItem('group_name')||'';
  $('btn-prev').onclick=()=>{if(index>0){index--;render();}};
  $('btn-next').onclick=()=>{if(index<questions.length-1){index++;render();}};
  $('btn-clear').onclick=()=>{if(blocked||submitting)return;delete answers[questions[index].id];saveSoon();render();};
  $('btn-finish').onclick=()=>{
    if(blocked)return;$('confirm-finish-message').textContent=`${questions.length} savoldan ${Object.keys(answers).length} tasiga javob berdingiz. Testni yakunlaysizmi?`;
    $('confirm-finish-modal').classList.add('active');};
  for(const id of ['btn-close-confirm','btn-cancel-finish'])$(id).onclick=()=>$('confirm-finish-modal').classList.remove('active');
  $('btn-submit-confirmed').onclick=()=>{$('confirm-finish-modal').classList.remove('active');submit();};
  $('btn-modal-continue').onclick=()=>{if(!blocked)$('anti-cheat-modal').classList.remove('active');};
  $('btn-fullscreen').onclick=()=>{if(!document.fullscreenElement)document.documentElement.requestFullscreen().catch(()=>{});else document.exitFullscreen().catch(()=>{});};
  window.addEventListener('pagehide',()=>{persist();cleanup();});
  window.addEventListener('online',()=>enqueue(sync).catch(networkError));
  try{
    const data=await request(`/api/student/test/${testId}`);questions=data.questions;
    if(!questions?.length)throw Error('Test savollari topilmadi.');
    $('hdr-test-title').textContent=`${data.test.subject_name} • ${data.test.title}`;
    const initial=await request(`/api/camera-monitor/${testId}/sync`,{});
    settings=initial.settings;
    answers=initial.answers||{};
    if(dirty&&draft.epoch===initial.epoch&&initial.status==='ACTIVE'){
      answers=Object.fromEntries(Object.entries(draft.answers||{}).filter(([qid,opt])=>questions.some(q=>String(q.id)===qid&&q.options.some(o=>o.id===opt))));
    }
    pending=pending.filter(e=>e.epoch===initial.epoch);index=Math.min(draft.index||0,questions.length-1);
    started=true;apply(initial);render();timer=setInterval(tick,250);tick();
    camera=new CameraMonitor({
      onReady:()=>{$('monitor-warning').textContent='Kamera nazorati faol. Testni boshlashingiz mumkin.';cameraReady=true;reportReload();event('camera_ready','Kamera moslashtirildi.');updateLock();enqueue(sync).catch(networkError);},
      onEvent:event,
      onStatus:kind=>{cameraStatus=kind;},
      onError:message=>{
        cameraReady=false;event('camera_error',message);updateLock();
        if(settings.camera_policy!=='allow_without_camera')freezeLocal();
        enqueue(sync).catch(networkError);
      }
    });
    $('camera-retry').onclick=()=>{if(!blocked&&!finished){cameraReady=false;updateLock();enqueue(sync).catch(networkError);camera.start();}};
    if(settings.enable_camera){$('camera-panel').hidden=false;if(!blocked)camera.start();}
    else{cameraReady=true;cameraStatus='off';$('camera-panel').hidden=true;$('monitor-warning').textContent='Test tayyor. Javoblar avtomatik saqlanadi.';}
    if(!settings.enable_camera)reportReload();
    heartbeat();
    // Ignore camera permission focus changes until calibration has finished.
    let leaveTimer=null;
    function leave(){
      if(!started||blocked||submitting||finished||(settings.enable_camera&&!cameraReady))return;
      clearTimeout(leaveTimer);leaveTimer=setTimeout(()=>{if(document.hidden||!document.hasFocus())event('tab_switch','Test oynasidan chiqildi.');},500);
    }
    document.addEventListener('visibilitychange',()=>{if(document.hidden)leave();});window.addEventListener('blur',leave);
    document.addEventListener('fullscreenchange',()=>{if(!document.fullscreenElement&&started&&cameraReady)event('fullscreen_exit','To‘liq ekran rejimidan chiqildi.');});
    for(const type of ['contextmenu','copy','cut'])document.addEventListener(type,e=>e.preventDefault());
  }catch(e){$('monitor-warning').textContent=e.message||'Testni ochib bo‘lmadi.';$('monitor-save').textContent='Sahifani qayta oching yoki administratorga murojaat qiling.';}
});
