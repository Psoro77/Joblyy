import logging

from app.services import database

logger = logging.getLogger(__name__)


GET_JOBS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_jobs",
        "description": (
            "Retrieve the user's saved jobs from the database. Use this when "
            "the user asks what jobs they have, which jobs are saved, or "
            "requests a list of jobs by status."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["found", "saved", "applied", "rejected", "interview"],
                    "description": "Filter by status",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results, default 10",
                },
            },
        },
    },
}


GET_APPLICATION_STATUS_SCHEMA = {
    "type": "function",
    "function": {
        "name": "get_application_status",
        "description": (
            "Check the status of the user's job applications. Omit job_id to "
            "get a summary of all recent applications, or pass a specific "
            "job_id for details on one."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "job_id": {
                    "type": "integer",
                    "description": "Specific job ID, or omit for all recent applications",
                },
            },
        },
    },
}


async def get_jobs(status: str | None = None, limit: int = 10) -> str:
    try:
        rows = await database.get_jobs(status=status, limit=limit)
        if not rows:
            if status:
                return f"No jobs found with status '{status}'."
            return "No jobs found."

        lines = [
            f"- {r.get('title', '?')} — {r.get('company', '?')} [{r.get('status', '?')}]"
            for r in rows
        ]
        header = f"{len(rows)} job(s):"
        return header + "\n" + "\n".join(lines)

    except Exception as exc:
        logger.exception("get_jobs tool failed")
        return f"Error in get_jobs: {exc}"


async def get_application_status(job_id: int | None = None) -> str:
    try:
        rows = await database.get_applications(job_id=job_id)
        if not rows:
            if job_id is not None:
                return f"No application found for job_id={job_id}."
            return "No applications yet."

        lines = []
        for r in rows:
            title = r.get("title", "?")
            company = r.get("company", "?")
            app_status = r.get("status", "?")
            applied_at = r.get("applied_at", "?")
            method = r.get("method", "?")
            lines.append(
                f"- {title} @ {company}: {app_status} (via {method}, {applied_at})"
            )
        header = f"{len(rows)} application(s):"
        return header + "\n" + "\n".join(lines)

    except Exception as exc:
        logger.exception("get_application_status tool failed")
        return f"Error in get_application_status: {exc}"


JOB_TOOLS: dict[str, dict] = {
    "get_jobs": {
        "schema": GET_JOBS_SCHEMA,
        "fn": get_jobs,
    },
    "get_application_status": {
        "schema": GET_APPLICATION_STATUS_SCHEMA,
        "fn": get_application_status,
    },
}
