# Joblyy

**Joblyy** is an AI-powered job search and application automation system. It uses intelligent agents to understand your profile and preferences, search for matching opportunities, and handle applications automatically.

---

## Features

- **Conversational AI** — Natural language interface designed with a specialized agent for user interaction and memory management
- **Automated job search** — Browser automation agent that searches job portals based on your criteria
- **Profile management** — Parse and store your CV, skills, and experience via Markdown for LLM context
- **Preference tracking** — Define job criteria, locations, salary expectations, and other preferences
- **Application automation** — Automatically fill out and submit job applications with your profile data
- **Session memory** — Maintains conversation context and tracks application history

---

## Architecture

### Two-Agent System

**Conversational Agent**
- Communicates directly with the user via natural language
- Manages context and memory using tool calling via Ollama API
- Delegates browser tasks to the Browser Agent
- No frameworks around the LLM: raw API calls with JSON schema tool definitions

**Browser Agent**
- Receives structured JSON instructions (not natural language)
- Executes web actions via browser-use
- Returns compact summaries of results
- Stateless between tasks for robustness

**Orchestrator**
- Pure Python logic without LLM involvement
- Routes tasks between agents and memory module
- Manages SQLite database operations

### Memory System

- **SQLite database** — Structured data for users, jobs, applications, and conversations
- **Markdown files per user** — Human-readable context files:
  - `memory/{user_id}/profile.md` — Parsed CV, skills, and experience
  - `memory/{user_id}/preferences.md` — Job criteria, locations, salary expectations
  - `memory/{user_id}/session.md` — Current conversation context (resets per session)
- **Intelligent context loading** — Only relevant memory loaded as context based on task intent (never exceeds ~3000 tokens)

---

## Tech Stack

- **Backend** — FastAPI
- **Frontend** — Vanilla HTML/JavaScript with streaming responses (SSE)
- **Database** — SQLite
- **LLM** — Ollama with Gemma 4 (primary) or LiteLLM for cloud fallback
- **Browser Automation** — browser-use
- **No frameworks** — Direct LLM API calls, minimal abstraction layers

---

## Project Structure

```
app/
├── main.py                          # FastAPI application entry point
├── config.py                        # Configuration settings
├── routers/
│   ├── chat.py                      # Conversation endpoints (SSE)
│   ├── jobs.py                      # Job CRUD operations
│   ├── profile.py                   # Profile viewing and editing
│   └── settings.py                  # Settings and preferences
├── agents/
│   ├── conversational.py            # Main conversational agent with tool calling
│   ├── browser_agent.py             # Browser automation agent (browser-use)
│   └── tools/
│       ├── memory_tools.py          # parse_profile, update_preferences, read_memory
│       ├── job_tools.py             # get_jobs, save_job, get_application_status
│       └── browser_tools.py         # delegate_to_browser
├── services/
│   ├── llm.py                       # Ollama + LiteLLM wrapper
│   ├── memory.py                    # Markdown read/write and context builder
│   └── database.py                  # SQLite operations
├── models/
│   └── schemas.py                   # Pydantic models
└── memory/                          # Per-user memory files

frontend/
└── index.html                       # Simple chat interface
```

---

## Conversational Agent Tools

### parse_and_save_profile
- Extracts structured information from raw CV text
- Writes parsed data to `profile.md` and SQLite
- Returns confirmation and summary

### update_preferences
- Accepts natural language job preferences
- Updates `preferences.md`
- Confirms updated criteria

### read_memory
- Loads relevant context by intent category (profile, preferences, jobs, applications)
- Returns formatted context string for LLM

### delegate_to_browser
- Sends structured JSON instructions to Browser Agent
- Task types: search, apply, scrape
- Returns compact summary of results

### get_jobs
- Queries SQLite jobs table with optional filters
- Returns formatted job list

### get_application_status
- Queries application status and history
- Optional job_id filter

---

## Database Schema

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE jobs (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    title TEXT,
    company TEXT,
    url TEXT UNIQUE,
    description TEXT,
    source TEXT,
    match_score REAL,
    status TEXT DEFAULT 'found',  -- found, saved, applied, rejected, interview
    found_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE applications (
    id INTEGER PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    user_id INTEGER REFERENCES users(id),
    applied_at TIMESTAMP,
    method TEXT,  -- auto, manual
    status TEXT DEFAULT 'submitted',
    notes TEXT
);

CREATE TABLE conversations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    role TEXT,  -- user, assistant
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Getting Started

### Requirements

- Python 3.9+
- Ollama with Gemma 4 (or LiteLLM configured for cloud API)
- SQLite3

### Installation

```bash
# Clone the repository
git clone https://github.com/Psoro77/Joblyy.git
cd Joblyy

# Create and activate virtual environment
python3 -m venv env
source env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. Set your Ollama endpoint (default: http://localhost:11434) or provide a cloud API key
2. Optionally set environment variables in `.env` for API configuration

### Running the Application

```bash
# Start the FastAPI server
uvicorn app.main:app --reload
```

The application will be available at `http://localhost:8000`

---

## Implementation Checklist

- [x] FastAPI skeleton + SQLite setup
- [ ] Conversational agent with parse_and_save_profile and read_memory tools
- [ ] update_preferences and get_jobs tools
- [ ] Frontend chat interface with SSE streaming
- [ ] Browser agent integration with search
- [ ] Application workflow (form filling, submission, tracking)
- [ ] Dashboard and session management

---

## Design Principles

- **Simplicity first** — No over-engineering; direct API calls preferred
- **Tool-driven** — Every agent capability expressed as discrete, testable tools
- **Agent isolation** — Browser agent failure does not break conversational agent
- **Human-readable memory** — All Markdown files editable manually as fallback
- **Context efficiency** — Never exceed ~3000 tokens for memory context per request

---

## Contributing

Contributions, ideas, and feedback are welcome. Feel free to open an issue or submit a pull request.

---

## License

This project is licensed under the [MIT License](LICENSE).
