"""
CareerOS — Profile Endpoint.

Serves the authenticated user's profile by aggregating data directly
from ResumeRepository (parsed sections + claims).
This is the single source of truth for what the user uploaded.
"""

import re
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException

from apps.api.app.core.security import AuthenticatedUser, get_current_user
from apps.api.app.repositories.resume_repository import ResumeRepository

from pydantic import BaseModel

router = APIRouter(prefix="/profiles", tags=["Profiles"])

_user_target_roles: dict[str, list[str]] = {}

class TargetRolesRequest(BaseModel):
    target_roles: list[str]

@router.post("/target-roles")
async def update_target_roles(
    request: TargetRolesRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
):
    _user_target_roles[str(current_user.user_id)] = request.target_roles
    return {"success": True, "data": {"target_roles": request.target_roles}}


def _extract_name_from_text(raw_text: str) -> str:
    """Extract the candidate name from the first line of resume text."""
    if not raw_text:
        return ""
    first_line = raw_text.strip().splitlines()[0].strip()
    for sep in ["Email:", "|", "Phone:", "Mobile:", "\u25cf"]:
        if sep in first_line:
            first_line = first_line.split(sep)[0].strip()
    return first_line.strip()


def _extract_location(raw_text: str) -> str:
    """Extract location from first few lines of resume text."""
    if not raw_text:
        return ""
    lines = raw_text.strip().splitlines()
    for line in lines[:5]:
        line_lower = line.lower()
        if any(kw in line_lower for kw in [
            "hyderabad", "bangalore", "mumbai", "delhi", "india",
            "san francisco", "new york", "chennai", "pune", "kolkata",
        ]):
            parts = line.strip().split("Mobile:")
            return parts[0].strip().rstrip(",").strip()
    return ""


def _extract_about(summary_text: str) -> str:
    """Extract the professional summary, skipping the contact info lines."""
    if not summary_text:
        return ""
    lines = summary_text.strip().splitlines()
    # Skip lines with contact info (name, email, location, links)
    content_lines = []
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        line_lower = line_stripped.lower()
        # Skip contact/header lines
        if any(kw in line_lower for kw in ["email:", "mobile:", "github |", "linkedin", "@gmail", "+91"]):
            continue
        # Skip if it looks like just a name (very short, no verbs)
        if len(line_stripped.split()) <= 3 and not any(c.islower() for c in line_stripped[:5]):
            continue
        content_lines.append(line_stripped)
    return " ".join(content_lines)


def _parse_experience_entries(exp_text: str) -> list[dict]:
    """
    Parse the EXPERIENCE section into structured entries.
    Each entry starts with a line like "Role | Company Date1 - Date2".
    """
    if not exp_text:
        return []

    entries = []
    # Split by double newlines or lines that look like role headers
    blocks = re.split(r"\n(?=[A-Z][\w\s]+\|)", exp_text)
    if len(blocks) <= 1:
        # Fallback: treat the whole thing as one entry
        blocks = [exp_text]

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        title_line = lines[0].strip()
        description = "\n".join(lines[1:]).strip()
        # Clean bullet characters
        description = description.replace("\u25cf", "\u2022")
        entries.append({
            "id": f"exp-{len(entries)+1}",
            "title": title_line,
            "description": description[:300],
            "provenance": "Resume",
            "date": "",
        })

    return entries


def _parse_project_entries(proj_text: str) -> list[dict]:
    """Parse the PROJECTS section into structured entries."""
    if not proj_text:
        return []

    entries = []
    # Split by project headers (lines starting with a project name followed by | GitHub or similar)
    blocks = re.split(r"\n(?=[A-Z][\w\s]+\|)", proj_text)
    if len(blocks) <= 1:
        blocks = re.split(r"\n\n+", proj_text)

    for block in blocks:
        block = block.strip()
        if not block:
            continue
        lines = block.splitlines()
        title_line = lines[0].strip()
        description = "\n".join(lines[1:]).strip()
        description = description.replace("\u25cf", "\u2022")
        entries.append({
            "id": f"proj-{len(entries)+1}",
            "title": title_line,
            "description": description[:300],
            "provenance": "Resume",
            "date": "",
        })

    return entries


@router.get("/me", response_model=dict)
async def get_my_profile(current_user: AuthenticatedUser = Depends(get_current_user)):
    """
    Build and return the user's profile from their most recent uploaded resume.
    Sources data from ResumeRepository (sections + claims).
    """
    user_id = current_user.user_id

    # 1. Find the user's most recent resume in the in-memory store
    user_resume = None
    user_resume_id = None
    for rid, rdoc in ResumeRepository._resumes.items():
        if rdoc.get("user_id") == user_id:
            user_resume = rdoc
            user_resume_id = rid
            break

    if not user_resume:
        return {"success": True, "data": {
            "handle": current_user.email.split("@")[0],
            "full_name": "",
            "headline": "Upload your resume to get started.",
            "location": "",
            "about": "",
            "target_roles": [],
            "verified_skills": [],
            "verified_evidence": [],
        }}

    raw_text = user_resume.get("raw_text", "")
    sections = user_resume.get("sections", {})
    claims = ResumeRepository._claims.get(user_resume_id, [])

    # 2. Extract candidate identity
    full_name = _extract_name_from_text(raw_text)
    location = _extract_location(raw_text)
    about = _extract_about(sections.get("SUMMARY", ""))
    headline = about[:120] + "..." if len(about) > 120 else about

    # 3. Build verified_skills from SKILL claims
    verified_skills = []
    seen_skills = set()
    for claim in claims:
        if claim.get("claim_type") == "SKILL":
            skill_name = claim.get("statement", "")
            if skill_name.lower() not in seen_skills:
                seen_skills.add(skill_name.lower())
                verified_skills.append({
                    "name": skill_name,
                    "confidence": claim.get("verification_status", "VERIFIED"),
                    "evidence": f"Extracted from resume: {user_resume.get('file_name', 'resume')}"
                })

    # 4. Build verified_evidence from EXPERIENCE and PROJECTS sections
    verified_evidence = []
    verified_evidence.extend(_parse_experience_entries(sections.get("EXPERIENCE", "")))
    verified_evidence.extend(_parse_project_entries(sections.get("PROJECTS", "")))

    # 5. Education
    edu_text = sections.get("EDUCATION", "")
    education_line = edu_text.strip().splitlines()[0] if edu_text.strip() else ""

    # 6. Credentials from CREDENTIAL claims (fallback if not explicitly set)
    target_roles = _user_target_roles.get(str(user_id))
    if target_roles is None:
        target_roles = []
        for claim in claims:
            if claim.get("claim_type") == "CREDENTIAL":
                target_roles.append(claim.get("statement", ""))

    profile_data = {
        "handle": current_user.email.split("@")[0],
        "full_name": full_name,
        "headline": headline if headline else "Profile extracted from resume",
        "location": location,
        "about": about,
        "education": education_line,
        "target_roles": target_roles,
        "verified_skills": verified_skills,
        "verified_evidence": verified_evidence,
    }

    return {"success": True, "data": profile_data}
