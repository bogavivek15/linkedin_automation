"""
CareerOS Phase 19 — CareerOS Network Repository.
Persistence and business logic for professional network entities and agent operations.
"""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from apps.api.app.domain.network.models import (
    AgentOutreachProposal,
    NetworkComment,
    NetworkConnection,
    NetworkMessage,
    NetworkPost,
    NetworkProfile,
)


class NetworkRepository:
    """
    In-memory & Supabase-compatible store for the CareerOS Network.
    """

    _profiles: dict[str, NetworkProfile] = {}
    _posts: dict[str, NetworkPost] = {}
    _comments: list[NetworkComment] = []
    _connections: dict[str, NetworkConnection] = {}
    _messages: list[NetworkMessage] = []
    _initialized: bool = False

    @classmethod
    def reset_store(cls) -> None:
        """Helper for test isolation."""
        cls._posts.clear()
        cls._comments.clear()
        cls._connections.clear()
        cls._messages.clear()
        cls._profiles.clear()
        cls._initialized = False
        cls._seed_defaults()

    @classmethod
    def _seed_defaults(cls):
        if cls._initialized:
            return

        p1 = NetworkProfile(
            id="a0000000-0000-0000-0000-000000000001",
            handle="sarahchen",
            full_name="Sarah Chen",
            headline="Senior Machine Learning Engineer @ Anthropic | Building Autonomous Agent Toolchains",
            company="Anthropic",
            location="San Francisco, CA",
            about="Researching agentic alignment, tool grounding, and context-window optimizations for frontier LLMs.",
            skills=["Python", "PyTorch", "LangGraph", "Agentic Systems", "Vector Search"],
            match_score=96,
            is_target=True,
            role_type="ENGINEER",
            connection_status="NONE",
        )
        p2 = NetworkProfile(
            id="a0000000-0000-0000-0000-000000000002",
            handle="davidkim",
            full_name="David Kim",
            headline="Staff Technical Recruiter @ Google DeepMind | Hiring AI/Systems Research Interns",
            company="Google DeepMind",
            location="New York, NY",
            about="Passionate about connecting exceptional student builders with cutting-edge reinforcement learning and LLM engineering teams.",
            skills=["Technical Recruiting", "AI Talent", "University Relations", "Engineering Leadership"],
            match_score=92,
            is_target=True,
            role_type="RECRUITER",
            connection_status="NONE",
        )
        p3 = NetworkProfile(
            id="a0000000-0000-0000-0000-000000000003",
            handle="elenarostova",
            full_name="Elena Rostova",
            headline="Co-Founder & CTO @ NexusAI (YC W24) | ex-OpenAI Systems",
            company="NexusAI",
            location="San Francisco, CA",
            about="Scaling high-throughput deterministic LLM inference engines. Looking for passionate backend and distributed systems interns.",
            skills=["Rust", "Distributed Systems", "CUDA", "Python", "FastAPI"],
            match_score=88,
            is_target=True,
            role_type="FOUNDER",
            connection_status="NONE",
        )
        p4 = NetworkProfile(
            id="a0000000-0000-0000-0000-000000000004",
            handle="marcusvance",
            full_name="Marcus Vance",
            headline="Lead AI Architect @ Scale AI | Multi-Agent Coordination & Synthetic Data",
            company="Scale AI",
            location="Seattle, WA",
            about="Architecting human-in-the-loop evaluation pipelines for enterprise agentic workflows.",
            skills=["Multi-Agent Systems", "Python", "Evaluation Metrics", "Kubernetes"],
            match_score=84,
            is_target=False,
            role_type="ENGINEER",
            connection_status="NONE",
        )

        for p in [p1, p2, p3, p4]:
            cls._profiles[p.id] = p

        post1 = NetworkPost(
            id="b0000000-0000-0000-0000-000000000001",
            author_id=p1.id,
            author_name=p1.full_name,
            author_headline=p1.headline,
            author_avatar=p1.avatar_url,
            content=(
                "One of the biggest mistakes I see candidates make when applying to agentic engineering roles "
                "is claiming 'hallucination-free LLM pipelines' without evidence provenance. If your system cannot cite "
                "the exact memory hash or verified document segment, it is not production ready. Grounding + deterministic guardrails is the future."
            ),
            likes_count=42,
            comments_count=2,
            tags=["AgenticAI", "PromptEngineering", "MachineLearning", "Grounding"],
            agent_relevance_note="Highly relevant to your verified LangChain evidence claims. Sarah frequently mentors students building deterministic evaluation guardrails.",
        )
        post2 = NetworkPost(
            id="b0000000-0000-0000-0000-000000000002",
            author_id=p2.id,
            author_name=p2.full_name,
            author_headline=p2.headline,
            author_avatar=p2.avatar_url,
            content=(
                "We just opened applications for our 2025 AI Systems & Autonomous Agents Engineering internships at DeepMind! "
                "We care far less about standard boilerplate leetcode grinding and far more about genuine open-source contributions, "
                "evidence-grounded projects, and clear problem solving. Reach out directly if you have built working agent orchestrators."
            ),
            likes_count=128,
            comments_count=14,
            tags=["DeepMind", "Internships", "Hiring", "GenerativeAI"],
            agent_relevance_note="Direct match for your primary target goal: 'Generative AI Internship'. Outreach Agent recommends personalized connection with verified GitHub portfolio.",
        )
        post3 = NetworkPost(
            id="b0000000-0000-0000-0000-000000000003",
            author_id=p3.id,
            author_name=p3.full_name,
            author_headline=p3.headline,
            author_avatar=p3.avatar_url,
            content=(
                "Just deployed our distributed embedding index using pgvector with HNSW indexing on 10M+ tokens. "
                "Latency dropped by 68% compared to IVFFlat. If you are a student working with pgvector and FastAPI, "
                "drop your repo link in the comments—we love hiring hands-on builders."
            ),
            likes_count=89,
            comments_count=5,
            tags=["PostgreSQL", "pgvector", "FastAPI", "HighPerformance"],
            agent_relevance_note="Matches your verified FastAPI and pgvector tech stack. Personalization Agent can generate a high-signal comment highlighting your CareerOS vector benchmark.",
        )

        for po in [post1, post2, post3]:
            cls._posts[po.id] = po

        cls._initialized = True

    @classmethod
    async def get_profiles(cls) -> list[NetworkProfile]:
        cls._seed_defaults()
        return list(cls._profiles.values())

    @classmethod
    async def get_profile_by_id(cls, profile_id: str) -> NetworkProfile | None:
        cls._seed_defaults()
        return cls._profiles.get(profile_id)

    @classmethod
    async def get_feed_posts(cls) -> list[NetworkPost]:
        cls._seed_defaults()
        posts = list(cls._posts.values())
        posts.sort(key=lambda p: p.created_at, reverse=True)
        return posts

    @classmethod
    async def like_post(cls, post_id: str) -> NetworkPost | None:
        cls._seed_defaults()
        post = cls._posts.get(post_id)
        if not post:
            return None
        if post.liked_by_user:
            post.liked_by_user = False
            post.likes_count = max(0, post.likes_count - 1)
        else:
            post.liked_by_user = True
            post.likes_count += 1
        return post

    @classmethod
    async def create_post(cls, post: NetworkPost) -> NetworkPost:
        cls._seed_defaults()
        post_id = str(post.id) if post.id else str(uuid4())
        post.id = post_id
        cls._posts[post_id] = post
        return post

    @classmethod
    async def add_comment(cls, comment: NetworkComment) -> NetworkComment:
        cls._seed_defaults()
        cls._comments.append(comment)
        if comment.post_id in cls._posts:
            cls._posts[comment.post_id].comments_count += 1
        return comment

    @classmethod
    async def get_comments(cls, post_id: str) -> list[NetworkComment]:
        cls._seed_defaults()
        return [c for c in cls._comments if c.post_id == post_id]

    @classmethod
    async def create_connection(cls, conn: NetworkConnection) -> NetworkConnection:
        cls._seed_defaults()
        cls._connections[conn.target_profile_id] = conn
        if conn.target_profile_id in cls._profiles:
            cls._profiles[conn.target_profile_id].connection_status = conn.status
            conn.target_name = cls._profiles[conn.target_profile_id].full_name
            conn.target_headline = cls._profiles[conn.target_profile_id].headline
        return conn

    @classmethod
    async def get_connections(cls) -> list[NetworkConnection]:
        cls._seed_defaults()
        return list(cls._connections.values())

    @classmethod
    async def send_message(cls, msg: NetworkMessage) -> NetworkMessage:
        cls._seed_defaults()
        if msg.receiver_id in cls._profiles:
            msg.receiver_name = cls._profiles[msg.receiver_id].full_name
        cls._messages.append(msg)
        return msg

    @classmethod
    async def get_messages_thread(cls, target_profile_id: str) -> list[NetworkMessage]:
        cls._seed_defaults()
        return [
            m for m in cls._messages
            if m.receiver_id == target_profile_id or m.sender_id == target_profile_id
        ]

    @classmethod
    async def get_all_messages(cls) -> list[NetworkMessage]:
        cls._seed_defaults()
        return cls._messages

    @classmethod
    async def generate_agent_proposals(cls) -> list[AgentOutreachProposal]:
        """
        Synthesize evidence-grounded connection proposals for target profiles.
        """
        cls._seed_defaults()
        proposals = [
            AgentOutreachProposal(
                target_profile_id="a0000000-0000-0000-0000-000000000001",
                target_name="Sarah Chen",
                target_headline="Senior Machine Learning Engineer @ Anthropic",
                match_score=96,
                proposed_note=(
                    "Hi Sarah, loved your insight on evidence provenance in agentic systems. "
                    "In my CareerOS project, I implemented an 8-gate deterministic Decision Engine and LangGraph state machine "
                    "with zero-hallucination verification. Would love to connect and follow your work on agent alignment!"
                ),
                evidence_citations=[
                    "GitHub: bogavivek15/game_score (LangGraph orchestrator)",
                    "Verified Skill: Python 3.11 & Agentic Guardrails",
                ],
                gate_decision="NEEDS_APPROVAL",
                reasoning="High-relevance Anthropic engineer. Gate 7 requires student consent prior to cold connection.",
            ),
            AgentOutreachProposal(
                target_profile_id="a0000000-0000-0000-0000-000000000002",
                target_name="David Kim",
                target_headline="Staff Technical Recruiter @ Google DeepMind",
                match_score=92,
                proposed_note=(
                    "Hi David, I saw your post regarding DeepMind's 2025 AI Systems internships. "
                    "I have spent the past year building autonomous career orchestration pipelines with pgvector and FastAPI, "
                    "grounding claims directly against verified transcripts. I'd love to connect to discuss student opportunities!"
                ),
                evidence_citations=[
                    "DeepMind Internship Post Match",
                    "Authoritative Memory: Multi-Agent Systems & FastAPI",
                ],
                gate_decision="NEEDS_APPROVAL",
                reasoning="Active recruiter for candidate's top target company. Tailored note prepared with verified credentials.",
            ),
            AgentOutreachProposal(
                target_profile_id="a0000000-0000-0000-0000-000000000003",
                target_name="Elena Rostova",
                target_headline="Co-Founder & CTO @ NexusAI (YC W24)",
                match_score=88,
                proposed_note=(
                    "Hi Elena, saw your benchmark on pgvector HNSW reducing latency by 68%. "
                    "We observed similar gains implementing hybrid vector search for skill matching in CareerOS. "
                    "Excited by what you are building at NexusAI and would love to stay in touch!"
                ),
                evidence_citations=[
                    "NexusAI HNSW Benchmark Post",
                    "Verified Fact: PostgreSQL 15 & pgvector experience",
                ],
                gate_decision="NEEDS_APPROVAL",
                reasoning="Founder actively seeking hands-on backend and systems builders. High alignment with tech stack.",
            ),
        ]
        return proposals
