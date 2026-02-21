from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(".").resolve()

def _norm(s: str) -> str:
    return s.replace("\r\n", "\n").replace("\r", "\n")

def write_if_diff(rel: str, content: str) -> None:
    p = ROOT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    new = _norm(content)
    if p.exists():
        old = _norm(p.read_text(encoding="utf-8"))
        if old == new:
            return
    p.write_text(new, encoding="utf-8")

REQ = """\
fastapi==0.129.0
uvicorn==0.41.0
SQLAlchemy==2.0.46
alembic==1.18.4
Jinja2==3.1.6
typer==0.24.0
"""

REQ_DEV = """\
ruff==0.15.2
mypy==1.19.1
pytest==9.0.2
httpx==0.28.1
"""

PYPROJECT = """\
[project]
name = "hitech-forms"
version = "0.1.0"
description = "HITECH_FORMS: Python-first forms.app-style system"
requires-python = ">=3.10"
dependencies = []

[build-system]
requires = ["setuptools>=69", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "B", "UP"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = false
no_implicit_optional = true
strict_optional = true
"""

ENV_EXAMPLE = """\
HFORMS_DB_PATH=var/hitech_forms.db
HFORMS_HOST=127.0.0.1
HFORMS_PORT=8000
HFORMS_FLAG_DEMO=false
"""

GITIGNORE = """\
.venv/
__pycache__/
*.pyc
var/
*.db
.pytest_cache/
.mypy_cache/
.ruff_cache/
dist/
build/
*.egg-info/
"""

README = """\
# HITECH_FORMS (Wave 1 scaffold)

## Run
PowerShell:
- `powershell -NoProfile -ExecutionPolicy Bypass -File .\\tools\\bootstrap.ps1`

## Endpoints
- API health: http://127.0.0.1:8000/api/health
- Admin forms: http://127.0.0.1:8000/admin/forms
"""

BOOTSTRAP_PS1 = r"""\
$ErrorActionPreference = "Stop"

function Step($percent, $msg) {
  Write-Progress -Activity "HITECH_FORMS Bootstrap" -Status $msg -PercentComplete $percent
  Write-Host "[$percent%] $msg"
}

Step 5 "Setting deterministic environment..."
$env:PYTHONHASHSEED = "0"

Step 10 "Ensuring folders..."
$folders = @(".\.venv", ".\var", ".\var\logs", ".\var\exports")
foreach ($f in $folders) { if (!(Test-Path $f)) { New-Item -ItemType Directory -Path $f | Out-Null } }

Step 20 "Creating venv if missing..."
if (!(Test-Path ".\.venv\Scripts\python.exe")) { python -m venv .\.venv }
$Py = ".\.venv\Scripts\python.exe"

Step 30 "Upgrading pip..."
& $Py -m pip install --upgrade pip

Step 42 "Installing dependencies..."
& $Py -m pip install -r .\requirements.txt
& $Py -m pip install -r .\requirements-dev.txt

Step 50 "Installing project (editable)..."
& $Py -m pip install -e .

Step 65 "Running migrations..."
& $Py -m hitech_forms.ops.cli db upgrade

Step 75 "Seeding demo data (idempotent)..."
& $Py -m hitech_forms.ops.cli seed --demo

Step 82 "Ruff auto-fix + format..."
& $Py -m ruff check src tests --fix
& $Py -m ruff format src tests

Step 88 "Running integration gate (Wave 1)..."
& $Py -m hitech_forms.ops.ci lint
& $Py -m hitech_forms.ops.ci typecheck
& $Py -m hitech_forms.ops.ci start-smoke
& $Py -m hitech_forms.ops.ci e2e --flows smoke_health
& $Py -m hitech_forms.ops.ci determinism-check

Step 92 "Starting server..."
$port = 8000
$env:HFORMS_DB_PATH = ".\var\hitech_forms.db"
$env:HFORMS_HOST = "127.0.0.1"
$env:HFORMS_PORT = "$port"
Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -Command `"$Py -m hitech_forms.ops.cli runserver --host 127.0.0.1 --port $port`""

Step 97 "Opening browser..."
Start-Sleep -Seconds 1
Start-Process "http://127.0.0.1:$port/admin/forms"

Step 100 "Done. 🚀"
Write-Progress -Activity "HITECH_FORMS Bootstrap" -Completed
"""

ALEMBIC_INI = """\
[alembic]
script_location = migrations
prepend_sys_path = .

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
"""

ALEMBIC_ENV = """\
from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from hitech_forms.platform.settings import get_settings
from hitech_forms.db.models import Base  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def get_url() -> str:
    s = get_settings()
    return f"sqlite:///{s.db_path}"

def run_migrations_offline() -> None:
    url = get_url()
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool, future=True)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
"""

MIG_0001 = """\
\"\"\"0001_initial

Revision ID: 0001_initial
Revises:
Create Date: 2026-02-21
\"\"\"

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "forms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=200), nullable=True, unique=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "form_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("form_id", sa.Integer(), sa.ForeignKey("forms.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("published_at", sa.Integer(), nullable=True),
        sa.UniqueConstraint("form_id", "version_number", name="uq_form_version"),
    )

    op.create_table(
        "fields",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("form_version_id", sa.Integer(), sa.ForeignKey("form_versions.id"), nullable=False),
        sa.Column("field_key", sa.String(length=120), nullable=False),
        sa.Column("label", sa.String(length=200), nullable=False),
        sa.Column("type", sa.String(length=30), nullable=False, server_default="text"),
        sa.Column("required", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("config_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("form_version_id", "field_key", name="uq_field_key_per_version"),
    )

def downgrade() -> None:
    op.drop_table("fields")
    op.drop_table("form_versions")
    op.drop_table("forms")
"""

FILES: dict[str, str] = {}

# Core docs/config
FILES["README.md"] = README
FILES["pyproject.toml"] = PYPROJECT
FILES["requirements.txt"] = REQ
FILES["requirements-dev.txt"] = REQ_DEV
FILES[".env.example"] = ENV_EXAMPLE
FILES[".gitignore"] = GITIGNORE
FILES["tools/bootstrap.ps1"] = BOOTSTRAP_PS1

# Package init
FILES["src/hitech_forms/__init__.py"] = '__all__ = ["__version__"]\n__version__ = "0.1.0"\n'

# Platform
FILES["src/hitech_forms/platform/settings.py"] = """\
from __future__ import annotations

from dataclasses import dataclass
import os

@dataclass(frozen=True)
class Settings:
    db_path: str = os.getenv("HFORMS_DB_PATH", "var/hitech_forms.db")
    host: str = os.getenv("HFORMS_HOST", "127.0.0.1")
    port: int = int(os.getenv("HFORMS_PORT", "8000"))

_SETTINGS: Settings | None = None

def get_settings() -> Settings:
    global _SETTINGS
    if _SETTINGS is None:
        _SETTINGS = Settings()
    return _SETTINGS
"""
FILES["src/hitech_forms/platform/feature_flags.py"] = """\
from __future__ import annotations

from dataclasses import dataclass
import os

def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name, str(default)).strip().lower()
    return v in ("1", "true", "yes", "on")

@dataclass(frozen=True)
class FeatureFlags:
    demo: bool = _env_bool("HFORMS_FLAG_DEMO", False)

_FLAGS: FeatureFlags | None = None

def get_feature_flags() -> FeatureFlags:
    global _FLAGS
    if _FLAGS is None:
        _FLAGS = FeatureFlags()
    return _FLAGS
"""
FILES["src/hitech_forms/platform/determinism.py"] = """\
from __future__ import annotations

import json
import os
from typing import Any

def canonical_json_dumps(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

def ensure_determinism_env() -> None:
    if os.getenv("PYTHONHASHSEED") != "0":
        raise RuntimeError("Determinism violation: PYTHONHASHSEED must be 0.")

def stable_sorted(seq, key=None):
    return sorted(seq, key=key)
"""
FILES["src/hitech_forms/platform/slug.py"] = """\
from __future__ import annotations

import re

_slug_re = re.compile(r"[^a-z0-9]+", re.IGNORECASE)

def slugify(text: str) -> str:
    t = (text or "").strip().lower()
    t = _slug_re.sub("-", t).strip("-")
    return t or "form"
"""
FILES["src/hitech_forms/platform/__init__.py"] = """\
from __future__ import annotations

from .determinism import canonical_json_dumps, ensure_determinism_env
from .feature_flags import FeatureFlags, get_feature_flags
from .settings import Settings, get_settings
from .slug import slugify

__all__ = [
    "Settings",
    "get_settings",
    "FeatureFlags",
    "get_feature_flags",
    "canonical_json_dumps",
    "ensure_determinism_env",
    "slugify",
]
"""

# App
FILES["src/hitech_forms/app/lifespan.py"] = """\
from __future__ import annotations

from contextlib import asynccontextmanager

from hitech_forms.platform.settings import get_settings

@asynccontextmanager
async def lifespan(app):
    _ = get_settings()
    yield
"""
FILES["src/hitech_forms/app/main.py"] = """\
from __future__ import annotations

from fastapi import FastAPI

from hitech_forms.api.router import api_router
from hitech_forms.app.lifespan import lifespan
from hitech_forms.web.router import web_router

app = FastAPI(title="HITECH_FORMS", lifespan=lifespan)
app.include_router(api_router)
app.include_router(web_router)
"""

# API + Web
FILES["src/hitech_forms/api/router.py"] = """\
from __future__ import annotations

import json

from fastapi import APIRouter

from hitech_forms.platform.determinism import canonical_json_dumps

api_router = APIRouter(prefix="/api")

@api_router.get("/health")
def health():
    payload = {"ok": True, "service": "HITECH_FORMS"}
    return json.loads(canonical_json_dumps(payload))
"""
FILES["src/hitech_forms/api/__init__.py"] = "__all__ = ['api_router']\nfrom .router import api_router\n"
FILES["src/hitech_forms/web/router.py"] = """\
from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

web_router = APIRouter()

@web_router.get("/admin/forms")
def admin_forms():
    return HTMLResponse("<html><body><h1>HITECH_FORMS</h1><p>Wave 1: SSR skeleton ✅</p></body></html>")
"""
FILES["src/hitech_forms/web/__init__.py"] = "__all__ = ['web_router']\nfrom .router import web_router\n"

# DB minimal (engine/session/models) + migrations
FILES["src/hitech_forms/db/engine.py"] = """\
from __future__ import annotations

from sqlalchemy import create_engine

from hitech_forms.platform.settings import get_settings

_ENGINE = None

def get_engine():
    global _ENGINE
    if _ENGINE is None:
        s = get_settings()
        url = f"sqlite:///{s.db_path}"
        _ENGINE = create_engine(url, future=True, echo=False, connect_args={"check_same_thread": False})
    return _ENGINE
"""
FILES["src/hitech_forms/db/session.py"] = """\
from __future__ import annotations

from contextlib import contextmanager

from sqlalchemy.orm import sessionmaker

from hitech_forms.db.engine import get_engine

SessionLocal = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, future=True)

@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
"""
FILES["src/hitech_forms/db/__init__.py"] = """\
from __future__ import annotations

from .engine import get_engine
from .session import SessionLocal, session_scope

__all__ = ["get_engine", "session_scope", "SessionLocal"]
"""
FILES["src/hitech_forms/db/models/base.py"] = """\
from __future__ import annotations

from sqlalchemy.orm import declarative_base

Base = declarative_base()
"""
FILES["src/hitech_forms/db/models/form.py"] = """\
from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hitech_forms.db.models.base import Base

class Form(Base):
    __tablename__ = "forms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    versions = relationship("FormVersion", back_populates="form", cascade="all, delete-orphan")
"""
FILES["src/hitech_forms/db/models/form_version.py"] = """\
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hitech_forms.db.models.base import Base

class FormVersion(Base):
    __tablename__ = "form_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    form_id: Mapped[int] = mapped_column(ForeignKey("forms.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_at: Mapped[int | None] = mapped_column(Integer, nullable=True)

    form = relationship("Form", back_populates="versions")
    fields = relationship("Field", back_populates="form_version", cascade="all, delete-orphan")
"""
FILES["src/hitech_forms/db/models/field.py"] = """\
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from hitech_forms.db.models.base import Base

class Field(Base):
    __tablename__ = "fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    form_version_id: Mapped[int] = mapped_column(ForeignKey("form_versions.id"), nullable=False)
    field_key: Mapped[str] = mapped_column(String(120), nullable=False)
    label: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str] = mapped_column(String(30), nullable=False, default="text")
    required: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    form_version = relationship("FormVersion", back_populates="fields")
"""
FILES["src/hitech_forms/db/models/__init__.py"] = """\
from __future__ import annotations

from .base import Base
from .field import Field
from .form import Form
from .form_version import FormVersion

__all__ = ["Base", "Form", "FormVersion", "Field"]
"""

FILES["migrations/alembic.ini"] = ALEMBIC_INI
FILES["migrations/env.py"] = ALEMBIC_ENV
FILES["migrations/versions/0001_initial.py"] = MIG_0001
FILES["migrations/script.py.mako"] = "<%text># alembic template</%text>\n"

# Ops CLI + CI
FILES["src/hitech_forms/ops/cli.py"] = """\
from __future__ import annotations

import os
import subprocess
import sys

import typer

from hitech_forms.platform.settings import get_settings

app = typer.Typer(add_completion=False)

db = typer.Typer(add_completion=False)
app.add_typer(db, name="db")

@app.command()
def runserver(host: str = "127.0.0.1", port: int = 8000):
    import uvicorn
    uvicorn.run("hitech_forms.app.main:app", host=host, port=port, reload=False)

@db.command("upgrade")
def db_upgrade():
    s = get_settings()
    env = os.environ.copy()
    env["HFORMS_DB_PATH"] = s.db_path
    subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "migrations/alembic.ini", "upgrade", "head"],
        check=True,
        env=env,
    )

@app.command()
def seed(demo: bool = True):
    typer.echo("seed: demo placeholder (Wave 1) ✅")

def main():
    app()

if __name__ == "__main__":
    main()
"""
FILES["src/hitech_forms/ops/ci.py"] = """\
from __future__ import annotations

import subprocess
import sys

import typer

from hitech_forms.platform.determinism import ensure_determinism_env

app = typer.Typer(add_completion=False)

@app.command()
def lint():
    subprocess.run([sys.executable, "-m", "ruff", "check", "src", "tests"], check=True)
    subprocess.run([sys.executable, "-m", "ruff", "format", "--check", "src", "tests"], check=True)

@app.command()
def typecheck():
    subprocess.run([sys.executable, "-m", "mypy", "src"], check=True)

@app.command()
def start_smoke():
    # Reuse E2E smoke deterministically (no flaky UI automation)
    subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/e2e", "-k", "smoke_health"], check=True)

@app.command()
def e2e(flows: str = "smoke_health"):
    subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/e2e", "-k", flows], check=True)

@app.command()
def determinism_check():
    ensure_determinism_env()

def main():
    app()

if __name__ == "__main__":
    main()
"""

# E2E async httpx
FILES["tests/e2e/test_smoke_health.py"] = """\
from __future__ import annotations

import pytest
import httpx

@pytest.mark.anyio
async def test_smoke_health():
    from hitech_forms.app.main import app as asgi_app

    transport = httpx.ASGITransport(app=asgi_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.get("/api/health")
        assert r.status_code == 200
        assert r.json() == {"ok": True, "service": "HITECH_FORMS"}

        r2 = await client.get("/admin/forms")
        assert r2.status_code == 200
"""

def main() -> None:
    for rel, content in FILES.items():
        write_if_diff(rel, content)
    print("Wave 1 scaffold generated ✅")

if __name__ == "__main__":
    main()
