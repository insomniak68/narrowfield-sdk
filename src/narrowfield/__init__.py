"""Narrowfield SDK — Data contracts and plugin interfaces.

This package provides the types and protocols needed to build
Narrowfield plugins. It has zero dependencies beyond the stdlib.

Plugin authors: implement SourcePlugin and/or SinkPlugin using the
data models defined here.
"""

from .spec import (
    SourcePlugin,
    SinkPlugin,
    JobImport,
    CandidateImport,
    SkillDefinition,
    FixedSkillDefinition,
    ScreeningDecision,
    DecisionDetail,
    DecisionOutcome,
    PluginInfo,
    PluginError,
    ConfigField,
)

__all__ = [
    "SourcePlugin",
    "SinkPlugin",
    "JobImport",
    "CandidateImport",
    "SkillDefinition",
    "FixedSkillDefinition",
    "ScreeningDecision",
    "DecisionDetail",
    "DecisionOutcome",
    "PluginInfo",
    "PluginError",
    "ConfigField",
]

__version__ = "0.1.0"
