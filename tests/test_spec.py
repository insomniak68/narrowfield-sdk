"""Basic tests for SDK data models and protocols."""

from superrecruit import (
    JobImport,
    CandidateImport,
    SkillDefinition,
    ScreeningDecision,
    DecisionDetail,
    DecisionOutcome,
    PluginInfo,
    PluginError,
    SourcePlugin,
    SinkPlugin,
)


def test_job_import_defaults():
    job = JobImport(title="Engineer")
    assert job.title == "Engineer"
    assert job.required_skills == []
    assert job.metadata == {}


def test_candidate_import():
    c = CandidateImport(name="Alice", email="alice@example.com", resume_text="Python dev")
    assert c.name == "Alice"
    assert c.resume_bytes == b""


def test_screening_decision():
    d = ScreeningDecision(
        candidate_email="alice@example.com",
        candidate_name="Alice",
        position_title="Engineer",
        outcome=DecisionOutcome.ADVANCE,
        fit_score=0.85,
        fit_level="strong",
        rationale="Strong Python match",
    )
    assert d.outcome == DecisionOutcome.ADVANCE
    assert d.fit_score == 0.85


def test_decision_detail():
    detail = DecisionDetail(aspect="skill_match", score=0.9, summary="Good")
    assert detail.aspect == "skill_match"


def test_plugin_info():
    info = PluginInfo(name="test", display_name="Test Plugin", version="1.0.0")
    assert info.capabilities == []


def test_plugin_error():
    try:
        raise PluginError("test error")
    except PluginError as e:
        assert str(e) == "test error"


def test_source_protocol():
    """A class implementing all SourcePlugin methods satisfies the protocol."""

    class MySource:
        def info(self): return PluginInfo(name="x", display_name="X", version="0")
        def configure(self, config): pass
        def test_connection(self): return {"ok": True}
        def fetch_jobs(self, **f): return []
        def fetch_candidates(self, job_id="", **f): return []
        def fetch_skills(self): return []

    assert isinstance(MySource(), SourcePlugin)


def test_sink_protocol():
    class MySink:
        def info(self): return PluginInfo(name="x", display_name="X", version="0")
        def configure(self, config): pass
        def test_connection(self): return {"ok": True}
        def send_decision(self, d): return {"ok": True}
        def send_decisions(self, ds): return {"ok": True}

    assert isinstance(MySink(), SinkPlugin)
