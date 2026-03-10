# SuperRecruit SDK

Data contracts and plugin interfaces for building [SuperRecruit](https://github.com/insomniak68/superrecruit-desktop) integrations.

## Install

```bash
pip install superrecruit-sdk
```

Or from source:

```bash
pip install git+https://github.com/insomniak68/superrecruit-sdk.git
```

## What's in the box

**Zero dependencies.** Pure Python 3.10+ stdlib — dataclasses, protocols, enums.

| Type | Purpose |
|---|---|
| `SourcePlugin` | Protocol for importing jobs, candidates, and skills into SR |
| `SinkPlugin` | Protocol for exporting screening decisions from SR |
| `JobImport` | Job/position data model |
| `CandidateImport` | Candidate data model (with resume support) |
| `SkillDefinition` | Skill/competency data model |
| `ScreeningDecision` | Screening result with fit score, rationale, skill analysis |
| `DecisionDetail` | Per-aspect scoring breakdown |
| `PluginInfo` | Plugin metadata (name, version, capabilities) |

## Quick Start

```python
from superrecruit import SourcePlugin, PluginInfo, JobImport, SkillDefinition

class Plugin:
    def info(self):
        return PluginInfo(
            name="myats",
            display_name="My ATS",
            version="1.0.0",
            capabilities=["source:jobs", "source:candidates"],
        )

    def configure(self, config):
        self.api_key = config["api_key"]

    def test_connection(self):
        return {"ok": True, "message": "Connected"}

    def fetch_jobs(self, **filters):
        return [JobImport(title="Engineer", required_skills=[SkillDefinition(name="Python")])]

    def fetch_candidates(self, job_id="", **filters):
        return []

    def fetch_skills(self):
        return []
```

See [docs/PLUGIN_SPEC.md](docs/PLUGIN_SPEC.md) for the full reference, including sink plugins, data models, and registration methods.

## Example Plugins

Check out [superrecruit-plugins](https://github.com/insomniak68/superrecruit-plugins) for reference implementations:

- **CSV** — Import jobs/candidates from CSV files
- **Webhook** — POST screening decisions to any URL

## License

MIT — build whatever you want.
