"""Tests validating container deployment assets, Dockerfile, Docker Compose, and health endpoints."""
import os
import stat
from pathlib import Path
import pytest
import yaml
from fastapi.testclient import TestClient

from src.main import app


def test_dockerfile_structure():
    """Verify production Dockerfile directives, multi-stage build, and security hardening."""
    root_dir = Path(__file__).resolve().parents[2]
    dockerfile_path = root_dir / "Dockerfile"
    assert dockerfile_path.is_file(), "Dockerfile must exist at repository root"

    content = dockerfile_path.read_text(encoding="utf-8")
    assert "FROM python:3.12-slim AS builder" in content
    assert "FROM python:3.12-slim AS runner" in content
    assert "USER opc" in content, "Must run as non-root user 'opc' for container security"
    assert "EXPOSE 8000" in content
    assert "HEALTHCHECK" in content
    assert "uvicorn" in content


def test_docker_compose_configuration():
    """Verify docker-compose.yml syntax and critical production volume/network definitions."""
    root_dir = Path(__file__).resolve().parents[2]
    compose_path = root_dir / "docker-compose.yml"
    assert compose_path.is_file(), "docker-compose.yml must exist at repository root"

    with open(compose_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert "services" in data
    assert "opchub-server" in data["services"]
    svc = data["services"]["opchub-server"]
    assert "build" in svc
    assert any("8000" in str(p) for p in svc.get("ports", []))
    assert any("./data:/app/data" in str(v) for v in svc.get("volumes", []))
    assert "healthcheck" in svc
    assert "networks" in svc


def test_dockerignore_and_env_template():
    """Verify .dockerignore exclusions and .env.example environment variables."""
    root_dir = Path(__file__).resolve().parents[2]

    dockerignore_path = root_dir / ".dockerignore"
    assert dockerignore_path.is_file()
    di_content = dockerignore_path.read_text(encoding="utf-8")
    assert ".git" in di_content
    assert ".venv" in di_content
    assert "__pycache__" in di_content

    env_path = root_dir / ".env.example"
    assert env_path.is_file()
    env_content = env_path.read_text(encoding="utf-8")
    assert "OPCHUB_PORT" in env_content
    assert "SILICONFLOW_API_KEY" in env_content


def test_quickstart_scripts_exist():
    """Verify quickstart helper scripts exist and bash script has execution permissions."""
    root_dir = Path(__file__).resolve().parents[2]
    sh_script = root_dir / "scripts" / "quickstart.sh"
    bat_script = root_dir / "scripts" / "quickstart.bat"

    assert sh_script.is_file()
    assert bat_script.is_file()

    # Check executable permission on POSIX systems
    if os.name != "nt":
        st = os.stat(sh_script)
        assert bool(st.st_mode & stat.S_IXUSR), "quickstart.sh must have user execute bit set"


def test_container_health_endpoints():
    """Verify /health and /healthz health check endpoints."""
    client = TestClient(app)

    res_health = client.get("/health")
    assert res_health.status_code == 200
    data_health = res_health.json()
    assert data_health["status"].upper() in ("HEALTHY", "OK", "SUCCESS", "UP")

    res_healthz = client.get("/healthz")
    assert res_healthz.status_code == 200
    data_healthz = res_healthz.json()
    assert "uptime_seconds" in data_healthz or "status" in data_healthz or "kernel_status" in data_healthz


def test_web_console_root_serving():
    """Verify GET / and GET /app return 200 HTML page."""
    client = TestClient(app)

    res_root = client.get("/")
    assert res_root.status_code == 200
    assert "text/html" in res_root.headers.get("content-type", "")

    res_app = client.get("/app")
    assert res_app.status_code == 200
    assert "text/html" in res_app.headers.get("content-type", "")


def test_console_html_javascript_syntax_validity():
    """Verify that all inline JavaScript in the web console HTML is free of syntax errors."""
    import re
    import shutil
    import subprocess

    root_dir = Path(__file__).resolve().parents[2]
    html_path = root_dir / "hs_dev_docs/_02_feature_spec/_03_prototype_html/opchub_all_pages_demo.html"
    assert html_path.is_file(), f"HTML file not found at {html_path}"

    html_content = html_path.read_text(encoding="utf-8")
    scripts = re.findall(r"<script.*?>([\s\S]*?)</script>", html_content)
    assert len(scripts) > 0, "No script tags found in web console HTML"

    node_bin = shutil.which("node")
    if node_bin:
        for idx, script in enumerate(scripts):
            proc = subprocess.run(
                [node_bin, "--check"],
                input=script,
                text=True,
                capture_output=True,
            )
            assert proc.returncode == 0, f"JavaScript syntax error in script block #{idx}:\n{proc.stderr}"

