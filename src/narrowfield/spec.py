"""Plugin specifications — the contracts that plugins implement.

These are the data models and interfaces that SR defines. Plugin authors
import these and implement SourcePlugin or SinkPlugin (or both).

All models use plain dicts/dataclasses with JSON-serializable fields
so plugins don't need pydantic or any SR-specific dependencies.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional, Protocol, runtime_checkable


# ── Error handling ──

class PluginError(Exception):
    """Base error for plugin operations."""
    pass


# ── Plugin identity ──

@dataclass
class PluginInfo:
    """Metadata about a plugin."""
    name: str                        # Unique identifier, e.g. "greenhouse", "lever"
    display_name: str                # Human-readable, e.g. "Greenhouse ATS"
    version: str                     # Semver
    description: str = ""
    author: str = ""
    url: str = ""                    # Documentation / homepage
    capabilities: list[str] = field(default_factory=list)  # ["source:jobs", "source:candidates", "sink:decisions"]


# ══════════════════════════════════════════════════════════════════
# INPUT SPEC — Data flowing INTO Narrowfield
# ══════════════════════════════════════════════════════════════════

@dataclass
class SkillDefinition:
    """A skill or competency from an external system."""
    name: str                        # Canonical name, e.g. "Python"
    category: str = ""               # e.g. "language", "framework", "soft_skill"
    aliases: list[str] = field(default_factory=list)  # Alternative names
    external_id: str = ""            # ID in the source system
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class JobImport:
    """A job/position from an external system."""
    title: str
    description: str = ""
    department: str = ""
    required_skills: list[SkillDefinition] = field(default_factory=list)
    preferred_skills: list[SkillDefinition] = field(default_factory=list)
    min_experience_years: int = 0
    location: str = ""
    employment_type: str = ""        # "full_time", "contract", "part_time"
    external_id: str = ""            # ID in the source system (e.g. Greenhouse job ID)
    external_url: str = ""           # Link back to the source
    raw: dict[str, Any] = field(default_factory=dict)  # Original payload for debugging
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CandidateImport:
    """A candidate from an external system."""
    name: str
    email: str
    phone: str = ""
    resume_text: str = ""            # Plain text resume content
    resume_url: str = ""             # URL to download resume
    resume_bytes: bytes = b""        # Raw resume file (PDF, DOCX)
    resume_filename: str = ""        # Original filename
    skills: list[SkillDefinition] = field(default_factory=list)  # Pre-parsed skills from ATS
    experience_years: int = 0
    current_title: str = ""
    current_company: str = ""
    source: str = ""                 # "applied", "referred", "sourced"
    external_id: str = ""            # ID in the source system
    external_url: str = ""
    applied_to: str = ""             # External job ID this candidate applied to
    raw: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════
# OUTPUT SPEC — Data flowing OUT of Narrowfield
# ══════════════════════════════════════════════════════════════════

class DecisionOutcome(str, Enum):
    """Possible screening outcomes."""
    ADVANCE = "advance"              # Move forward in the process
    REJECT = "reject"                # Do not advance
    HOLD = "hold"                    # Needs more information / review
    ASSESSMENT = "assessment"        # Send technical assessment


@dataclass
class DecisionDetail:
    """Detailed reasoning for a single aspect of the decision."""
    aspect: str                      # e.g. "skill_match", "experience", "equivalency"
    score: float = 0.0               # 0.0 - 1.0
    summary: str = ""                # Human-readable explanation
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ScreeningDecision:
    """The result of screening a candidate for a position.

    This is what SR produces and sink plugins consume.
    """
    candidate_email: str             # Candidate identifier
    candidate_name: str
    position_title: str              # Position this decision is for
    outcome: DecisionOutcome
    fit_score: float                 # 0.0 - 1.0
    fit_level: str                   # "strong", "moderate", "weak"
    rationale: str                   # Human-readable summary
    details: list[DecisionDetail] = field(default_factory=list)
    skills_matched: list[str] = field(default_factory=list)
    skills_missing: list[str] = field(default_factory=list)
    skills_equivalent: list[dict[str, str]] = field(default_factory=list)  # [{"required": "X", "matched": "Y", "weight": 0.9}]
    recommended_assessments: list[str] = field(default_factory=list)  # Test IDs to send
    decided_at: str = ""             # ISO 8601
    decided_by: str = "narrowfield" # "narrowfield" or screener name
    candidate_external_id: str = ""  # For mapping back to source system
    position_external_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════
# PLUGIN INTERFACES
# ══════════════════════════════════════════════════════════════════

@runtime_checkable
class SourcePlugin(Protocol):
    """Interface for plugins that import data into SR.

    Implement the methods relevant to your integration.
    Return empty lists for capabilities you don't support.
    """

    def info(self) -> PluginInfo:
        """Return plugin metadata."""
        ...

    def configure(self, config: dict[str, Any]) -> None:
        """Initialize with plugin-specific config (API keys, URLs, etc.)."""
        ...

    def test_connection(self) -> dict[str, Any]:
        """Verify the connection to the external system.

        Returns: {"ok": bool, "message": str}
        """
        ...

    def fetch_jobs(self, **filters) -> list[JobImport]:
        """Fetch jobs/positions from the external system.

        Optional filters (plugin-specific): status, department, updated_since, etc.
        """
        ...

    def fetch_candidates(self, job_id: str = "", **filters) -> list[CandidateImport]:
        """Fetch candidates, optionally filtered by job.

        Optional filters: status, updated_since, etc.
        """
        ...

    def fetch_skills(self) -> list[SkillDefinition]:
        """Fetch the skill taxonomy from the external system."""
        ...


@runtime_checkable
class SinkPlugin(Protocol):
    """Interface for plugins that export decisions from SR.

    Implement the methods relevant to your integration.
    """

    def info(self) -> PluginInfo:
        """Return plugin metadata."""
        ...

    def configure(self, config: dict[str, Any]) -> None:
        """Initialize with plugin-specific config."""
        ...

    def test_connection(self) -> dict[str, Any]:
        """Verify the connection to the external system."""
        ...

    def send_decision(self, decision: ScreeningDecision) -> dict[str, Any]:
        """Send a single screening decision to the external system.

        Returns: {"ok": bool, "message": str, "external_id": str}
        """
        ...

    def send_decisions(self, decisions: list[ScreeningDecision]) -> dict[str, Any]:
        """Send multiple decisions in batch.

        Returns: {"ok": bool, "message": str, "sent": int, "failed": int}
        """
        ...
