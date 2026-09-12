import re

# Canonical skill taxonomy with aliases
SKILL_TAXONOMY: dict[str, list[str]] = {
    "python": ["python", "python3", "py"],
    "typescript": ["typescript", "ts"],
    "javascript": ["javascript", "js", "ecmascript"],
    "react": ["react", "react.js", "reactjs", "react native"],
    "next.js": ["next.js", "nextjs", "next"],
    "node.js": ["node.js", "nodejs", "node"],
    "fastapi": ["fastapi", "fast-api"],
    "django": ["django", "django rest framework", "drf"],
    "flask": ["flask"],
    "postgresql": ["postgresql", "postgres", "psql"],
    "mongodb": ["mongodb", "mongo"],
    "redis": ["redis"],
    "docker": ["docker", "containerization", "containers"],
    "kubernetes": ["kubernetes", "k8s"],
    "aws": ["aws", "amazon web services", "ec2", "s3", "lambda"],
    "gcp": ["gcp", "google cloud", "google cloud platform"],
    "azure": ["azure", "microsoft azure"],
    "graphql": ["graphql", "gql"],
    "rest": ["rest", "restful", "rest api"],
    "git": ["git", "github", "gitlab"],
    "ci/cd": ["ci/cd", "continuous integration", "github actions"],
    "linux": ["linux", "unix", "bash"],
    "tailwind": ["tailwind", "tailwindcss"],
    "css": ["css", "css3", "sass", "scss"],
    "html": ["html", "html5"],
    "sql": ["sql", "rdbms"],
    "langchain": ["langchain"],
    "llamaindex": ["llamaindex", "llama-index"],
    "ollama": ["ollama"],
    "huggingface": ["huggingface", "transformers"],
    "pytorch": ["pytorch", "torch"],
    "tensorflow": ["tensorflow", "tf", "keras"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "scikit-learn": ["scikit-learn", "sklearn"],
    "spark": ["spark", "pyspark", "apache spark"],
    "kafka": ["kafka", "apache kafka"],
    "go": ["golang", "go language"],
    "rust": ["rust", "rustlang"],
    "java": ["java", "spring", "spring boot"],
    "c++": ["c++", "cpp"],
}

# Inverted mapping for fast lookup: alias -> canonical
SKILL_ALIAS_MAP: dict[str, str] = {}
for canonical, aliases in SKILL_TAXONOMY.items():
    SKILL_ALIAS_MAP[canonical] = canonical
    for alias in aliases:
        SKILL_ALIAS_MAP[alias.lower()] = canonical

# Regex for experience matching (e.g., "3+ years", "3-5 years of experience", "minimum 5 years")
EXPERIENCE_RE = re.compile(
    r"\b(?:(?:minimum|at least)\s+)?(\d{1,2})(?:\s*[-–to]\s*\d{1,2})?\+?\s*years?(?:\s+of\s+experience)?\b",
    re.IGNORECASE,
)

# Section boundary patterns
PREFERRED_SECTION_RE = re.compile(
    r"\b(nice to have|preferred|bonus|plus|good to have|desired|optional)\b",
    re.IGNORECASE,
)
REQUIRED_SECTION_RE = re.compile(
    r"\b(requirements|qualifications|must have|what you(?:\'ll)? bring|who you are|skills required)\b",
    re.IGNORECASE,
)


def extract_skills_from_text(text: str) -> list[str]:
    """
    Extract canonical skills from text using boundary-checked regex patterns.
    """
    if not text:
        return []

    found_skills: set[str] = set()
    text_lower = f" {text.lower()} "

    for alias, canonical in SKILL_ALIAS_MAP.items():
        # Match whole word or exact bounded phrase (handling dots for node.js / next.js)
        if "." in alias:
            pattern = r"(?<![a-zA-Z0-9_\-])" + re.escape(alias) + r"(?![a-zA-Z0-9_\-])"
        elif alias == "c++":
            pattern = r"(?<![a-zA-Z0-9_\-])c\+\+(?![a-zA-Z0-9_\-])"
        else:
            pattern = r"\b" + re.escape(alias) + r"\b"

        if re.search(pattern, text_lower):
            found_skills.add(canonical)

    return sorted(found_skills)


def extract_requirements(description: str) -> tuple[list[str], list[str], float | None]:
    """
    Split description into required vs. preferred sections, then extract:
    Returns: (required_skills, preferred_skills, experience_min)
    """
    if not description:
        return [], [], None

    # 1. Experience extraction
    experience_min: float | None = None
    exp_matches = EXPERIENCE_RE.findall(description)
    if exp_matches:
        try:
            years = [float(m) for m in exp_matches if 0 < float(m) <= 20]
            if years:
                experience_min = min(years)
        except Exception:
            pass

    # 2. Section separation
    lines = description.split("\n")
    required_text_parts: list[str] = []
    preferred_text_parts: list[str] = []
    current_mode = "required"  # default context

    for line in lines:
        line_clean = line.strip()
        if not line_clean:
            continue

        if PREFERRED_SECTION_RE.search(line_clean):
            current_mode = "preferred"
            continue
        elif REQUIRED_SECTION_RE.search(line_clean):
            current_mode = "required"
            continue

        if current_mode == "preferred":
            preferred_text_parts.append(line_clean)
        else:
            required_text_parts.append(line_clean)

    required_skills = extract_skills_from_text(" ".join(required_text_parts))
    preferred_skills = extract_skills_from_text(" ".join(preferred_text_parts))

    # Remove duplicates from preferred if already in required
    preferred_skills = [s for s in preferred_skills if s not in required_skills]

    # If no section headings found and required is empty, extract from full description as required
    if not required_skills and not preferred_skills:
        required_skills = extract_skills_from_text(description)

    return required_skills, preferred_skills, experience_min
