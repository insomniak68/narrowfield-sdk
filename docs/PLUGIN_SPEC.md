# SuperRecruit Plugin Spec

Plugins connect SuperRecruit to external systems without coupling SR to any vendor. SR defines the data contracts; plugins implement adapters.

## Architecture

```
External Systems                SuperRecruit                    External Systems
┌──────────────┐               ┌──────────────┐               ┌──────────────┐
│ Greenhouse   │──┐            │              │            ┌──│ Slack        │
│ Lever        │──┤  Source    │   Plugin     │   Sink     ├──│ Email        │
│ Workday      │──├──Plugins──▶│   Registry   │──Plugins──▶├──│ ATS          │
│ CSV/JSON     │──┤            │              │            ├──│ Webhook      │
│ Job Boards   │──┘            └──────────────┘            └──│ HRIS         │
└──────────────┘                                              └──────────────┘
```

## Two Plugin Types

### Source Plugins — Import data INTO SR

| Method | What it imports |
|---|---|
| `fetch_jobs()` | Positions with titles, descriptions, required/preferred skills |
| `fetch_candidates()` | Candidates with resumes, contact info, pre-parsed skills |
| `fetch_skills()` | Skill taxonomy / competency framework |

### Sink Plugins — Export decisions OUT of SR

| Method | What it exports |
|---|---|
| `send_decision()` | Single screening result with fit score, rationale, matched/missing skills |
| `send_decisions()` | Batch of screening results |

## Data Models

### Input: `JobImport`

```python
@dataclass
class JobImport:
    title: str
    description: str = ""
    department: str = ""
    required_skills: list[SkillDefinition] = []
    preferred_skills: list[SkillDefinition] = []
    min_experience_years: int = 0
    location: str = ""
    employment_type: str = ""        # "full_time", "contract", "part_time"
    external_id: str = ""            # ID in your system
    external_url: str = ""           # Link back
    raw: dict = {}                   # Original payload
    metadata: dict = {}
```

### Input: `CandidateImport`

```python
@dataclass
class CandidateImport:
    name: str
    email: str
    phone: str = ""
    resume_text: str = ""            # Plain text
    resume_url: str = ""             # URL to download
    resume_bytes: bytes = b""        # Raw file (PDF/DOCX)
    resume_filename: str = ""
    skills: list[SkillDefinition] = []  # Pre-parsed from ATS
    experience_years: int = 0
    current_title: str = ""
    current_company: str = ""
    source: str = ""                 # "applied", "referred", "sourced"
    external_id: str = ""
    external_url: str = ""
    applied_to: str = ""             # External job ID
    raw: dict = {}
    metadata: dict = {}
```

### Input: `SkillDefinition`

```python
@dataclass
class SkillDefinition:
    name: str                        # "Python"
    category: str = ""               # "language", "framework", "soft_skill"
    aliases: list[str] = []          # ["Python3", "CPython"]
    external_id: str = ""
    metadata: dict = {}
```

### Output: `ScreeningDecision`

```python
@dataclass
class ScreeningDecision:
    candidate_email: str
    candidate_name: str
    position_title: str
    outcome: DecisionOutcome         # "advance", "reject", "hold", "assessment"
    fit_score: float                 # 0.0 - 1.0
    fit_level: str                   # "strong", "moderate", "weak"
    rationale: str                   # Human-readable summary
    details: list[DecisionDetail]    # Per-aspect breakdowns
    skills_matched: list[str]
    skills_missing: list[str]
    skills_equivalent: list[dict]    # [{"required": "X", "matched": "Y", "weight": 0.9}]
    recommended_assessments: list[str]
    decided_at: str                  # ISO 8601
    decided_by: str                  # "superrecruit" or screener name
    candidate_external_id: str = ""  # For mapping back
    position_external_id: str = ""
    metadata: dict = {}
```

### Output: `DecisionDetail`

```python
@dataclass
class DecisionDetail:
    aspect: str                      # "skill_match", "experience", "equivalency"
    score: float                     # 0.0 - 1.0
    summary: str
    details: dict = {}
```

## Writing a Plugin

### Minimal Source Plugin

```python
# sr_myats/__init__.py

from superrecruit import SourcePlugin, PluginInfo, JobImport, CandidateImport, SkillDefinition

class Plugin:
    """My ATS integration."""

    def info(self):
        return PluginInfo(
            name="myats",
            display_name="My ATS",
            version="1.0.0",
            capabilities=["source:jobs", "source:candidates"],
        )

    def configure(self, config):
        self.api_key = config.get("api_key", "")
        self.base_url = config.get("base_url", "https://api.myats.com")

    def test_connection(self):
        # Verify API access
        import httpx
        resp = httpx.get(f"{self.base_url}/ping", headers={"Authorization": f"Bearer {self.api_key}"})
        if resp.status_code == 200:
            return {"ok": True, "message": "Connected to My ATS"}
        return {"ok": False, "message": f"HTTP {resp.status_code}"}

    def fetch_jobs(self, **filters):
        import httpx
        resp = httpx.get(f"{self.base_url}/jobs", headers={"Authorization": f"Bearer {self.api_key}"})
        jobs = []
        for j in resp.json()["jobs"]:
            jobs.append(JobImport(
                title=j["title"],
                description=j["description"],
                external_id=str(j["id"]),
                required_skills=[SkillDefinition(name=s) for s in j.get("skills", [])],
            ))
        return jobs

    def fetch_candidates(self, job_id="", **filters):
        # Similar pattern — call API, return CandidateImport list
        return []

    def fetch_skills(self):
        return []
```

### Minimal Sink Plugin

```python
# sr_webhook/__init__.py

from superrecruit import SinkPlugin, PluginInfo, ScreeningDecision
import dataclasses, json

class Plugin:
    def info(self):
        return PluginInfo(
            name="webhook",
            display_name="Webhook",
            version="1.0.0",
            capabilities=["sink:decisions"],
        )

    def configure(self, config):
        self.url = config["url"]
        self.auth = config.get("auth_header", "")

    def test_connection(self):
        import httpx
        try:
            resp = httpx.get(self.url, headers={"Authorization": self.auth}, timeout=5)
            return {"ok": resp.status_code < 400, "message": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"ok": False, "message": str(e)}

    def send_decision(self, decision):
        import httpx
        payload = dataclasses.asdict(decision)
        resp = httpx.post(self.url, json=payload, headers={"Authorization": self.auth})
        return {"ok": resp.status_code < 300, "message": f"HTTP {resp.status_code}"}

    def send_decisions(self, decisions):
        results = [self.send_decision(d) for d in decisions]
        sent = sum(1 for r in results if r["ok"])
        return {"ok": sent == len(results), "sent": sent, "failed": len(results) - sent}
```

## Registration

### Via config/plugins.yaml

```yaml
plugins:
  - name: myats
    module: sr_myats           # pip-installable or local module
    enabled: true
    config:
      api_key: ${MY_ATS_API_KEY}
      base_url: https://api.myats.com
```

### Via plugins/ directory (auto-discovery)

Place plugin packages in `plugins/`:

```
superrecruit-desktop/
├── plugins/
│   ├── myats/
│   │   ├── __init__.py        # Contains Plugin class
│   │   └── ...
│   └── webhook/
│       └── __init__.py
```

### Programmatic

```python
from superrecruit.plugins import get_registry  # From the SR app, not the SDK

registry = get_registry()
registry.register_source(MyPlugin(), config={"api_key": "..."})
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/plugins` | List registered plugins |
| POST | `/api/plugins/{name}/test` | Test a plugin's connection |
| POST | `/api/plugins/{name}/sync/jobs` | Import jobs from a source plugin |
| POST | `/api/plugins/{name}/sync/candidates` | Import candidates from a source plugin |
| POST | `/api/plugins/{name}/sync/skills` | Import skills from a source plugin |
| POST | `/api/plugins/{name}/send-decision` | Send a decision via a sink plugin |

## Design Principles

1. **SR owns the spec, plugins own the adapters.** SR never imports vendor-specific code.
2. **Plugins are separate packages.** Install via pip, drop in plugins/, or configure in YAML.
3. **All data passes through SR's models.** Plugins translate between external formats and SR's contracts.
4. **External IDs preserved.** Every import carries `external_id` for round-trip mapping.
5. **Raw payloads stored.** The `raw` field on imports preserves the original data for debugging.
6. **Fail gracefully.** Plugin errors don't crash SR. All operations return status dicts.
