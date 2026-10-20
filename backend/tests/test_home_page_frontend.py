"""Tests for Home Page (Landing Page & Content Showcase) and Unauthenticated Access Restriction.

Verifies:
1. Frontend dist bundle exists and contains the HomeView promotional showcase content.
2. Unauthenticated user restriction: HomeView is the default and only visible page for unlogged users.
3. Content showcase style elements: Bento grid, metric pillars, journey roadmap, testimonials, and content exhibition tabs.
4. Promotional message accurately describes OpcHub's capabilities (Policy Radar, SOP documents, Product Showcase, Demands Marketplace, Perks).
"""
import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from frontend.server import app as frontend_app

client = TestClient(frontend_app)


def test_frontend_serves_landing_page():
    """Verify that GET / serves the compiled SPA index.html with 200 OK."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    assert '<div id="app"></div>' in resp.text
    assert "OpcHub" in resp.text


def test_frontend_dist_contains_home_promotional_content():
    """Verify that built JS/CSS bundle contains platform promotional keywords and Bento grid."""
    dist_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist" / "assets"
    assert dist_dir.is_dir(), "Frontend dist assets directory must exist"

    js_files = list(dist_dir.glob("*.js"))
    assert len(js_files) > 0, "At least one JS bundle must exist"

    combined_js = ""
    for js_file in js_files:
        combined_js += js_file.read_text(encoding="utf-8")

    # Requirement 2: 首页展示的内容是本平台的宣传
    promotional_keywords = [
      "一人公司",
      "超级个体",
      "商业操作系统",
      "政策雷达",
      "流程文书",
      "产品橱窗",
      "需求集市",
      "生态特权",
    ]
    for kw in promotional_keywords:
        assert kw in combined_js, f"Promotional keyword '{kw}' missing from compiled frontend bundle"

    # Requirement 3: 首页的风格可以参考内容展示类平台的设计思路 (Bento grid, Exhibition, Metrics, Journey)
    content_showcase_indicators = [
      "四大核心支柱",
      "精选展厅",
      "一人公司演进路径",
      "听听来自前线创客的真实声音",
    ]
    for indicator in content_showcase_indicators:
        assert indicator in combined_js, f"Showcase element '{indicator}' missing from bundle"


def test_unauthenticated_user_access_gated_in_source():
    """Verify in App.vue and Navbar.vue that unauthenticated users are restricted strictly to HomeView."""
    frontend_src = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"
    app_vue = (frontend_src / "App.vue").read_text(encoding="utf-8")
    navbar_vue = (frontend_src / "components" / "Navbar.vue").read_text(encoding="utf-8")
    home_vue = (frontend_src / "views" / "HomeView.vue").read_text(encoding="utf-8")

    # 1. HomeView is imported and default activeTab is 'home'
    assert "import HomeView from '@/views/HomeView.vue'" in app_vue
    assert "activeTab = ref('home')" in app_vue

    # 2. Main rendering container strictly restricts unauthenticated users to HomeView
    assert "v-if=\"!userSession || activeTab === 'home'\"" in app_vue
    assert "v-else-if=\"userSession && currentRole !== 'ADMIN'\"" in app_vue

    # 3. handleSwitchTab intercepts unauthenticated requests
    assert "!userSession.value && tab !== 'home'" in app_vue
    assert "showLoginModal.value = true" in app_vue

    # 4. Navbar displays navigation tabs ONLY after login (no locks), and provides login/register pill
    assert 'v-if="userSession" class="nav-tabs-wrapper"' in navbar_vue
    assert "nav-lock-badge" not in navbar_vue
    assert "🔒" not in navbar_vue
    assert "登录 / 入驻" in navbar_vue


def test_page_display_width_locked_consistently():
    """Verify that page display width is locked consistently across all views and styles."""
    style_css = (Path(__file__).resolve().parent.parent.parent / "frontend" / "src" / "style.css").read_text(encoding="utf-8")
    
    # 1. Scrollbar gutter is stabilized to avoid visual jitter across pages of varying lengths
    assert "scrollbar-gutter: stable" in style_css
    assert "overflow-y: scroll" in style_css

    # 2. Header and Main containers have fixed unified 1240px max-width and box-sizing
    assert "max-width: 1240px" in style_css
    assert "flex: 1 0 auto" in style_css

    # 3. All view panels are locked to 100% width of the container
    assert ".view-panel" in style_css
    assert "width: 100%" in style_css


def test_page_refresh_and_mode_persistence_in_source():
    """Verify in App.vue that page refresh maintains current page and does not auto-switch page mode."""
    frontend_src = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"
    app_vue = (frontend_src / "App.vue").read_text(encoding="utf-8")

    # 1. Page mode (role) and active tab are persisted to localStorage
    assert "localStorage.setItem('opchub_current_role'" in app_vue
    assert "localStorage.setItem('opchub_active_tab'" in app_vue
    assert "localStorage.getItem('opchub_current_role')" in app_vue
    assert "localStorage.getItem('opchub_active_tab')" in app_vue

    # 2. URL hash is synchronized and monitored via hashchange
    assert "window.location.hash" in app_vue
    assert "hashchange" in app_vue

    # 3. In checkSession, existing selected mode is preserved instead of unconditionally forcing ADMIN
    assert "savedRole === 'MAKER' || savedRole === 'ADMIN'" in app_vue
    assert "currentRole.value = savedRole" in app_vue

    # 4. User session is hydrated on startup to avoid page flash
    assert "localStorage.getItem('opchub_user_session')" in app_vue

