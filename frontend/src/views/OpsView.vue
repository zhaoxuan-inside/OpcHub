<template>
  <div class="view-panel active">
    <!-- Header -->
    <div class="glass-box" style="padding: 24px 32px 18px; margin-bottom: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div>
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
            <h1 class="page-title" style="font-size: 26px; margin: 0;">运营数据大盘与三端视窗</h1>
            <span class="mono-tag" style="background: rgba(52, 199, 89, 0.12); color: #34C759; border-color: rgba(52, 199, 89, 0.3);">
              实时遥测引擎
            </span>
          </div>
          <p style="font-size: 13px; color: var(--text-secondary);">
            实时监测 DAU、UV、PV 与微内核网关吞吐；三端视觉风格严格保持 Apple VisionOS 液态毛玻璃一致性。
          </p>
        </div>
        <span class="mono-tag" style="background: var(--accent-glass); color: var(--accent);">
          TELEMETRY · ACTIVE
        </span>
      </div>

      <!-- KPI Grid 6 -->
      <div class="kpi-grid-6" style="margin-top: 20px;">
        <div class="kpi-card">
          <div class="kpi-label"><span>DAU 日活跃创客</span><span style="color: #34C759;">●</span></div>
          <div class="kpi-value">14,820</div>
          <div class="kpi-delta up">↑ 18.2% 周同比</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label"><span>UV 独立访客</span><span style="color: #34C759;">●</span></div>
          <div class="kpi-value">89,540</div>
          <div class="kpi-delta up">↑ 24.5% 周同比</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label"><span>PV 页面浏览总量</span><span style="color: #34C759;">●</span></div>
          <div class="kpi-value">628,400</div>
          <div class="kpi-delta up">↑ 31.0% 周同比</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label"><span>微内核网关平均延迟</span><span style="color: #34C759;">●</span></div>
          <div class="kpi-value" style="color: #34C759;">14 ms</div>
          <div class="kpi-delta up">P99 稳定</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label"><span>创客 7 日留存率</span><span style="color: #34C759;">●</span></div>
          <div class="kpi-value">48.5%</div>
          <div class="kpi-delta up">↑ 3.2% 优化</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label"><span>商机委托撮合履约</span><span style="color: #34C759;">●</span></div>
          <div class="kpi-value">99.8%</div>
          <div class="kpi-delta up">担保无纠纷</div>
        </div>
      </div>
    </div>

    <!-- Section B: Cross-Platform Client Simulators -->
    <div class="glass-box" style="padding: 18px 24px 14px; margin-bottom: 20px;">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
        <div>
          <h2 style="font-size: 18px; font-weight: 600;">移动端纯信息展示页面 (iOS & Android)</h2>
          <p style="font-size: 12.5px; color: var(--text-secondary); margin-top: 2px;">
            三端视觉风格严格保持 Apple VisionOS 液态毛玻璃一致性；移动双端专为创客设计为轻量高密度的「只读信息流与运营播报」，绝不堆砌复杂编辑工具。
          </p>
        </div>
        <span class="mono-tag" style="background: var(--accent-glass); color: var(--accent);">
          STYLE: VISIONOS SPECULAR IDENTICAL
        </span>
      </div>
    </div>

    <div class="device-showcase-container">
      <!-- 1. iOS Client Simulator -->
      <div class="device-frame-ios">
        <div class="device-status-bar">
          <span>9:41</span>
          <div class="dynamic-island">
            <span style="color: #34C759;">● 运营中</span>
            <span style="color: #aaa;">DAU 14.8k</span>
          </div>
          <div style="display: flex; align-items: center; gap: 4px;">
            <span>5G</span>
            <span style="color: #34C759;">100%</span>
          </div>
        </div>

        <div style="padding: 8px 16px 10px; border-bottom: 1px solid var(--glass-border-subtle); display: flex; justify-content: space-between; align-items: center;">
          <div>
            <div style="font-size: 10px; font-family: var(--font-mono); color: var(--accent);">OPCHUB · IOS CLIENT</div>
            <div style="font-size: 16px; font-weight: 700; letter-spacing: -0.01em;">创客头条速递</div>
          </div>
          <span class="mono-tag" style="font-size: 10px; padding: 2px 6px;">纯信息展示</span>
        </div>

        <div class="mobile-content-stream">
          <div class="mobile-card-liquid" style="background: linear-gradient(135deg, rgba(0, 113, 227, 0.12), rgba(52, 199, 89, 0.08));">
            <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 6px;">
              <span style="font-weight: 600; color: var(--text-primary);">今日运营大盘简报</span>
              <span style="color: #34C759; font-family: var(--font-mono);">LIVE</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); text-align: center; gap: 6px;">
              <div>
                <div style="font-size: 9.5px; color: var(--text-tertiary);">DAU 日活</div>
                <div style="font-size: 14px; font-weight: 700; color: var(--text-primary);">14,820</div>
              </div>
              <div>
                <div style="font-size: 9.5px; color: var(--text-tertiary);">UV 独立访客</div>
                <div style="font-size: 14px; font-weight: 700; color: var(--text-primary);">89,540</div>
              </div>
              <div>
                <div style="font-size: 9.5px; color: var(--text-tertiary);">7日留存</div>
                <div style="font-size: 14px; font-weight: 700; color: #34C759;">48.5%</div>
              </div>
            </div>
          </div>

          <div class="mobile-card-liquid">
            <div style="display: flex; justify-content: space-between; font-size: 10.5px; margin-bottom: 4px;">
              <span class="mono-tag" style="background: rgba(0,113,227,0.15); color: var(--accent); padding: 1px 5px;">政策快讯</span>
              <span style="color: var(--text-tertiary);">10 分钟前</span>
            </div>
            <div style="font-size: 13px; font-weight: 600; line-height: 1.4; margin-bottom: 4px;">
              2026 一人公司工商年报与增值税免征额度最新细则出台
            </div>
            <p style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.45;">
              针对季度营收 30 万元以下免税政策的电子税务局申报实录，附常见报错与退税处理指引。
            </p>
          </div>

          <div class="mobile-card-liquid">
            <div style="display: flex; justify-content: space-between; font-size: 10.5px; margin-bottom: 4px;">
              <span class="mono-tag" style="background: rgba(52,199,89,0.15); color: #34C759; padding: 1px 5px;">外包商机</span>
              <span style="color: #34C759; font-weight: 600;">预算 ¥25,000</span>
            </div>
            <div style="font-size: 13px; font-weight: 600; line-height: 1.4; margin-bottom: 4px;">
              跨境电商独立站 AI 客服系统定制开发
            </div>
            <p style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.45;">
              需对接 Shopify 与 WhatsApp API，要求独立创客团队交付，工期 3 周。
            </p>
          </div>
        </div>

        <div class="mobile-tabbar-liquid">
          <div class="mobile-tab-item active">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>
            <span>首页</span>
          </div>
          <div class="mobile-tab-item">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 2a10 10 0 0 1 10 10"/></svg>
            <span>政策</span>
          </div>
          <div class="mobile-tab-item">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
            <span>风暴</span>
          </div>
        </div>
      </div>

      <!-- 2. Android Client Simulator -->
      <div class="device-frame-android">
        <div class="device-status-bar">
          <span>10:08</span>
          <div class="android-camera-hole"></div>
          <div style="display: flex; align-items: center; gap: 4px;">
            <span>WiFi</span>
            <span style="color: #34C759;">98%</span>
          </div>
        </div>

        <div style="padding: 8px 16px 10px; border-bottom: 1px solid var(--glass-border-subtle); display: flex; justify-content: space-between; align-items: center;">
          <div>
            <div style="font-size: 10px; font-family: var(--font-mono); color: #34C759;">OPCHUB · ANDROID APP</div>
            <div style="font-size: 16px; font-weight: 700; letter-spacing: -0.01em;">创客资讯视窗</div>
          </div>
          <span class="mono-tag" style="font-size: 10px; padding: 2px 6px;">纯信息展示</span>
        </div>

        <div class="mobile-content-stream">
          <div class="mobile-card-liquid" style="background: linear-gradient(135deg, rgba(52, 199, 89, 0.12), rgba(0, 113, 227, 0.08));">
            <div style="display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 6px;">
              <span style="font-weight: 600; color: var(--text-primary);">平台服务与算力晴雨表</span>
              <span style="color: #34C759; font-family: var(--font-mono);">ONLINE</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-top: 4px;">
              <div>
                <div style="font-size: 9.5px; color: var(--text-tertiary);">全网今日 PV</div>
                <div style="font-size: 17px; font-weight: 700; color: var(--text-primary);">62.8 万</div>
              </div>
              <div style="text-align: right;">
                <div style="font-size: 9.5px; color: var(--text-tertiary);">网关平均延迟</div>
                <div style="font-size: 14px; font-weight: 600; color: #34C759;">14ms (正常)</div>
              </div>
            </div>
          </div>

          <div class="mobile-card-liquid">
            <div style="display: flex; justify-content: space-between; font-size: 10.5px; margin-bottom: 4px;">
              <span class="mono-tag" style="background: rgba(52,199,89,0.15); color: #34C759; padding: 1px 5px;">算力特权</span>
              <span style="color: #34C759;">价值 $5,000</span>
            </div>
            <div style="font-size: 13px; font-weight: 600; line-height: 1.4; margin-bottom: 4px;">
              AWS Activate 创客计划新一批额度开放
            </div>
            <p style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.45;">
              为平台认证超级个体提供 2 年期 $5,000 云服务积分与高级企业架构师一对一技术支持。
            </p>
          </div>

          <div class="mobile-card-liquid">
            <div style="display: flex; justify-content: space-between; font-size: 10.5px; margin-bottom: 4px;">
              <span class="mono-tag" style="background: rgba(0,113,227,0.15); color: var(--accent); padding: 1px 5px;">产品橱窗</span>
              <span style="color: var(--accent); font-weight: 600;">TOP 1 打榜</span>
            </div>
            <div style="font-size: 13px; font-weight: 600; line-height: 1.4; margin-bottom: 4px;">
              InkFlow AI · 超级个体沉浸写作引擎
            </div>
            <p style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.45;">
              集成分镜排版、多语言出海分发与本地 Markdown 导出，本周创客点赞数 428 次。
            </p>
          </div>
        </div>

        <div class="mobile-tabbar-liquid">
          <div class="mobile-tab-item active">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
            <span>看板</span>
          </div>
          <div class="mobile-tab-item">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
            <span>资讯</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
</script>
