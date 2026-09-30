"""
Cloud agent scheduler — authoritative source of agent execution.
Agents continue when the desktop EXE is closed.
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timezone, timedelta
from app.database.database import SessionLocal
from app.database.models import Agent, AgentRun
from app.agents.executor import execute_agent
import logging
import asyncio

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_running_agents: set[int] = set()
_lock = asyncio.Lock()

# If next_run was more than this far in the past, record MISSED and reschedule
# instead of running a pile of catch-up jobs after downtime.
MAX_CATCHUP_MINUTES = 120


async def check_and_run_agents():
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        agents = (
            db.query(Agent)
            .filter(Agent.status == "on")
            .filter(
                (Agent.next_run_at == None) | (Agent.next_run_at <= now)
            )
            .all()
        )
        for agent in agents:
            agent_id = agent.id

            # Missed schedule recovery: if far overdue, skip catch-up spam
            if agent.next_run_at is not None:
                nxt = agent.next_run_at
                if nxt.tzinfo is None:
                    nxt = nxt.replace(tzinfo=timezone.utc)
                lag = (now - nxt).total_seconds() / 60.0
                if lag > MAX_CATCHUP_MINUTES:
                    logger.info(
                        f"Agent {agent_id} missed by {lag:.0f}m — recording skipped recovery run"
                    )
                    skip = AgentRun(
                        agent_id=agent_id,
                        status="skipped",
                        started_at=now,
                        completed_at=now,
                        summary=f"Missed while server offline ({int(lag)} minutes). Rescheduled.",
                        sources_checked=0,
                        changes_detected=0,
                        notification_sent=False,
                        raw_data={"reason": "missed_schedule", "lag_minutes": int(lag)},
                    )
                    db.add(skip)
                    agent.next_run_at = now + timedelta(
                        minutes=max(agent.schedule_interval_minutes, 5)
                    )
                    agent.last_run_at = now
                    db.commit()
                    continue

            async with _lock:
                if agent_id in _running_agents:
                    logger.debug(f"Agent {agent_id} already running — skip duplicate")
                    continue
                recent = (
                    db.query(AgentRun)
                    .filter(
                        AgentRun.agent_id == agent_id,
                        AgentRun.status.in_(["running", "pending"]),
                        AgentRun.started_at >= now - timedelta(minutes=10),
                    )
                    .first()
                )
                if recent:
                    logger.debug(f"Agent {agent_id} has active run {recent.id} — skip")
                    continue
                _running_agents.add(agent_id)

            try:
                logger.info(f"Running agent {agent_id}: {agent.name}")
                agent = db.query(Agent).filter(Agent.id == agent_id).first()
                if not agent or agent.status != "on":
                    continue
                await execute_agent(agent, db)
            except Exception as e:
                logger.exception(f"Failed to run agent {agent_id}: {e}")
                try:
                    agent = db.query(Agent).filter(Agent.id == agent_id).first()
                    if agent and agent.status == "on":
                        agent.next_run_at = datetime.now(timezone.utc) + timedelta(
                            minutes=max(agent.schedule_interval_minutes, 5)
                        )
                        db.commit()
                except Exception:
                    pass
            finally:
                async with _lock:
                    _running_agents.discard(agent_id)
    finally:
        db.close()


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            check_and_run_agents,
            trigger=IntervalTrigger(seconds=60),
            id="agent_scheduler",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
        logger.info("RainMoal agent scheduler started (cloud-authoritative)")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Agent scheduler stopped")


def scheduler_status() -> dict:
    return {
        "running": scheduler.running if scheduler else False,
        "jobs": len(scheduler.get_jobs()) if scheduler and scheduler.running else 0,
        "in_flight": len(_running_agents),
    }
