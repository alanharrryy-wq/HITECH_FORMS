from __future__ import annotations

from dataclasses import dataclass

from hitech_forms.platform.settings import get_settings


@dataclass(frozen=True)
class FeatureFlags:
    demo: bool
    webhooks_outbox: bool
    rate_limit: bool
    metrics: bool


_FLAGS: FeatureFlags | None = None


def get_feature_flags() -> FeatureFlags:
    global _FLAGS
    if _FLAGS is None:
        settings = get_settings()
        _FLAGS = FeatureFlags(
            demo=settings.feature_demo,
            webhooks_outbox=settings.feature_webhooks_outbox,
            rate_limit=settings.feature_rate_limit,
            metrics=settings.feature_metrics,
        )
    return _FLAGS


def reset_feature_flags_cache() -> None:
    global _FLAGS
    _FLAGS = None
