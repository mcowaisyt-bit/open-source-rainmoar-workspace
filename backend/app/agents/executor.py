import hashlib
import feedparser
import httpx
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.database.models import Agent, AgentRun, AgentSource, Notification, AuditLog
from app.ai.router import get_ai_router
import logging

logger = logging.getLogger(__name__)


async def fetch_rss(url: str) -> dict:
    """Fetch and parse an RSS feed."""
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "AI-Command-Center/1.0"})
            resp.raise_for_status()
            content = resp.text
    except Exception as e:
        return {"error": str(e), "entries": []}
    
    feed = feedparser.parse(content)
    entries = []
    for entry in feed.entries[:15]:
        entries.append({
            "title": getattr(entry, "title", ""),
            "link": getattr(entry, "link", ""),
            "summary": getattr(entry, "summary", "")[:500],
            "published": getattr(entry, "published", ""),
        })
    
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    return {
        "title": getattr(feed.feed, "title", url),
        "entries": entries,
        "content_hash": content_hash,
        "error": None,
    }


async def execute_agent(agent: Agent, db: Session) -> AgentRun:
    """
    Full agent execution pipeline:
    LOAD → CHECK PERMISSIONS → FETCH → DETECT CHANGES → AI ANALYSIS → ACTION → NOTIFY → LOG
    """
    run = AgentRun(
        agent_id=agent.id,
        status="running",
        started_at=datetime.now(timezone.utc),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    
    start = datetime.now(timezone.utc)
    
    try:
        sources_checked = 0
        changes = []
        all_new_items = []
        
        for source in agent.sources:
            if not source.is_active:
                continue
            sources_checked += 1
            
            if source.source_type == "rss":
                data = await fetch_rss(source.url)
                if data.get("error"):
                    logger.warning(f"RSS error for {source.url}: {data['error']}")
                    continue
                
                new_hash = data.get("content_hash")
                if source.last_content_hash and source.last_content_hash == new_hash:
                    # No change
                    source.last_fetched_at = datetime.now(timezone.utc)
                    continue
                
                # Detect new entries (simple: if hash changed, consider all current entries)
                for entry in data.get("entries", []):
                    all_new_items.append({
                        "source": source.name or source.url,
                        "title": entry["title"],
                        "link": entry["link"],
                        "summary": entry["summary"],
                        "published": entry["published"],
                    })
                
                source.last_content_hash = new_hash
                source.last_fetched_at = datetime.now(timezone.utc)
                changes.append({"source": source.name, "new_items": len(data.get("entries", []))})
        
        run.sources_checked = sources_checked
        run.changes_detected = len(all_new_items)
        
        if not all_new_items:
            run.status = "completed"
            run.summary = "No important changes detected."
            run.ai_result = "No new content found across monitored sources."
            run.completed_at = datetime.now(timezone.utc)
            run.duration_ms = int((run.completed_at - start).total_seconds() * 1000)
            agent.last_run_at = run.completed_at
            if agent.status == "on":
                agent.next_run_at = run.completed_at + timedelta(minutes=agent.schedule_interval_minutes)
            db.commit()
            return run
        
        # Send to AI for analysis
        items_text = "\n\n".join(
            f"**{item['title']}**\nSource: {item['source']}\n{item['summary']}\nLink: {item['link']}"
            for item in all_new_items[:10]
        )
        
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an AI agent monitoring information sources. "
                    "Analyze the following new items and determine if any are important "
                    "according to the agent's instructions. "
                    "If important, provide a concise summary and why it matters. "
                    "If nothing is important, say so clearly."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Agent instructions:\n{agent.instructions}\n\n"
                    f"New items from sources:\n{items_text}\n\n"
                    "Respond with:\n"
                    "IMPORTANT: yes/no\n"
                    "SUMMARY: ...\n"
                    "WHY IT MATTERS: ...\n"
                    "KEY ITEMS: ..."
                ),
            },
        ]
        
        router = get_ai_router()
        try:
            result = await router.chat(
                messages=messages,
                user=agent.user,
                db=db,
                model=agent.model or "auto",
                task_hint="classification",
            )
            ai_text = result["content"]
            run.model_used = result.get("model")
            run.provider_used = result.get("provider")
            run.ai_result = ai_text
            # Store routing / fallback visibility for UI
            if not run.raw_data:
                run.raw_data = {}
            run.raw_data = {
                **(run.raw_data or {}),
                "routing_note": result.get("routing_note"),
                "was_fallback": result.get("was_fallback", False),
                "fallback_log": result.get("fallback_log", []),
            }
        except Exception as e:
            run.ai_result = f"AI analysis failed: {e}"
            run.error_message = str(e)
            # Still complete the run with the raw data
            ai_text = f"Could not analyze with AI. Found {len(all_new_items)} new items."
        
        # Determine if important
        is_important = "IMPORTANT: yes" in (run.ai_result or "").upper() or "IMPORTANT: YES" in (run.ai_result or "")
        
        # Extract summary
        summary = run.ai_result or f"Found {len(all_new_items)} new items."
        if len(summary) > 500:
            summary = summary[:500] + "..."
        run.summary = summary
        
        # Notification
        if is_important and agent.notification_enabled:
            notif = Notification(
                user_id=agent.user_id,
                agent_id=agent.id,
                title=f"🔔 {agent.name}",
                body=summary[:300],
                data={
                    "run_id": run.id,
                    "agent_id": agent.id,
                    "items_count": len(all_new_items),
                },
            )
            db.add(notif)
            run.notification_sent = True
        
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        run.duration_ms = int((run.completed_at - start).total_seconds() * 1000)
        run.raw_data = {"items": all_new_items[:20], "changes": changes}
        
        agent.last_run_at = run.completed_at
        if agent.status == "on":
            agent.next_run_at = run.completed_at + timedelta(minutes=agent.schedule_interval_minutes)
        
        db.commit()
        db.refresh(run)
        return run
        
    except Exception as e:
        logger.exception(f"Agent {agent.id} execution failed")
        run.status = "failed"
        run.error_message = str(e)
        run.completed_at = datetime.now(timezone.utc)
        run.duration_ms = int((run.completed_at - start).total_seconds() * 1000)
        agent.last_run_at = run.completed_at
        if agent.status == "on":
            agent.next_run_at = run.completed_at + timedelta(minutes=agent.schedule_interval_minutes)
        db.commit()
        db.refresh(run)
        return run
