from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from app.database.database import get_db
from app.database.models import User, Conversation, Message
from app.auth.deps import get_current_user
from app.ai.router import get_ai_router

router = APIRouter()


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)
    model: Optional[str] = "auto"


class MessageResponse(BaseModel):
    id: int
    role: str
    content: str
    model_used: Optional[str]
    provider_used: Optional[str]
    created_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    id: int
    title: str
    model: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    messages: List[MessageResponse] = []
    
    class Config:
        from_attributes = True


class ConversationListItem(BaseModel):
    id: int
    title: str
    model: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


@router.get("/conversations", response_model=List[ConversationListItem])
async def list_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    convs = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.updated_at.desc().nullslast(), Conversation.created_at.desc())
        .all()
    )
    return [ConversationListItem.model_validate(c) for c in convs]


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    model: str = "auto",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = Conversation(user_id=current_user.id, title="New Chat", model=model)
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return ConversationResponse.model_validate(conv)


@router.get("/conversations/{conv_id}", response_model=ConversationResponse)
async def get_conversation(
    conv_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id, Conversation.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationResponse.model_validate(conv)


@router.delete("/conversations/{conv_id}", status_code=204)
async def delete_conversation(
    conv_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id, Conversation.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    db.delete(conv)
    db.commit()
    return None


@router.patch("/conversations/{conv_id}")
async def rename_conversation(
    conv_id: int,
    title: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id, Conversation.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.title = title[:256]
    db.commit()
    return {"title": conv.title}


@router.post("/conversations/{conv_id}/messages", response_model=MessageResponse)
async def send_message(
    conv_id: int,
    req: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conv = db.query(Conversation).filter(
        Conversation.id == conv_id, Conversation.user_id == current_user.id
    ).first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Save user message
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=req.content,
    )
    db.add(user_msg)
    db.flush()
    
    # Build message history
    history = [
        {"role": m.role, "content": m.content}
        for m in conv.messages
    ]
    history.append({"role": "user", "content": req.content})
    
    # System prompt based on user preferences
    style = current_user.preferred_style or "professional"
    style_map = {
        "simple": "Respond simply and directly. Avoid unnecessary detail.",
        "detailed": "Provide detailed, thorough responses with explanations.",
        "friendly": "Be warm, friendly, and conversational.",
        "professional": "Be professional, clear, and precise.",
    }
    system = f"You are a helpful AI assistant in AI Command Center. {style_map.get(style, style_map['professional'])}"
    if current_user.display_name:
        system += f" The user's name is {current_user.display_name}."
    
    messages = [{"role": "system", "content": system}] + history
    
    model = req.model or conv.model or "auto"
    
    try:
        router_instance = get_ai_router()
        result = await router_instance.chat(
            messages=messages,
            user=current_user,
            db=db,
            model=model,
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=502, detail=str(e))
    
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=result["content"],
        model_used=result.get("model"),
        provider_used=result.get("provider"),
        tokens_used=(result.get("usage") or {}).get("total_tokens"),
    )
    db.add(assistant_msg)
    
    # Auto-title from first message
    if conv.title == "New Chat" and len(history) <= 1:
        conv.title = req.content[:60] + ("..." if len(req.content) > 60 else "")
    
    conv.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(assistant_msg)
    return MessageResponse.model_validate(assistant_msg)
