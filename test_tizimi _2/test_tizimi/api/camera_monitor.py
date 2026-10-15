from typing import Optional, Dict, Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, StrictInt
from services.auth_service import require_student
from services import camera_monitor as monitor

router=APIRouter(prefix='/api/camera-monitor',tags=['camera-monitor'])
class SyncRequest(BaseModel):
    answers: Optional[Dict[str,StrictInt]]=None
    ready: Optional[bool]=None
    camera_status: Optional[str]=Field(None,max_length=80)
class EventRequest(BaseModel):
    event_type: Literal['look_away','camera_error','camera_ready','face_missing','multiple_faces_notice','tab_switch','fullscreen_exit','reload']
    event_id: str=Field(min_length=8,max_length=80)
    epoch: int=Field(ge=0)
    answers: Optional[Dict[str,StrictInt]]=None
    details: str=Field('',max_length=500)

@router.post('/{test_id}/sync')
def sync(test_id:int,data:SyncRequest,user:dict=Depends(require_student)):
    try:return monitor.sync(user['student_id'],test_id,**data.model_dump())
    except ValueError as e:raise HTTPException(403,str(e))

@router.post('/{test_id}/event')
def report(test_id:int,data:EventRequest,user:dict=Depends(require_student)):
    try:return monitor.report(user['student_id'],test_id,**data.model_dump())
    except ValueError as e:raise HTTPException(403,str(e))
