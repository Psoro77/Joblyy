from typing import Dict, List
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MEMORY_DIR = Path("app/memory")

VALID_FILES = {"profile.md", "preferences.md", "session.md"}

PROFILE_TEMPLATE = """\
# Profile

## Name
(not set)

## Skills
(not set)

## Experience
(not set)

## Education
(not set)

## Languages
(not set)

## Summary
(not set)
"""

PREFERENCES_TEMPLATE = """\
# Job Preferences

## Target roles
(not set)

## Locations
(not set)

## Salary expectations
(not set)

## Work type
(not set)

## Industries
(not set)

## Dealbreakers
(not set)
"""

_TEMPLATES: Dict[str, str] = {
    "profile.md": PROFILE_TEMPLATE,
    "preferences.md": PREFERENCES_TEMPLATE,
    "session.md": "",
}

MAX_CONTEXT_TOKENS = 3000
SUMMARY_TOKEN_LIMIT = 200


def _token_estimate(text: str) -> int:
    return int(len(text.split()) * 1.3)


def _user_dir(user_id: int) -> Path:
    return MEMORY_DIR / str(user_id)


def _validate_file(file: str) -> None:
    if file not in VALID_FILES:
        raise ValueError(f"Invalid memory file: {file!r}. Must be one of {VALID_FILES}")


# ── File management ──

def init_user_memory(user_id: int) -> None:
    user_path = _user_dir(user_id)
    user_path.mkdir(parents=True, exist_ok=True)

    for filename, template in _TEMPLATES.items():
        filepath = user_path / filename
        if not filepath.exists():
            filepath.write_text(template, encoding="utf-8")

    logger.info("Initialized memory directory for user %d", user_id)


def read_markdown(user_id: int, file: str) -> str:
    _validate_file(file)
    filepath = _user_dir(user_id) / file
    if not filepath.exists():
        return ""
    return filepath.read_text(encoding="utf-8")


def write_markdown(user_id: int, file: str, content: str) -> None:
    _validate_file(file)
    user_path = _user_dir(user_id)
    user_path.mkdir(parents=True, exist_ok=True)
    (user_path / file).write_text(content, encoding="utf-8")


def append_markdown(user_id: int, file: str, content: str) -> None:
    _validate_file(file)
    user_path = _user_dir(user_id)
    user_path.mkdir(parents=True, exist_ok=True)
    filepath = user_path / file
    with filepath.open("a", encoding="utf-8") as f:
        f.write(content)


# ── Context builder ──

def _truncate_to_tokens(text: str, max_tokens: int) -> str:
    words = text.split()
    target_words = int(max_tokens / 1.3)
    if len(words) <= target_words:
        return text
    return " ".join(words[:target_words]) + "\n...(truncated)"


def _profile_summary(user_id: int) -> str:
    full = read_markdown(user_id, "profile.md")
    if not full:
        return ""
    return _truncate_to_tokens(full, SUMMARY_TOKEN_LIMIT)


def build_context(user_id: int, intent: str, **kwargs: str) -> str:
    """Assemble system-prompt context based on intent.

    Supported intents: general, profile_edit, preferences_edit,
    job_search, apply, status_check.

    Keyword args:
        job_details: job description string, used with intent="apply".
    """
    try:
        parts: List[str] = []

        if intent == "general":
            summary = _profile_summary(user_id)
            if summary:
                parts.append(f"## Profile (summary)\n{summary}")

        elif intent == "profile_edit":
            full_profile = read_markdown(user_id, "profile.md")
            if full_profile:
                parts.append(f"## Profile\n{full_profile}")

        elif intent == "preferences_edit":
            prefs = read_markdown(user_id, "preferences.md")
            if prefs:
                parts.append(f"## Preferences\n{prefs}")

        elif intent == "job_search":
            summary = _profile_summary(user_id)
            if summary:
                parts.append(f"## Profile (summary)\n{summary}")
            prefs = read_markdown(user_id, "preferences.md")
            if prefs:
                parts.append(f"## Preferences\n{prefs}")

        elif intent == "apply":
            full_profile = read_markdown(user_id, "profile.md")
            if full_profile:
                parts.append(f"## Profile\n{full_profile}")
            prefs = read_markdown(user_id, "preferences.md")
            if prefs:
                parts.append(f"## Preferences\n{prefs}")
            job_details = kwargs.get("job_details", "")
            if job_details:
                parts.append(f"## Job Details\n{job_details}")

        elif intent == "status_check":
            pass

        else:
            logger.warning("Unknown intent %r, returning empty context", intent)

        context = "\n\n".join(parts)
        tokens = _token_estimate(context)

        if tokens > MAX_CONTEXT_TOKENS:
            logger.warning(
                "Context for user %d intent %r is ~%d tokens (limit %d)",
                user_id, intent, tokens, MAX_CONTEXT_TOKENS,
            )

        return context

    except Exception:
        logger.exception("build_context failed for user %d intent %r", user_id, intent)
        return ""
