from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel, Field
from app.database.database import get_db
from app.database.models import User, Agent, AgentSource, AgentRun, AuditLog
from app.auth.deps import get_current_user

router = APIRouter()


class AgentSourceCreate(BaseModel):
    source_type: str = "rss"
    url: str
    name: Optional[str] = None
    config: Optional[dict] = {}


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: Optional[str] = None
    instructions: str = Field(..., min_length=1)
    model: str = "auto"
    schedule_interval_minutes: int = Field(default=30, ge=5, le=1440)
    notification_enabled: bool = True
    permissions: Optional[dict] = {}
    sources: Optional[List[AgentSourceCreate]] = []
    status: str = "off"


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    instructions: Optional[str] = None
    model: Optional[str] = None
    schedule_interval_minutes: Optional[int] = Field(default=None, ge=5, le=1440)
    notification_enabled: Optional[bool] = None
    permissions: Optional[dict] = None
    status: Optional[str] = None


class AgentSourceResponse(BaseModel):
    id: int
    source_type: str
    url: str
    name: Optional[str]
    is_active: bool
    
    class Config:
        from_attributes = True


class AgentResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    instructions: str
    model: str
    schedule_interval_minutes: int
    status: str
    notification_enabled: bool
    permissions: Optional[dict]
    last_run_at: Optional[datetime]
    next_run_at: Optional[datetime]
    created_at: Optional[datetime]
    sources: List[AgentSourceResponse] = []
    
    class Config:
        from_attributes = True


class AgentRunResponse(BaseModel):
    id: int
    status: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    duration_ms: Optional[int]
    sources_checked: int
    changes_detected: int
    model_used: Optional[str]
    provider_used: Optional[str]
    summary: Optional[str]
    ai_result: Optional[str]
    notification_sent: bool
    error_message: Optional[str]
    raw_data: Optional[dict] = None
    routing_note: Optional[str] = None
    was_fallback: Optional[bool] = None
    
    class Config:
        from_attributes = True
    
    @classmethod
    def model_validate(cls, obj, **kwargs):
        data = super().model_validate(obj, **kwargs)
        # Lift routing fields from raw_data for UI
        raw = getattr(obj, "raw_data", None) or {}
        if isinstance(raw, dict):
            if not data.routing_note:
                object.__setattr__(data, "routing_note", raw.get("routing_note"))
            if data.was_fallback is None:
                object.__setattr__(data, "was_fallback", raw.get("was_fallback"))
        return data


class NaturalLanguageAgentRequest(BaseModel):
    prompt: str = Field(..., min_length=5)


@router.get("", response_model=List[AgentResponse])
async def list_agents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agents = db.query(Agent).filter(Agent.user_id == current_user.id).order_by(Agent.created_at.desc()).all()
    return [AgentResponse.model_validate(a) for a in agents]


@router.post("", response_model=AgentResponse, status_code=201)
async def create_agent(
    req: AgentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = Agent(
        user_id=current_user.id,
        name=req.name,
        description=req.description,
        instructions=req.instructions,
        model=req.model,
        schedule_interval_minutes=req.schedule_interval_minutes,
        status=req.status,
        notification_enabled=req.notification_enabled,
        permissions=req.permissions or {},
    )
    if req.status == "on":
        agent.next_run_at = datetime.now(timezone.utc) + timedelta(minutes=1)
    
    db.add(agent)
    db.flush()
    
    for src in (req.sources or []):
        source = AgentSource(
            agent_id=agent.id,
            source_type=src.source_type,
            url=src.url,
            name=src.name or src.url,
            config=src.config or {},
        )
        db.add(source)
    
    audit = AuditLog(
        user_id=current_user.id,
        action="agent_created",
        resource_type="agent",
        resource_id=agent.id,
        details={"name": agent.name},
    )
    db.add(audit)
    db.commit()
    db.refresh(agent)
    return AgentResponse.model_validate(agent)


@router.post("/from-prompt", response_model=AgentResponse, status_code=201)
async def create_agent_from_prompt(
    req: NaturalLanguageAgentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Natural language agent creation.
    Uses simple heuristics for MVP; later can call AI to parse.
    """
    prompt_lower = req.prompt.lower()
    
    # Derive a name
    name = "Custom Agent"
    if "apple" in prompt_lower:
        name = "Apple Watcher"
    elif "news" in prompt_lower:
        name = "AI News Watcher"
    elif "email" in prompt_lower or "gmail" in prompt_lower:
        name = "Important Emails"
    elif "github" in prompt_lower:
        name = "GitHub Monitor"
    else:
        # Take first few words
        words = req.prompt.strip().split()[:4]
        name = " ".join(words).title()[:64] or "Custom Agent"
    
    # Default RSS sources based on keywords
    sources = []
    if "apple" in prompt_lower:
        sources.append(AgentSourceCreate(
            source_type="rss",
            url="https://www.apple.com/newsroom/rss-feed.rss",
            name="Apple Newsroom",
        ))
    if "ai" in prompt_lower or "news" in prompt_lower:
        sources.append(AgentSourceCreate(
            source_type="rss",
            url="https://feeds.feedburner.com/TechCrunch",
            name="TechCrunch",
        ))
        sources.append(AgentSourceCreate(
            source_type="rss",
            url="https://rss.arxiv.org/rss/cs.AI",
            name="arXiv AI",
        ))
    
    if not sources:
        sources.append(AgentSourceCreate(
            source_type="rss",
            url="https://feeds.feedburner.com/TechCrunch",
            name="TechCrunch",
        ))
    
    agent = Agent(
        user_id=current_user.id,
        name=name,
        description=req.prompt[:500],
        instructions=f"Monitor the configured sources and detect important information matching: {req.prompt}\n\nSummarize only significant changes or announcements. Ignore routine updates.",
        model="auto",
        schedule_interval_minutes=30,
        status="off",
        notification_enabled=True,
        permissions={},
    )
    db.add(agent)
    db.flush()
    
    for src in sources:
        source = AgentSource(
            agent_id=agent.id,
            source_type=src.source_type,
            url=src.url,
            name=src.name,
            config={},
        )
        db.add(source)
    
    audit = AuditLog(
        user_id=current_user.id,
        action="agent_created_from_prompt",
        resource_type="agent",
        resource_id=agent.id,
        details={"prompt": req.prompt[:200], "name": name},
    )
    db.add(audit)
    db.commit()
    db.refresh(agent)
    return AgentResponse.model_validate(agent)


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == current_user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return AgentResponse.model_validate(agent)


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: int,
    req: AgentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == current_user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    update_data = req.model_dump(exclude_unset=True)
    old_status = agent.status
    
    for key, value in update_data.items():
        setattr(agent, key, value)
    
    if "status" in update_data:
        if update_data["status"] == "on" and old_status != "on":
            agent.next_run_at = datetime.now(timezone.utc) + timedelta(minutes=1)
            action = "agent_enabled"
        elif update_data["status"] == "off" and old_status != "off":
            agent.next_run_at = None
            action = "agent_disabled"
        else:
            action = "agent_updated"
    else:
        action = "agent_updated"
    
    audit = AuditLog(
        user_id=current_user.id,
        action=action,
        resource_type="agent",
        resource_id=agent.id,
        details=update_data,
    )
    db.add(audit)
    db.commit()
    db.refresh(agent)
    return AgentResponse.model_validate(agent)


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == current_user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    audit = AuditLog(
        user_id=current_user.id,
        action="agent_deleted",
        resource_type="agent",
        resource_id=agent.id,
        details={"name": agent.name},
    )
    db.add(audit)
    db.delete(agent)
    db.commit()
    return None


@router.get("/{agent_id}/runs", response_model=List[AgentRunResponse])
async def list_agent_runs(
    agent_id: int,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == current_user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    runs = (
        db.query(AgentRun)
        .filter(AgentRun.agent_id == agent_id)
        .order_by(AgentRun.started_at.desc())
        .limit(limit)
        .all()
    )
    return [AgentRunResponse.model_validate(r) for r in runs]


@router.get("/{agent_id}/runs/{run_id}", response_model=AgentRunResponse)
async def get_agent_run(
    agent_id: int,
    run_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == current_user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    run = db.query(AgentRun).filter(AgentRun.id == run_id, AgentRun.agent_id == agent_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return AgentRunResponse.model_validate(run)


@router.post("/{agent_id}/run-now", response_model=AgentRunResponse)
async def run_agent_now(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Trigger an immediate agent run (async in background later)."""
    from app.agents.executor import execute_agent
    
    agent = db.query(Agent).filter(Agent.id == agent_id, Agent.user_id == current_user.id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    run = await execute_agent(agent, db)
    return AgentRunResponse.model_validate(run)
