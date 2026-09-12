from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/network", tags=["Network"])

class CommentRequest(BaseModel):
    content: str
    agent_drafted: bool = False
    evidence_citation: Optional[str] = None

class ConnectRequest(BaseModel):
    target_profile_id: str
    outreach_note: str
    agent_generated: bool = False
    evidence_grounding: str = ""

class MessageRequest(BaseModel):
    receiver_id: str
    body: str
    agent_generated: bool = False
    evidence_grounding: str = ""

@router.get("/feed")
async def get_feed():
    return {"success": True, "data": []}

@router.post("/posts/{post_id}/like")
async def like_post(post_id: str):
    return {"success": True, "data": {"liked": True}}

@router.get("/posts/{post_id}/comments")
async def get_comments(post_id: str):
    return {"success": True, "data": []}

@router.post("/posts/{post_id}/comments")
async def post_comment(post_id: str, request: CommentRequest):
    return {
        "success": True,
        "data": {
            "id": "comm-mock",
            "post_id": post_id,
            "author_name": "You (Candidate)",
            "author_headline": "Candidate",
            "content": request.content,
            "agent_drafted": request.agent_drafted,
            "evidence_citation": request.evidence_citation,
            "created_at": "2024-01-01T00:00:00Z",
        }
    }

@router.get("/profiles")
async def get_network_profiles():
    return {"success": True, "data": []}

@router.get("/agent/proposals")
async def get_agent_proposals():
    return {"success": True, "data": []}

@router.post("/actions/connect")
async def send_connection_request(request: ConnectRequest):
    return {"success": True, "data": {"status": "PENDING"}}

@router.get("/messages")
async def get_messages(target_id: str):
    return {"success": True, "data": []}

@router.post("/actions/message")
async def send_message(request: MessageRequest):
    return {
        "success": True,
        "data": {
            "id": "msg-mock",
            "sender_id": "user_current_candidate",
            "receiver_id": request.receiver_id,
            "sender_name": "You",
            "body": request.body,
            "agent_generated": request.agent_generated,
            "evidence_grounding": request.evidence_grounding,
            "read": True,
            "created_at": "2024-01-01T00:00:00Z",
        }
    }
