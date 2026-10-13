(function(root){
  class CameraMonitor {
    constructor({onReady,onEvent,onStatus,onError}){
      Object.assign(this,{onReady,onEvent,onStatus,onError});
      this.rule=new GazeRule();this.generation=0;this.stream=null;this.worker=null;
      this.video=document.getElementById('camera-preview');this.timer=null;this.watchdog=null;
      this.base=null;this.samples=[];this.paused=false;this.lastVideoTime=-1;this.lastStatus=null;
    }
    status(text,kind){
      document.getElementById('camera-message').textContent=text;
      if(this.lastStatus!==kind){this.lastStatus=kind;this.onStatus(kind);}
    }
    async start(){
      this.stop();const generation=this.generation;
      this.paused=false;this.samples=[];this.base=null;this.rule.reset();this.lastVideoTime=-1;
      this.status('Kameraga ruxsat bering. So‘ng ekranning markaziga qarang.','waiting');
      try{
        if(!isSecureContext || !navigator.mediaDevices?.getUserMedia)throw Error('Kamera uchun HTTPS yoki localhost kerak.');
        if(!window.Worker || !window.createImageBitmap)throw Error('Bu brauzer kamera tahlilini qo‘llamaydi.');
        const stream=await navigator.mediaDevices.getUserMedia({audio:false,video:{width:{ideal:640,max:640},height:{ideal:480,max:480},frameRate:{ideal:10,max:15}}});
        if(generation!==this.generation){stream.getTracks().forEach(t=>t.stop());return;}
        this.stream=stream;this.video.srcObject=stream;await this.video.play();
        if(generation!==this.generation)return;
        stream.getVideoTracks()[0].addEventListener('ended',()=>{if(generation===this.generation)this.fail('Kamera uzildi. Qayta ulang.');});
        this.worker=new Worker('/static/js/camera-worker.js?v=20261012');
        this.worker.onerror=()=>this.fail('AI moduli ishlamadi. Kamerani qayta ishga tushiring.');
        this.worker.onmessage=({data})=>{
          if(generation!==this.generation)return;
          clearTimeout(this.watchdog);
          if(data.type==='error'){this.fail('Tasvir tahlilida xato. Kamerani qayta ishga tushiring.');return;}
          if(data.type==='ready'){this.schedule(0);return;}
          if(data.type==='result'){
            this.result(data);
            // At most 2 FPS. Slow CPUs wait at least 3x inference time before next frame.
            this.schedule(Math.max(500,Math.min(1500,data.ms*3)));
          }
        };
        this.worker.postMessage({type:'init'});
        this.watchdog=setTimeout(()=>this.fail('AI yuklanmadi. Model fayllarini va serverni tekshiring.'),45000);
      }catch(e){if(generation===this.generation)this.fail(e.name==='NotAllowedError'?'Kameraga ruxsat berilmadi. Brauzer ruxsatini yoqing.':String(e.message||e));}
    }
    schedule(delay){clearTimeout(this.timer);if(!this.paused)this.timer=setTimeout(()=>this.frame(),delay);}
    async frame(){
      const generation=this.generation;
      if(this.paused||!this.worker)return;
      if(document.hidden){this.rule.sample('unknown',performance.now());this.schedule(700);return;}
      if(this.video.readyState<2||this.video.currentTime===this.lastVideoTime){
        this.staleSince ??= performance.now();
        if(performance.now()-this.staleSince>5000){this.fail('Kamera tasviri to‘xtab qoldi. Qayta ulang.');return;}
        this.rule.sample('unknown',performance.now());this.schedule(500);return;
      }
      this.staleSince=null;this.lastVideoTime=this.video.currentTime;
      try{
        const width=480,height=Math.round(width*this.video.videoHeight/this.video.videoWidth);
        const bitmap=await createImageBitmap(this.video,{resizeWidth:width,resizeHeight:height});
        if(generation!==this.generation||this.paused){bitmap.close();return;}
        this.worker.postMessage({type:'frame',bitmap,width,height,timestamp:performance.now()},[bitmap]);
        this.watchdog=setTimeout(()=>this.fail('AI javobi kechikdi. Kamerani qayta ishga tushiring.'),10000);
      }catch(e){this.fail('Kamera tasvirini o‘qib bo‘lmadi.');}
    }
    result(data){
      if(this.paused)return;
      const now=performance.now();
      if(data.faces!==1||!data.pose?.reliable){
        this.rule.sample('unknown',now);this.samples=[];
        const kind=data.faces>1?'multiple_faces':'face_missing';
        this.status(data.faces>1?'Kadrda faqat o‘zingiz bo‘ling.':'Yuz to‘liq ko‘rinsin. Yorug‘likni va kamerani tekshiring.',kind);
        if(!this.noticeAt||now-this.noticeAt>15000){this.noticeAt=now;this.onEvent(data.faces>1?'multiple_faces_notice':'face_missing','Tasvir aniqligi yetarli emas; chetga qarash hisoblanmadi.');}
        return;
      }
      const {yaw,pitch}=data.pose;
      if(!this.base){
        if(Math.abs(yaw)>18){this.samples=[];this.status('Boshni to‘g‘ri tutib, ekranning markaziga qarang.','waiting');return;}
        this.samples.push({yaw,pitch,at:now});
        const ys=this.samples.map(x=>x.yaw),ps=this.samples.map(x=>x.pitch);
        if(Math.max(...ys)-Math.min(...ys)>8||Math.max(...ps)-Math.min(...ps)>8){this.samples=[{yaw,pitch,at:now}];}
        this.status('Moslashtirish: 3 soniya ekranning markaziga qarang.','waiting');
        if(this.samples.length>=4 && now-this.samples[0].at>=3000){
          const avg=k=>this.samples.reduce((n,x)=>n+x[k],0)/this.samples.length;
          this.base={yaw:avg('yaw'),pitch:avg('pitch')};this.samples=[];
          this.status('Kamera nazorati faol.','ready');this.onReady();
        }
        return;
      }
      const dy=Math.abs(yaw-this.base.yaw),dp=Math.abs(pitch-this.base.pitch);
      const kind=dy>=25||dp>=22?'away':(dy<=15&&dp<=14?'front':'unknown');
      this.status(kind==='away'?'Ekranga qarang.':'Kamera nazorati faol.','ready');
      if(this.rule.sample(kind,now))this.onEvent('look_away','Bosh yo‘nalishi 2 soniyadan ortiq ekrandan chetda.');
    }
    pause(){this.paused=true;clearTimeout(this.timer);this.rule.sample('unknown',performance.now());}
    resume(){this.paused=false;this.rule.reset();if(this.worker)this.schedule(0);}
    fail(message){this.stop();this.status(message,'technical_error');this.onError(message);}
    stop(){
      this.generation++;clearTimeout(this.timer);clearTimeout(this.watchdog);
      this.worker?.terminate();this.worker=null;
      this.stream?.getTracks().forEach(t=>t.stop());this.stream=null;
      if(this.video)this.video.srcObject=null;
    }
  }
  root.CameraMonitor=CameraMonitor;
})(window);
