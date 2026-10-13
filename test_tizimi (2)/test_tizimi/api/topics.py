from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from services.test_service import TestService
from services.auth_service import require_teacher, get_current_user

router = APIRouter(prefix="/api/topics", tags=["topics"])

class TopicCreate(BaseModel):
    name: str
    description: Optional[str] = ""

class TopicUpdate(BaseModel):
    name: str
    description: Optional[str] = ""

@router.get("")
def get_topics(user: dict = Depends(get_current_user)):
    return TestService.get_all_topics()

@router.post("")
def create_topic(data: TopicCreate, user: dict = Depends(require_teacher)):
    if not data.name.strip():
        raise HTTPException(status_code=400, detail="Mavzu nomi kiritilishi shart")
    try:
        topic_id = TestService.create_topic(data.name, data.description or "")
        return {"id": topic_id, "name": data.name, "message": "Mavzu muvaffaqiyatli qo'shildi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Mavzu qo'shishda xatolik: {e}")

@router.put("/{topic_id}")
def update_topic(topic_id: int, data: TopicUpdate, user: dict = Depends(require_teacher)):
    if not data.name.strip():
        raise HTTPException(status_code=400, detail="Mavzu nomi bo'sh bo'lishi mumkin emas")
    try:
        TestService.update_topic(topic_id, data.name, data.description or "")
        return {"id": topic_id, "message": "Mavzu muvaffaqiyatli yangilandi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Mavzuni yangilashda xatolik: {e}")

@router.delete("/{topic_id}")
def delete_topic(topic_id: int, user: dict = Depends(require_teacher)):
    try:
        TestService.delete_topic(topic_id)
        return {"message": "Mavzu muvaffaqiyatli o'chirildi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Mavzuni o'chirishda xatolik: {e}")

