"""Tests for Home Page (Landing Page & Content Showcase) and Unauthenticated Access Restriction.

Verifies:
1. Frontend dist bundle exists and contains the HomeView promotional showcase content.
2. Unauthenticated user restriction: HomeView is the default and only visible page for unlogged users.
3. Content showcase style elements: Bento grid, metric pillars, journey roadmap, testimonials, and content exhibition tabs.
4. Promotional message accurately describes OpcHub's capabilities (Policy Center, SOP documents, Product Showcase, Demands Marketplace, Perks).
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
      "政策中心",
      "流程文书",
      "产品橱窗",
      "需求集市",
      "生态特权",
    ]
    for kw in promotional_keywords:
        assert kw in combined_js, f"Promotional keyword '{kw}' missing from compiled frontend bundle"

    # Requirement 3: 首页的风格可以参考内容展示类平台的设计思路 (Bento grid, Exhibition, Journey)
    # 「创客心声」假证言区块已按全站 Mock 清理删除，不再作为契约指标。
    content_showcase_indicators = [
      "四大核心支柱",
      "精选展厅",
      "一人公司演进路径",
    ]
    for indicator in content_showcase_indicators:
        assert indicator in combined_js, f"Showcase element '{indicator}' missing from bundle"


def test_unauthenticated_user_access_gated_in_source():
    """Verify that unauthenticated users are restricted to the public home route.

    The shell moved from a hash/activeTab switch to vue-router in the 2026-10
    refactor, so the contract is now enforced by route meta + the navigation
    guard instead of a v-if chain in App.vue.
    """
    frontend_src = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"
    app_vue = (frontend_src / "App.vue").read_text(encoding="utf-8")
    router_js = (frontend_src / "router" / "index.js").read_text(encoding="utf-8")
    auth_js = (frontend_src / "stores" / "auth.js").read_text(encoding="utf-8")
    navbar_vue = (frontend_src / "components" / "Navbar.vue").read_text(encoding="utf-8")

    # 1. App renders the routed workspace, and the home route is public.
    assert "<RouterView" in app_vue
    assert "component: HomeView" in router_js
    assert "public: true" in router_js

    # 2. Every workspace route requires auth; the guard redirects to home + login.
    assert "requiresAuth: true" in router_js
    assert "ensureSession()" in router_js
    assert "query: { login: '1', redirect: to.fullPath }" in router_js
    assert "const requiresAuth = Boolean(to.meta.requiresAuth)" in router_js

    # 3. Session is hydrated from localStorage before the guard decides.
    assert "localStorage.getItem(TOKEN_KEY)" in auth_js
    assert "readJSON(USER_KEY)" in auth_js
    assert "export async function ensureSession" in auth_js

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
    """Verify page refresh preserves route + session without switching mode."""
    frontend_src = Path(__file__).resolve().parent.parent.parent / "frontend" / "src"
    app_vue = (frontend_src / "App.vue").read_text(encoding="utf-8")
    router_js = (frontend_src / "router" / "index.js").read_text(encoding="utf-8")
    auth_js = (frontend_src / "stores" / "auth.js").read_text(encoding="utf-8")
    main_js = (frontend_src / "main.js").read_text(encoding="utf-8")

    # 1. Role + user session are persisted; the route itself is the URL now.
    assert "localStorage.setItem(ROLE_KEY" in auth_js
    assert "localStorage.setItem(USER_KEY" in auth_js
    assert "localStorage.getItem(ROLE_KEY)" in auth_js
    assert "readJSON(USER_KEY)" in auth_js
    assert "localStorage.getItem(TOKEN_KEY)" in auth_js

    # 2. HTML5 history routing: a hard refresh on /policies/:id serves the SPA.
    assert "createWebHistory()" in router_js
    assert "path: '/policies/:id?'" in router_js
    assert "path: '/forum/:id?'" in router_js
    assert "spa_history_fallback" in (frontend_src.parent / "server.py").read_text(encoding="utf-8")

    # 3. Existing selected mode is preserved by the auth store, not overwritten on refresh.
    assert "saved === 'ADMIN' || saved === 'MAKER'" in auth_js
    assert "persistRole(saved)" in auth_js

    # 4. Session is hydrated before mount to avoid a login flash.
    assert "ensureSession(true)" in app_vue
    assert "migrateLegacyHash()" in main_js

