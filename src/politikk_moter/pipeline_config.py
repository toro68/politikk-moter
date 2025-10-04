"""Konfigurasjon for Slack-pipelines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


@dataclass(frozen=True)
class PipelineConfig:
    """Konfigurasjon for én Slack-pipeline."""

    key: str
    description: str
    kommune_groups: Sequence[str]
    calendar_sources: Sequence[str]
    slack_webhook_env: str
    enabled: bool = True


DEFAULT_PIPELINES: List[PipelineConfig] = [
    PipelineConfig(
        key="standard",
        description="Standardkanal med kommuner fra eksisterende oppsett",
        kommune_groups=("core",),
        calendar_sources=("arrangementer_sa",),
        slack_webhook_env="SLACK_WEBHOOK_URL",
    ),
    PipelineConfig(
        key="utvidet",
        description="Utvidet kanal med flere kommuner og alternativ kalender",
        kommune_groups=("core", "extended"),
        calendar_sources=("regional_kultur", "andre_slack"),
        slack_webhook_env="SLACK_WEBHOOK_URL_UTVIDET",
    ),
]


def get_pipeline_configs(include_disabled: bool = False) -> List[PipelineConfig]:
    """Returner tilgjengelige pipelines, eventuelt filtrert på enabled."""
    if include_disabled:
        return list(DEFAULT_PIPELINES)
    return [pipeline for pipeline in DEFAULT_PIPELINES if pipeline.enabled]