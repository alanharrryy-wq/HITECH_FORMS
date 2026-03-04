from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from hitech_forms.db import session_scope
from hitech_forms.db.repositories import (
    FormRepository,
    SubmissionRepository,
    WebhookOutboxRepository,
)
from hitech_forms.platform.determinism import canonical_json_dumps, utc_now_epoch
from hitech_forms.platform.settings import get_settings
from hitech_forms.services import (
    ExportService,
    FormService,
    SubmissionService,
    WebhookOutboxService,
)
from hitech_forms.services.webhooks import WebhookWorker

RUN_DIR_PATTERN = re.compile(r"^run-(\d{4})$")


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _next_run_name(root: Path) -> str:
    existing: list[int] = []
    if root.exists():
        for child in root.iterdir():
            if not child.is_dir():
                continue
            match = RUN_DIR_PATTERN.match(child.name)
            if match:
                existing.append(int(match.group(1)))
    next_id = (max(existing) if existing else 0) + 1
    return f"run-{next_id:04d}"


def _write_canonical_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(canonical_json_dumps(payload) + "\n", encoding="utf-8")


def _redacted_env_snapshot() -> str:
    deny_tokens = ("TOKEN", "SECRET", "PASSWORD", "KEY")
    lines: list[str] = []
    for key in sorted(os.environ):
        if not (key.startswith("HFORMS_") or key == "PYTHONHASHSEED"):
            continue
        value = os.environ.get(key, "")
        redacted = "***REDACTED***" if any(part in key for part in deny_tokens) else value
        lines.append(f"{key}={redacted}")
    return "\n".join(lines) + ("\n" if lines else "")


def _append_log(path: Path, event: str, **fields: Any) -> None:
    payload = {"event": event, "ts": utc_now_epoch(), **fields}
    with path.open("a", encoding="utf-8") as handle:
        handle.write(canonical_json_dumps(payload))
        handle.write("\n")


def run_demo_evidence(
    *,
    output_root: str = "var/demo_runs",
    submissions: int = 5,
    run_id: str | None = None,
    with_timestamp: bool = False,
    run_webhooks: bool = False,
) -> dict[str, Any]:
    settings = get_settings()
    root = _ensure_dir(Path(output_root))
    if run_id:
        run_name = run_id
    elif with_timestamp:
        run_name = f"run-ts-{utc_now_epoch()}"
    else:
        run_name = _next_run_name(root)

    run_dir = _ensure_dir(root / run_name)
    logs_dir = _ensure_dir(run_dir / "logs")
    events_log = logs_dir / "events.jsonl"
    csv_path = run_dir / "exported.csv"
    summary_path = run_dir / "summary.json"
    env_path = run_dir / "env_snapshot.txt"

    _append_log(events_log, "demo_start", run_id=run_name, output_root=str(root))

    created_form: dict[str, Any]
    submitted_ids: list[int] = []
    with session_scope() as session:
        form_repo = FormRepository(session)
        submission_repo = SubmissionRepository(session)
        webhook_repo = WebhookOutboxRepository(session)
        webhook_service = WebhookOutboxService(webhook_repo, settings)

        form_service = FormService(form_repo)
        submission_service = SubmissionService(form_repo, submission_repo, webhook_outbox_service=webhook_service)

        created_form = form_service.command_create_form(title="Investor Demo Intake", slug="investor-demo-intake")
        _append_log(events_log, "demo_form_created", form_id=created_form["id"], slug=created_form["slug"])
        form_service.command_replace_fields(
            form_id=created_form["id"],
            fields=[
                {"key": "name", "label": "Name", "type": "text", "required": True, "options": []},
                {"key": "email", "label": "Email", "type": "email", "required": True, "options": []},
                {
                    "key": "priority",
                    "label": "Priority",
                    "type": "select",
                    "required": True,
                    "options": ["low", "normal", "high"],
                },
                {"key": "notify", "label": "Notify", "type": "checkbox", "required": False, "options": []},
            ],
        )
        published = form_service.command_publish_form(created_form["id"])
        _append_log(events_log, "demo_form_published", form_id=published["id"], slug=published["slug"])

        priorities = ("low", "normal", "high")
        for idx in range(max(0, submissions)):
            payload = {
                "name": f"Demo User {idx:03d}",
                "email": f"demo{idx:03d}@example.com",
                "priority": priorities[idx % len(priorities)],
                "notify": "true" if idx % 2 == 0 else "false",
            }
            submission = submission_service.command_submit_public(slug=published["slug"], values=payload)
            submitted_ids.append(int(submission["id"]))
            _append_log(
                events_log,
                "demo_submission_created",
                submission_id=submission["id"],
                submission_seq=submission["submission_seq"],
            )

    with session_scope() as session:
        export_service = ExportService(FormRepository(session), SubmissionRepository(session))
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            for chunk in export_service.stream_form_csv(form_id=int(created_form["id"]), export_version="v1"):
                handle.write(chunk)
    _append_log(events_log, "demo_export_written", csv=str(csv_path))

    webhook_summary: dict[str, int] | None = None
    if run_webhooks:
        worker = WebhookWorker(settings=settings)
        result = worker.run_once(limit=max(1, submissions * settings.webhook_max_attempts))
        webhook_summary = {
            "processed": result.processed,
            "delivered": result.delivered,
            "retried": result.retried,
            "failed": result.failed,
        }
        _append_log(events_log, "demo_webhook_worker_run", **webhook_summary)

    env_path.write_text(_redacted_env_snapshot(), encoding="utf-8")
    summary = {
        "run_id": run_name,
        "run_dir": str(run_dir),
        "form_id": int(created_form["id"]),
        "form_slug": str(created_form["slug"]),
        "submissions_requested": int(submissions),
        "submissions_created": len(submitted_ids),
        "submission_ids": submitted_ids,
        "exported_csv": str(csv_path),
        "logs_dir": str(logs_dir),
        "webhook_worker": webhook_summary,
    }
    _write_canonical_json(summary_path, summary)
    _append_log(events_log, "demo_complete", summary_path=str(summary_path))
    return summary
