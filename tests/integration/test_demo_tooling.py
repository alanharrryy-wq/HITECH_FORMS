from __future__ import annotations

from pathlib import Path

from hitech_forms.ops.demo import run_demo_evidence
from hitech_forms.platform.settings import reset_settings_cache


def test_demo_evidence_run_folder_is_deterministic(runtime_env, monkeypatch, tmp_path: Path):
    _ = runtime_env
    monkeypatch.setenv("HFORMS_FEATURE_WEBHOOKS_OUTBOX", "false")
    reset_settings_cache()

    root = tmp_path / "demo-runs"
    first = run_demo_evidence(output_root=str(root), submissions=2, with_timestamp=False)
    second = run_demo_evidence(output_root=str(root), submissions=1, with_timestamp=False)

    assert first["run_id"] == "run-0001"
    assert second["run_id"] == "run-0002"
    assert Path(first["run_dir"]).exists()
    assert (Path(first["run_dir"]) / "summary.json").exists()
    assert (Path(first["run_dir"]) / "exported.csv").exists()
    assert (Path(first["run_dir"]) / "env_snapshot.txt").exists()
    assert (Path(first["run_dir"]) / "logs" / "events.jsonl").exists()
