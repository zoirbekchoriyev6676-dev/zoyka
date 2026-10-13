/* Classic worker: dynamic import allows MediaPipe's WASM loader importScripts. */
let model=null;
self.onmessage=async ({data})=>{
  if(data.type==='init'){
    try{
      const {FaceLandmarker,FilesetResolver}=await import('/static/vendor/mediapipe/vision_bundle.mjs');
      const files=await FilesetResolver.forVisionTasks('/static/vendor/mediapipe/wasm');
      model=await FaceLandmarker.createFromOptions(files,{
        baseOptions:{modelAssetPath:'/static/models/face_landmarker.task',delegate:'CPU'},
        runningMode:'VIDEO',numFaces:2,minFaceDetectionConfidence:0.65,
        minFacePresenceConfidence:0.65,minTrackingConfidence:0.65,
        outputFaceBlendshapes:false,outputFacialTransformationMatrixes:false
      });
      self.postMessage({type:'ready'});
    }catch(e){self.postMessage({type:'error',message:String(e.message||e)});}
  }else if(data.type==='frame'){
    const started=performance.now();
    try{
      const result=model.detectForVideo(data.bitmap,data.timestamp);
      const face=result.faceLandmarks[0];
      let pose=null;
      if(result.faceLandmarks.length===1){
        const left=face[33],right=face[263],top=face[10],bottom=face[152];
        const width=Math.hypot(right.x-left.x,right.y-left.y);
        // z and x use the same normalization; y is scaled by frame aspect ratio.
        const aspect=data.height/data.width;
        pose={yaw:Math.atan2(right.z-left.z,right.x-left.x)*180/Math.PI,
          pitch:Math.atan2(bottom.z-top.z,(bottom.y-top.y)*aspect)*180/Math.PI,
          reliable:width>0.065 && face[1].x>0.08 && face[1].x<0.92};
      }
      self.postMessage({type:'result',faces:result.faceLandmarks.length,pose,ms:performance.now()-started});
    }catch(e){self.postMessage({type:'error',message:String(e.message||e)});}
    finally{data.bitmap.close();}
  }
};
