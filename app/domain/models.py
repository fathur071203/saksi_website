from dataclasses import dataclass, field
from typing import List


@dataclass(slots=True)
class Badge:
    topic: str
    level: str
    awarded_at: str
    description: str


@dataclass(slots=True)
class ExpertProfile:
    name: str
    badges: List[Badge]
    courtroom_hours: int
    status: str
    unit: str
    expertise_summary: str
    response_sla_minutes: int


@dataclass(slots=True)
class RegulationChunk:
    code: str
    title: str
    chapter: str
    article: str
    summary: str
    keywords: List[str] = field(default_factory=list)


@dataclass(slots=True)
class BriefSection:
    title: str
    body: str


@dataclass(slots=True)
class LegalBrief:
    scenario: str
    regulations: List[BriefSection]
    bap_draft: List[str]
    trap_questions: List[str]
    disclaimer: str


@dataclass(slots=True)
class InterrogationFeedback:
    score: int
    verdict: str
    transcript: str
    strengths: List[str]
    risks: List[str]
    highlighted_transcript: str
    coaching_prompt: str
