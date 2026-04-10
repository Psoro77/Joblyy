import logging
import re

from app.services import database, memory
from app.services.llm import chat_completion

logger = logging.getLogger(__name__)

USER_ID = 1


PARSE_AND_SAVE_PROFILE_SCHEMA = {
    "type": "function",
    "function": {
        "name": "parse_and_save_profile",
        "description": (
            "Parse raw CV/resume text pasted by the user, extract structured "
            "information, and save it to the profile memory. Use this whenever "
            "the user shares their CV, resume, or a block of professional "
            "experience to be saved."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "raw_text": {
                    "type": "string",
                    "description": "The raw CV or experience text from the user",
                },
            },
            "required": ["raw_text"],
        },
    },
}


UPDATE_PREFERENCES_SCHEMA = {
    "type": "function",
    "function": {
        "name": "update_preferences",
        "description": (
            "Update the user's job search preferences from a natural-language "
            "description. Use this when the user says what kind of jobs, "
            "locations, salary, or work type they want."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Natural language description of what the user is looking for",
                },
            },
            "required": ["description"],
        },
    },
}


_PROFILE_EXTRACTION_PROMPT = """\
You extract structured professional information from raw CV/resume text.
Return ONLY a markdown document with EXACTLY these sections, in this order:

# Profile

## Name
<full name, or "(not set)">

## Skills
<comma-separated list of skills, or "(not set)">

## Experience
<bullet list of roles: "- Title at Company (dates) — short description", or "(not set)">

## Education
<bullet list: "- Degree, Institution (year)", or "(not set)">

## Languages
<comma-separated list, or "(not set)">

## Summary
<2-3 sentence professional summary, or "(not set)">

Be thorough but concise. Do not invent data. Do not add extra sections or commentary.
"""


_PREFERENCES_MERGE_PROMPT = """\
You maintain a user's job search preferences as a markdown document.
Merge the new information into the existing preferences below. Keep any
existing values that are not contradicted by the new description.

Return ONLY a markdown document with EXACTLY these sections, in this order:

# Job Preferences

## Target roles
<comma-separated list, or "(not set)">

## Locations
<comma-separated list, or "(not set)">

## Salary expectations
<short description, or "(not set)">

## Work type
<remote/hybrid/onsite, or "(not set)">

## Industries
<comma-separated list, or "(not set)">

## Dealbreakers
<bullet list, or "(not set)">

Do not add extra sections or commentary.
"""


def _extract_name(profile_md: str) -> str | None:
    match = re.search(r"##\s*Name\s*\n+([^\n]+)", profile_md)
    if not match:
        return None
    name = match.group(1).strip()
    if not name or name == "(not set)":
        return None
    return name


def _filled_sections(profile_md: str) -> list[str]:
    filled = []
    for section in ("Name", "Skills", "Experience", "Education", "Languages", "Summary"):
        pattern = rf"##\s*{section}\s*\n+([^\n]+)"
        match = re.search(pattern, profile_md)
        if match and match.group(1).strip() not in ("", "(not set)"):
            filled.append(section)
    return filled


async def parse_and_save_profile(raw_text: str) -> str:
    try:
        if not raw_text or not raw_text.strip():
            return "Error in parse_and_save_profile: raw_text is empty."

        messages = [
            {"role": "system", "content": _PROFILE_EXTRACTION_PROMPT},
            {"role": "user", "content": raw_text},
        ]
        response = await chat_completion(messages)
        profile_md = (response.get("content") or "").strip()

        if not profile_md or profile_md.startswith("Error:") or profile_md.startswith("LLM error:"):
            return f"Error in parse_and_save_profile: extraction failed ({profile_md[:120]})"

        memory.write_markdown(USER_ID, "profile.md", profile_md)

        name = _extract_name(profile_md)
        if name:
            try:
                await database.upsert_user_name(name)
            except Exception as exc:
                logger.warning("upsert_user_name failed: %s", exc)

        filled = _filled_sections(profile_md)
        summary = ", ".join(filled) if filled else "no sections filled"
        return f"Profile saved. Understood: {summary}."

    except Exception as exc:
        logger.exception("parse_and_save_profile failed")
        return f"Error in parse_and_save_profile: {exc}"


async def update_preferences(description: str) -> str:
    try:
        if not description or not description.strip():
            return "Error in update_preferences: description is empty."

        current = memory.read_markdown(USER_ID, "preferences.md")

        user_content = (
            f"Existing preferences:\n\n{current}\n\n"
            f"New information from user:\n\n{description}"
        )
        messages = [
            {"role": "system", "content": _PREFERENCES_MERGE_PROMPT},
            {"role": "user", "content": user_content},
        ]
        response = await chat_completion(messages)
        prefs_md = (response.get("content") or "").strip()

        if not prefs_md or prefs_md.startswith("Error:") or prefs_md.startswith("LLM error:"):
            return f"Error in update_preferences: merge failed ({prefs_md[:120]})"

        memory.write_markdown(USER_ID, "preferences.md", prefs_md)
        return "Preferences updated."

    except Exception as exc:
        logger.exception("update_preferences failed")
        return f"Error in update_preferences: {exc}"


MEMORY_TOOLS: dict[str, dict] = {
    "parse_and_save_profile": {
        "schema": PARSE_AND_SAVE_PROFILE_SCHEMA,
        "fn": parse_and_save_profile,
    },
    "update_preferences": {
        "schema": UPDATE_PREFERENCES_SCHEMA,
        "fn": update_preferences,
    },
}
