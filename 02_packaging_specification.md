# mypylogger v1 — Packaging & Hosting Specification

**Audience:** AI agent implementing the rewrite.
**Status:** Authoritative. Implement exactly as written; do not infer unstated behavior.
**Companion to:** `01_rewrite_specification.md` (library functionality). This document covers everything *around* the code: versioning, packaging metadata, PyPI hosting, CI/CD, and teardown of the legacy apparatus.
**Derived from:** QnA session 2026-07-12.

---

## 1. Goals and constraints

- **Clean break from `0.2.x`.** No legacy code, config, or references carried forward. Fresh start.
- **Minimal, convention-following packaging.** Every artifact must be industry-standard and self-justifying. No homegrown subsystems.
- **Zero stored secrets.** Publishing uses OIDC (PyPI Trusted Publishing); no API token persists anywhere.
- **Portfolio signal:** every visible element (metadata, badges, README) must be *honest and verifiable*. No hand-set values that imply measurement.
- Inherits the library constraints: stdlib-only, Python ≥ 3.12, macOS/Linux/Lambda/ECS targets.

---

## 2. Version & branch strategy

- **Target version: `1.0.0`.** A clean semantic break from the `0.2.x` line, signaling production-ready.
- **Rewrite happens on a branch named for the version** (e.g. `v1.0.0` or `rewrite/1.0.0`).
- **The rewrite replaces `main` entirely.** When merged, `main` contains only the new codebase — no legacy files survive (see §11 teardown manifest).
- **Single source of version truth:** the string `__version__ = "1.0.0"` in `src/mypylogger/__init__.py`. It exists in exactly one place. `pyproject.toml` derives it dynamically (§4).

---

## 3. Project metadata (`pyproject.toml` → `[project]`)

Follow PEP 621 + PEP 639 (SPDX license expression). Exact values:

```toml
[project]
name = "mypylogger"
dynamic = ["version"]
description = "Zero-dependency structured JSON logging for Python, with sensible defaults."
readme = "README.md"
requires-python = ">=3.12"
license = "MIT"
license-files = ["LICENSE"]
authors = [{ name = "Stephen Abbot", email = "stephen.abbot@denverbytes.com" }]
maintainers = [{ name = "Stephen Abbot", email = "stephen.abbot@denverbytes.com" }]
keywords = [
    "logging",
    "json",
    "structured-logging",
    "zero-dependency",
    "json-formatter",
    "observability",
]
classifiers = [
    "Development Status :: 5 - Production/Stable",
    "Intended Audience :: Developers",
    "Intended Audience :: System Administrators",
    "Operating System :: MacOS",
    "Operating System :: POSIX :: Linux",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Topic :: System :: Logging",
    "Typing :: Typed",
]
dependencies = []

[project.urls]
Homepage = "https://github.com/stephenabbot/mypylogger"
Repository = "https://github.com/stephenabbot/mypylogger"
Issues = "https://github.com/stephenabbot/mypylogger/issues"
Changelog = "https://github.com/stephenabbot/mypylogger/blob/main/CHANGELOG.md"
```

**Metadata rules:**
- **Email is exactly `stephen.abbot@denverbytes.com`** (dotted). This is a routed domain address the author controls. Replace all `admin@bittikens.com` occurrences — none survive.
- **No `License ::` classifier** — PEP 639 uses the `license` SPDX expression + `license-files` instead. Do not emit both.
- **GitHub identity lives in `[project.urls]`**, not in author fields. Do not put the handle in `authors`.
- Drop the `Download` / `Source Code` duplicate URLs from the old file; the four above are sufficient and non-redundant.

---

## 4. Build backend & version single-source

Convention-following hatchling setup:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.version]
path = "src/mypylogger/__init__.py"

[tool.hatch.build.targets.wheel]
packages = ["src/mypylogger"]
```

- `[project].dynamic = ["version"]` + `[tool.hatch.version].path` means the version is read from `__version__` in the module. **Do not** also hardcode `version =` under `[project]`.
- `src/` layout retained. The package is the single-file `src/mypylogger/__init__.py` per the functional spec §2.

---

## 5. Publishing — PyPI Trusted Publishing (OIDC)

**Mechanism:** GitHub Actions → PyPI Trusted Publishing. No API token is stored in GitHub secrets or anywhere else.

**One-time PyPI configuration (manual, done in the PyPI web UI — document, do not script):**
- On the `mypylogger` project, add a Trusted Publisher: owner `stephenabbot`, repository `mypylogger`, workflow filename `publish.yml`, environment name `pypi`.

**Publish workflow (`.github/workflows/publish.yml`) — following the pypa convention:**
- Trigger: on GitHub Release `published` (tag `v*`).
- Two jobs:
  1. **build** — checkout, set up Python 3.12, `python -m build` (sdist + wheel), upload artifacts.
  2. **publish** — needs `build`; runs in the `pypi` environment; permission `id-token: write`; uses `pypa/gh-action-pypi-publish@release/v1` with no token input (OIDC is automatic).

```yaml
permissions:
  id-token: write   # required for Trusted Publishing; nothing else
```

- **No `TWINE_*` variables, no stored token, no token rotation.** The entire `infrastructure/` directory (Terraform, CloudFormation, rotation Lambda) is deleted (§11) — it exists only to manage a token this approach eliminates.

---

## 6. CI/CD — consolidated workflows

Exactly **two** workflows. All `.disabled`, `security-driven-release`, `monitoring-step`, `yaml-validation-step`, and multi-stage security workflows are deleted.

**`.github/workflows/ci.yml`** — on push to any branch + pull requests to `main`:
- Matrix: Python `3.12`, `3.13`.
- Steps: install (dev group), `ruff check`, `ruff format --check`, `mypy`, `pytest` (with coverage gate).
- **Coverage is a CI gate only** (`--cov-fail-under`, threshold retained). It produces **no badge and no external upload** (no Codecov). Coverage failure fails the build; that is its entire role.

**`.github/workflows/publish.yml`** — §5.

---

## 7. Quality gates (retained, lean)

Keep only the tooling that serves a single-file library:
- **ruff** — lint + format. Prune the ~250-line rule config to a sensible default set; do not carry forward per-file-ignores referencing deleted `scripts/`, `security/`, `infrastructure/`.
- **mypy** — strict, `python_version = "3.12"`, `packages = ["mypylogger"]`.
- **pytest** — `--cov=mypylogger`, `--cov-fail-under=<threshold>`, strict markers.

Drop from `[dependency-groups]`: `bandit`, `safety`, `pip-audit`, `deptry`, `interrogate`, `codespell`, `sphinx-lint`, `bump2version`, `boto3`, `requests`, `pytest-benchmark`, `twine`, `tomli`, and the `security` / `docs` groups. Retain: `pytest`, `pytest-cov`, `mypy`, `ruff`, `build`. Remove `[tool.bumpversion]` entirely (version is single-sourced in `__init__.py`).

---

## 8. Badges

Exactly **four**, all dynamic and authoritative. No hand-set values.

| Badge | Source | Link target (href) |
|---|---|---|
| PyPI Version | `img.shields.io/pypi/v/mypylogger` | PyPI project page |
| Python Versions | `img.shields.io/pypi/pyversions/mypylogger` | PyPI project page |
| License | `img.shields.io/github/license/stephenabbot/mypylogger` | `LICENSE` on GitHub |
| CI | `img.shields.io/github/actions/workflow/status/stephenabbot/mypylogger/ci.yml` | the **workflow runs page**, not the image URL |

**Rules:**
- **Fix the legacy href bug:** each badge links to its real destination (PyPI / workflow page), never back to its own shields.io image URL.
- **Deleted badges and why:** coverage (hand-set string implies measurement), security-`verified` (static, implies a scan result), code-style-ruff and type-checked-mypy (low-signal convention badges — dropped by choice), downloads (vanity; reads ~0 on a fresh release).
- **Delete the entire `badges/` Python package** (~180KB: `dynamic_badges.py`, `monitoring.py`, `live_status.py`, `github_pages.py`, `status.py`, etc.). Badges are markdown image links in the README — no generation subsystem.

---

## 9. README (portfolio-facing)

Minimal, honest, single-file-library appropriate:
- Badge row (§8), one-line description, install (`pip install mypylogger`), a short usage example (`get_logger` / `bind` / `clear_bindings`), the env-var config table, and a link to the specs.
- No sphinx, no Read-the-Docs, no `docs/` build. The README is the documentation.

---

## 10. Repository conventions

- `LICENSE` (MIT) retained as-is.
- Add `CHANGELOG.md` with a `1.0.0` entry noting the clean rewrite and the breaking changes (Python ≥ 3.12 floor, new public API, removed legacy modules).
- `.gitignore` retained/trimmed as needed. `z_commands.sh` / `z_results.txt` remain gitignored.

---

## 11. Teardown manifest (delete on rewrite — nothing legacy survives)

Remove entirely:
- `infrastructure/` — Terraform, CloudFormation, PyPI token-rotation Lambda.
- `badges/` — the badge-generation package.
- `security/` — security tooling subsystem.
- `scripts/` — all 44 scripts.
- `docs/` — sphinx docs, Makefile, quality configs (README becomes the docs).
- `.github/workflows/*.disabled` and the `security-driven-release`, `monitoring-step`, `yaml-validation-step`, `security-automation-step`, `error-handling-step` workflows.
- `.github/SECURITY_CONFIG.yml`, `.github/SECURITY.md` — unless a minimal `SECURITY.md` is deliberately retained.
- `src/mypylogger/{config,formatters,handlers,core,exceptions}.py` — collapsed into single `__init__.py` per functional spec §2.
- `[tool.bumpversion]`, `[tool.deptry]`, and dev-dependency bloat (§7).
- Old `uv.lock` regenerated fresh against the trimmed dependency set.

Retain / rewrite: `pyproject.toml` (rewritten per this doc), `LICENSE`, `README.md` (rewritten), `.gitignore`, `tests/` (rewritten to the new API), `src/mypylogger/__init__.py` (new).

---

## 12. Metadata corrections from 0.2.x

| # | 0.2.x state | Correct state |
|---|---|---|
| 1 | `version = "0.2.8"` in `[project]` but `bumpversion current_version = "0.2.2"` — split truth | Single source: `__version__` in `__init__.py`; hatchling dynamic version |
| 2 | `requires-python = ">=3.8"` | `>=3.12` (matches functional spec) |
| 3 | Author email `admin@bittikens.com` | `stephen.abbot@denverbytes.com` |
| 4 | Classifiers list 3.8–3.11 | 3.12, 3.13 only |
| 5 | `License ::` classifier + `license = {text = "MIT"}` | PEP 639 `license = "MIT"` + `license-files`; no license classifier |
| 6 | Stored PyPI token + rotation Lambda + IaC | Trusted Publishing (OIDC), zero stored secrets |
| 7 | 6 active + 5 disabled workflows | Two: `ci.yml`, `publish.yml` |
| 8 | Homegrown `badges/` subsystem, 9 badges (some hand-set) | 4 dynamic badges, markdown-only |
| 9 | `Development Status :: 4 - Beta` | `5 - Production/Stable` (for 1.0.0) |

---

## 13. Non-goals (do not implement)

- Codecov or any external coverage-upload service.
- Read-the-Docs / sphinx documentation site.
- Any stored-token publishing path or token-rotation automation.
- Multi-stage security-scanning release pipeline.
- Dynamic/generated badges or a badge subsystem.
- Windows packaging/classifiers.
- Any dependency outside the dev toolchain (the shipped package stays zero-dependency).
