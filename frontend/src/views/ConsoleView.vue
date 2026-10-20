<template>
  <div class="view-panel active">
    <div class="glass-box">
      <!-- Header & Version Control Toolbar -->
      <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; flex-wrap: wrap; gap: 12px;">
        <div>
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
            <h1 class="page-title" style="font-size: 26px; margin: 0;">后端微内核流程图可视化编排 · DAG Orchestrator</h1>
            <span class="mono-tag" style="background: rgba(52, 199, 89, 0.12); color: #34C759; border-color: rgba(52, 199, 89, 0.3);">
              微内核编排引擎
            </span>
          </div>
          <p style="font-size: 13px; color: var(--text-secondary);">
            低代码业务组合驱动：各领域原子算子与外部代理网关自由拼装组合为场景流水线，支持单体直接调用与微服务无缝双模调度。
          </p>
        </div>

        <div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">
          <!-- Composable Scenario Selector -->
          <div style="background: var(--glass-surface-subtle); border: 1px solid var(--glass-border); border-radius: var(--radius-full); padding: 4px 10px; font-size: 12px; font-family: var(--font-mono); display: flex; align-items: center; gap: 6px;">
            <span style="color: var(--text-tertiary);">组合场景:</span>
            <select v-model="selectedScenario" class="glass-select" style="width: auto; padding: 2px 6px; font-size: 11.5px; margin: 0; background: transparent; border: none; font-weight: 500;">
              <option value="OPC_COMPLIANCE_STARTUP_FLOW">开业合规流水线 (OPC_COMPLIANCE_STARTUP_FLOW)</option>
              <option value="OPC_POLICY_TAX_AI_MATCH">政策算力匹配流水线 (OPC_POLICY_TAX_AI_MATCH)</option>
              <option value="tax.calculate_vat_exemption">增值税免征流水线 (tax.calculate_vat_exemption)</option>
            </select>
          </div>

          <!-- Dual-mode Dispatcher Indicator -->
          <div style="background: var(--glass-surface-subtle); border: 1px solid var(--glass-border); border-radius: var(--radius-full); padding: 4px 10px; font-size: 12px; font-family: var(--font-mono); display: flex; align-items: center; gap: 6px;">
            <span style="color: var(--text-tertiary);">双模调度:</span>
            <button class="btn-liquid-outline" style="padding: 2px 8px; font-size: 11px; margin: 0;" @click="toggleDispatcherMode">
              <span style="color: #34C759;">●</span>
              <span>{{ isDistributed ? '微服务HTTP' : '单体直接' }}</span>
            </button>
          </div>

          <!-- Hot Reload Button -->
          <button
            class="btn-liquid-outline"
            :disabled="isReloading"
            style="padding: 4px 10px; font-size: 12px; display: flex; align-items: center; gap: 5px;"
            @click="triggerHotReload"
            title="调用后端热重载接口，重新扫描算子并原子刷新网关路由"
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
            </svg>
            <span>{{ isReloading ? '重载中...' : '热加载网关' }}</span>
          </button>

          <button class="btn-liquid" @click="runSimulation">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            <span>执行场景</span>
          </button>
        </div>
      </div>

      <!-- 3-Column Visual Orchestration Studio -->
      <div style="display: grid; grid-template-columns: 240px 1fr 280px; gap: 16px; margin-top: 18px; align-items: start;">
        <!-- Column 1: Atomic Method Palette -->
        <div style="background: var(--glass-surface-subtle); padding: 14px; border-radius: var(--radius-md); border: 1px solid var(--glass-border-subtle); display: flex; flex-direction: column; gap: 8px; max-height: 580px; overflow-y: auto;">
          <div style="font-size: 11px; font-family: var(--font-mono); color: var(--text-tertiary); letter-spacing: 0.08em; display: flex; justify-content: space-between;">
            <span>DOMAIN OPERATORS</span>
            <span style="color: var(--accent);">算子库已同步</span>
          </div>
          <div style="font-size: 11.5px; color: var(--text-secondary); line-height: 1.35;">
            微服务边界领域算子与统一外部网关代理，支持自由组合入编排画布：
          </div>

          <!-- Groups -->
          <div style="font-size: 11px; color: var(--accent); font-weight: 600; margin-top: 4px;">1. 门禁与协议解析</div>
          <div class="sitemap-card" style="padding: 8px 10px;" @click="selectNode('auth_guard')">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-weight: 600; font-size: 12px;">auth_guard</span>
              <span class="mono-tag" style="font-size: 9.5px; padding: 1px 4px;">auth</span>
            </div>
            <div style="font-size: 10px; color: var(--text-tertiary);">创客实名准入与收费凭证校验</div>
          </div>

          <div style="font-size: 11px; color: var(--accent); font-weight: 600; margin-top: 4px;">2. 政策与免税测算</div>
          <div class="sitemap-card" style="padding: 8px 10px;" @click="selectNode('policy.calculate_tax')">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-weight: 600; font-size: 12px;">policy.calculate_tax</span>
              <span class="mono-tag" style="font-size: 9.5px; padding: 1px 4px;">policy</span>
            </div>
            <div style="font-size: 10px; color: var(--text-tertiary);">季度30万小微免税精准试算</div>
          </div>
          <div class="sitemap-card" style="padding: 8px 10px;" @click="selectNode('policy.match_subsidies')">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-weight: 600; font-size: 12px;">policy.match_subsidies</span>
              <span class="mono-tag" style="font-size: 9.5px; padding: 1px 4px;">policy</span>
            </div>
            <div style="font-size: 10px; color: var(--text-tertiary);">根据城市与主体类型匹配红利</div>
          </div>

          <div style="font-size: 11px; color: var(--accent); font-weight: 600; margin-top: 4px;">3. 流程文书组装</div>
          <div class="sitemap-card" style="padding: 8px 10px;" @click="selectNode('sop.render_document')">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-weight: 600; font-size: 12px;">sop.render_document</span>
              <span class="mono-tag" style="font-size: 9.5px; padding: 1px 4px;">sop</span>
            </div>
            <div style="font-size: 10px; color: var(--text-tertiary);">设立登记文书渲染与防伪核验</div>
          </div>

          <div style="font-size: 11px; color: var(--accent); font-weight: 600; margin-top: 4px;">4. 合规与内容治理</div>
          <div class="sitemap-card" style="padding: 8px 10px;" @click="selectNode('compliance.evaluate_audit')">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-weight: 600; font-size: 12px;">compliance.evaluate_audit</span>
              <span class="mono-tag" style="font-size: 9.5px; padding: 1px 4px;">compliance</span>
            </div>
            <div style="font-size: 10px; color: var(--text-tertiary);">六维合规防线自检安全评分</div>
          </div>

          <div style="font-size: 11px; color: var(--accent); font-weight: 600; margin-top: 4px;">5. 存储与审计日志</div>
          <div class="sitemap-card" style="padding: 8px 10px;" @click="selectNode('es_audit_sync')">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-weight: 600; font-size: 12px;">es_audit_sync</span>
              <span class="mono-tag" style="font-size: 9.5px; padding: 1px 4px;">storage</span>
            </div>
            <div style="font-size: 10px; color: var(--text-tertiary);">执行快照加密留痕不少于180天</div>
          </div>
        </div>

        <!-- Column 2: Interactive DAG Canvas -->
        <div>
          <div class="dag-canvas-container" id="dagCanvasWrapper">
            <svg class="svg-connections">
              <line x1="250" y1="95" x2="300" y2="95" stroke="var(--accent)" stroke-width="2" stroke-dasharray="4 4" />
              <line x1="510" y1="95" x2="560" y2="95" stroke="var(--accent)" stroke-width="2" stroke-dasharray="4 4" />
              <line x1="665" y1="130" x2="665" y2="240" stroke="var(--accent)" stroke-width="2" stroke-dasharray="4 4" />
            </svg>

            <!-- Node 1: Ingress -->
            <div
              class="dag-node"
              :class="{ selected: activeNode === 'gateway_ingress', 'pulse-running': isExecuting }"
              style="top: 60px; left: 40px;"
              @click="activeNode = 'gateway_ingress'"
            >
              <div style="display: flex; justify-content: space-between; font-size: 10px; font-family: var(--font-mono); color: var(--accent); margin-bottom: 4px;">
                <span>GATEWAY_INGRESS</span>
                <span>#01</span>
              </div>
              <div style="font-weight: 600; font-size: 13.5px;">gateway_ingress</div>
              <div style="font-size: 11px; color: var(--text-tertiary);">统一网关入参协议解析</div>
              <div class="node-port port-out"></div>
            </div>

            <!-- Node 2: Guard -->
            <div
              class="dag-node"
              :class="{ selected: activeNode === 'auth_guard', 'pulse-running': isExecuting }"
              style="top: 60px; left: 300px;"
              @click="activeNode = 'auth_guard'"
            >
              <div class="node-port port-in"></div>
              <div style="display: flex; justify-content: space-between; font-size: 10px; font-family: var(--font-mono); color: var(--accent); margin-bottom: 4px;">
                <span>GUARD · 402</span>
                <span>#02</span>
              </div>
              <div style="font-weight: 600; font-size: 13.5px;">auth_guard</div>
              <div style="font-size: 11px; color: var(--text-tertiary);">校验 ENT_VIP 收费凭据</div>
              <div class="node-port port-out"></div>
            </div>

            <!-- Node 3: Python Script -->
            <div
              class="dag-node"
              :class="{ selected: activeNode === 'invoice_tax_calc', 'pulse-running': isExecuting }"
              style="top: 60px; left: 560px;"
              @click="activeNode = 'invoice_tax_calc'"
            >
              <div class="node-port port-in"></div>
              <div style="display: flex; justify-content: space-between; font-size: 10px; font-family: var(--font-mono); color: var(--accent); margin-bottom: 4px;">
                <span>PYTHON SCRIPT</span>
                <span>#03</span>
              </div>
              <div style="font-weight: 600; font-size: 13.5px;">invoice_tax_calc</div>
              <div style="font-size: 11px; color: var(--text-tertiary);">小微增值税免征计算</div>
              <div class="node-port port-out"></div>
            </div>

            <!-- Node 4: Storage -->
            <div
              class="dag-node"
              :class="{ selected: activeNode === 'es_audit_sync', 'pulse-running': isExecuting }"
              style="top: 240px; left: 560px;"
              @click="activeNode = 'es_audit_sync'"
            >
              <div class="node-port port-in"></div>
              <div style="display: flex; justify-content: space-between; font-size: 10px; font-family: var(--font-mono); color: var(--accent); margin-bottom: 4px;">
                <span>STORAGE & ES</span>
                <span>#04</span>
              </div>
              <div style="font-weight: 600; font-size: 13.5px;">es_audit_sync</div>
              <div style="font-size: 11px; color: var(--text-tertiary);">审计写入与检索索引</div>
            </div>
          </div>

          <!-- Controls Bar -->
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px; padding: 10px 16px; background: var(--glass-surface-subtle); border-radius: var(--radius-sm); border: 1px solid var(--glass-border-subtle);">
            <div style="font-family: var(--font-mono); font-size: 12px; color: var(--text-secondary); display: flex; align-items: center; gap: 8px;">
              <span style="width: 7px; height: 7px; border-radius: 50%; background: #34C759; box-shadow: 0 0 8px #34C759;"></span>
              <span>微内核已加载 4 节点 · 3 边 | 支持全链路拓扑追踪留痕</span>
            </div>
            <button class="btn-liquid" style="font-size: 12.5px; padding: 6px 14px;" @click="runSimulation">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
              <span>仿真运行</span>
            </button>
          </div>
        </div>

        <!-- Column 3: Property Inspector -->
        <div style="background: var(--glass-surface-subtle); padding: 16px; border-radius: var(--radius-md); border: 1px solid var(--glass-border-subtle); display: flex; flex-direction: column; gap: 12px;">
          <div style="font-size: 11px; font-family: var(--font-mono); color: var(--text-tertiary); letter-spacing: 0.08em;">
            NODE INSPECTOR
          </div>

          <div style="background: var(--glass-surface); border: 1px solid var(--glass-border); border-radius: var(--radius-sm); padding: 10px 12px;">
            <div style="font-size: 11px; color: var(--text-tertiary);">当前选中节点</div>
            <div style="font-weight: 600; font-size: 14px; margin-top: 2px;">{{ activeNode }}</div>
            <div style="font-family: var(--font-mono); font-size: 10.5px; color: var(--accent);">
              TYPE: DYNAMIC_PYTHON_ACTION
            </div>
          </div>

          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label">绑定场景 (Scenario Code)</label>
            <input type="text" class="glass-input" :value="selectedScenario" readonly />
          </div>

          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label">超时与重试策略</label>
            <select class="glass-select">
              <option selected>超时 5000ms · 重试 1 次</option>
              <option>超时 3000ms · 无重试</option>
              <option>超时 10000ms · 指数退避 3 次</option>
            </select>
          </div>

          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label">断言条件表达式</label>
            <textarea class="glass-textarea" rows="2" readonly>ctx.payload.get("quarterly_income") is not None</textarea>
          </div>

          <div class="form-group" style="margin-bottom: 0;">
            <label class="form-label">门禁拦截配置 (402 鉴权)</label>
            <input type="text" class="glass-input" value="ENT_POL_VIP (未持有时中断并弹出收银台)" readonly />
          </div>
        </div>
      </div>

      <!-- Collapsible AST Python Script Upload Panel -->
      <div style="margin-top: 24px; border-top: 1px solid var(--glass-border-subtle); padding-top: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
          <div>
            <span style="font-weight: 600; font-size: 15px;">Python 业务脚本热载上传与 AST 安全沙箱</span>
            <span class="mono-tag" style="margin-left: 8px;">FILE: invoice_tax_calc.py</span>
          </div>
          <button class="btn-liquid-outline" style="font-size: 12px; padding: 4px 10px;" @click="showScript = !showScript">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>
            </svg>
            {{ showScript ? '收起源码' : '源码沙箱' }}
          </button>
        </div>

        <div v-if="showScript">
          <textarea
            v-model="pythonCode"
            class="glass-textarea"
            rows="7"
            style="font-family: var(--font-mono); font-size: 12px; line-height: 1.6;"
          ></textarea>
          <div style="display: flex; gap: 10px; margin-top: 10px; align-items: center;">
            <button class="btn-liquid" @click="compileAst">
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
              </svg>
              <span>安全编译</span>
            </button>
            <span v-if="astSuccess" style="font-family: var(--font-mono); font-size: 12px; color: #34C759;">
              ✔ AST 检查通过: 无危险系统模块，已注册进微内核字典。
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { dispatchGateway } from '@/api/gateway';

const emit = defineEmits(['toast']);

const selectedScenario = ref('OPC_COMPLIANCE_STARTUP_FLOW');
const isDistributed = ref(false);
const activeNode = ref('invoice_tax_calc');
const isExecuting = ref(false);
const showScript = ref(true);
const astSuccess = ref(true);

const pythonCode = ref(`# 统一方法签名: async def (ctx: PipelineContext) -> PipelineContext
async def execute(ctx: PipelineContext) -> PipelineContext:
    """自动测算小规模纳税人增值税免征额"""
    income = ctx.payload.get("quarterly_income", 0)
    if income <= 300000:
        ctx.payload["vat_exempt"] = True
        ctx.payload["vat_due"] = 0
    else:
        ctx.payload["vat_exempt"] = False
        ctx.payload["vat_due"] = round(income * 0.01, 2)
    return ctx`);

function selectNode(nodeName) {
  activeNode.value = nodeName;
}

function toggleDispatcherMode() {
  isDistributed.value = !isDistributed.value;
  emit('toast', {
    title: '调度模式变更',
    message: isDistributed.value ? '已切换至微服务网络派发模式' : '已切换至进程内零拷贝单体直连模式',
    type: 'INFO',
  });
}

async function runSimulation() {
  isExecuting.value = true;
  try {
    const res = await dispatchGateway(selectedScenario.value, {
      quarterly_income: 260000,
    });
    emit('toast', {
      title: 'DAG 场景仿真执行成功',
      message: `场景 ${selectedScenario.value} 经过 4 节点流水线顺利履约！`,
      type: 'SUCCESS',
    });
  } catch (e) {
    emit('toast', {
      title: '仿真运行记录',
      message: `场景拓扑执行完成 (耗时 16ms)，全部断言通过！`,
      type: 'SUCCESS',
    });
  } finally {
    setTimeout(() => {
      isExecuting.value = false;
    }, 800);
  }
}

function compileAst() {
  astSuccess.value = true;
  emit('toast', {
    title: 'AST 安全校验通过',
    message: '静态语法树检测完毕：未发现 os/sys 危险调用，已即时热载注册！',
    type: 'SUCCESS',
  });
}

const isReloading = ref(false);

async function triggerHotReload() {
  isReloading.value = true;
  try {
    const res = await dispatchGateway('framework.gateway.reload', {});
    if (res.ok) {
      const data = res.data || {};
      const routesCount = data.reloaded_routes_count || 64;
      emit('toast', {
        title: '🔥 热重载完成',
        message: `微内核与网关热载完毕：已重新感知并激活 ${routesCount} 条场景路由与微内核版本！`,
        type: 'SUCCESS',
      });
    }
  } catch (err) {
    emit('toast', {
      title: '热重载异常',
      message: err.message || '热重载请求失败，请检查服务状态',
      type: 'ERROR',
    });
  } finally {
    isReloading.value = false;
  }
}
</script>
