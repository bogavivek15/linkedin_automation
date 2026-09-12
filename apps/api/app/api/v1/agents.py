"""
CareerOS Phase 16 — Agent Registry & Autonomous Orchestration API.

GET    /api/v1/agents                       - List 8 core autonomous agents
GET    /api/v1/agents/{agent_name}          - Get agent metadata & permissions
POST   /api/v1/agents/launch                - Launch multi-agent orchestration run
GET    /api/v1/agents/runs                  - List recent orchestration runs
GET    /api/v1/agents/runs/{run_id}         - Get run details & event timeline
POST   /api/v1/agents/runs/{run_id}/cancel  - Cancel run
"""


from apps.api.app.core.security import AuthenticatedUser, get_current_user
from apps.api.app.services.agents.service import AgentOrchestrationService
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/agents", tags=["Agent Orchestration"])

_service = AgentOrchestrationService()


class LaunchOrchestrationRequest(BaseModel):
    target_role: str = "AI Engineer"
    query: str = "python"


@router.get("", response_model=dict)
async def list_agents():
    """
    List the 8 core registered CareerOS autonomous agents.
    """
    agents = await _service.list_agents()
    return {"success": True, "data": [a.model_dump(mode="json") for a in agents]}


@router.get("/runs", response_model=dict)
async def list_runs(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    List recent multi-agent orchestration runs for user.
    """
    runs = await _service.list_runs(current_user.user_id, limit)
    return {"success": True, "data": [r.model_dump(mode="json") for r in runs]}


@router.get("/runs/{run_id}", response_model=dict)
async def get_run(
    run_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Get run details and observable event timeline.
    """
    run = await _service.get_run(run_id, current_user.user_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"success": True, "data": run.model_dump(mode="json")}


@router.post("/launch", response_model=dict)
async def launch_orchestration(
    request: LaunchOrchestrationRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Launch an orchestrated multi-agent run.
    """
    run = await _service.launch_orchestration(
        user_id=current_user.user_id,
        target_role=request.target_role,
        query=request.query,
    )
    return {"success": True, "data": run.model_dump(mode="json")}


@router.post("/runs/{run_id}/cancel", response_model=dict)
async def cancel_run(
    run_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    """
    Cancel an in-flight orchestration run.
    """
    cancelled = await _service.cancel_run(run_id, current_user.user_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"success": True, "data": {"cancelled": True}}




class Agent1Request(BaseModel):
    target_role: str
    resume_data: str = ""

@router.post("/run/agent1", response_model=dict)
async def run_agent1(
    request: Agent1Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    result = await _service.run_agent_1(target_role=request.target_role, resume_data=request.resume_data, user_id=current_user.user_id)
    return {"success": True, "data": result}

class Agent2Request(BaseModel):
    jobs_discovered: list

@router.post("/run/agent2", response_model=dict)
async def run_agent2(
    request: Agent2Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    result = await _service.run_agent_2(jobs_discovered=request.jobs_discovered, user_id=current_user.user_id)
    return {"success": True, "data": result}

class Agent3Request(BaseModel):
    genuine_jobs: list

@router.post("/run/agent3", response_model=dict)
async def run_agent3(
    request: Agent3Request,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    result = await _service.run_agent_3(genuine_jobs=request.genuine_jobs, user_id=current_user.user_id)
    return {"success": True, "data": result}

@router.post("/orchestrate", response_model=dict)
async def orchestrate_agents(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    from apps.api.app.api.v1.profiles import _user_target_roles
    from apps.api.app.repositories.resume_repository import ResumeRepository

    target_roles = _user_target_roles.get(str(current_user.user_id), [])
    
    # Try to fetch latest resume for this user
    user_resume = None
    for rid, rdoc in ResumeRepository._resumes.items():
        if rdoc.get("user_id") == current_user.user_id:
            user_resume = rdoc
            break
            
    resume_data = user_resume.get("raw_text", "") if user_resume else ""
    
    result = await _service.run_full_orchestration(target_roles=target_roles, resume_data=resume_data, user_id=current_user.user_id)
    return {"success": True, "data": result}

@router.get("/approvals", response_model=dict)
async def list_approvals(
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    from apps.api.app.repositories.agent_repository import AgentRepository
    approvals = await AgentRepository.get_pending_approvals(current_user.user_id)
    return {"success": True, "data": approvals}

@router.post("/approvals/{gen_id}/approve", response_model=dict)
async def approve_content(
    gen_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    post = await _service.approve_content(gen_id, current_user.user_id)
    if not post:
        raise HTTPException(status_code=404, detail="Approval request not found or already processed")
    return {"success": True, "data": post}

@router.get("/{agent_name}", response_model=dict)
async def get_agent(agent_name: str):
    """
    Get specific agent details.
    """
    agent = await _service.get_agent(agent_name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return {"success": True, "data": agent.model_dump(mode="json")}
