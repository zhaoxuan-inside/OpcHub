import { marked } from 'marked';

// Configure marked options
marked.setOptions({
  gfm: true,
  breaks: true,
});

/**
 * Callout icons are injected as HTML strings, so they use the same redrawn
 * line-icon geometry as OpcIcon.vue but as inline SVG (no Emoji).
 */
const calloutIcon = (paths) =>
  `<svg class="opc-icon" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;

const CALLOUT_ICONS = {
  NOTE: calloutIcon(
    '<path d="M9 18h6M10 21h4"/><path d="M12 2.5A6.5 6.5 0 0 0 8.1 14.2c.6.5 1 1.2 1.1 2.1h5.6c.1-.9.5-1.6 1.1-2.1A6.5 6.5 0 0 0 12 2.5Z"/><path d="M9.6 12.4c.5-1 1.3-1.5 2.4-1.5s1.9.5 2.4 1.5"/>'
  ),
  TIP: calloutIcon(
    '<path d="M12 2.5C12 7.1 7.1 12 2.5 12 7.1 12 12 16.9 12 21.5 12 16.9 16.9 12 21.5 12 16.9 12 12 7.1 12 2.5Z"/>'
  ),
  IMPORTANT: calloutIcon(
    '<path d="M13 2.5 4.5 13.5h6L10.5 21.5 20 10.5h-6.5L13 2.5Z"/>'
  ),
  WARNING: calloutIcon(
    '<path d="M12 3.2 21.5 20H2.5L12 3.2Z"/><path d="M12 9v4.6"/><circle cx="12" cy="17.2" r="0.9" fill="currentColor" stroke="none"/>'
  ),
  CAUTION: calloutIcon(
    '<path d="M8 3h8l5 5v8l-5 5H8l-5-5V8l5-5Z"/><path d="M9 12h6" stroke-width="2"/>'
  ),
};


/**
 * Enhanced Markdown parser that outputs sanitized, styled HTML
 * Supports GitHub Flavored Markdown, callouts/alerts, code blocks, and tables.
 */
export function renderMarkdown(content) {
  if (!content || typeof content !== 'string') return '';

  try {
    let rawHtml = marked.parse(content);

    // Enhance Callouts / Alert boxes like > [!NOTE], > [!TIP], > [!WARNING], > [!IMPORTANT], > [!CAUTION]
    rawHtml = rawHtml.replace(
      /<blockquote>\s*<p>\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\s*([\s\S]*?)<\/p>\s*<\/blockquote>/gi,
      (match, type, innerContent) => {
        const t = type.toUpperCase();
        const iconMap = CALLOUT_ICONS;
        const titleMap = {
          NOTE: '提示说明',
          TIP: '经验诀窍',
          IMPORTANT: '关键要点',
          WARNING: '避坑预警',
          CAUTION: '高危阻断',
        };

        return `
          <div class="md-callout md-callout-${t.toLowerCase()}">
            <div class="md-callout-header">
              <span class="md-callout-icon">${iconMap[t] || CALLOUT_ICONS.NOTE}</span>
              <span class="md-callout-title">${titleMap[t] || t}</span>
            </div>
            <div class="md-callout-body">
              <p>${innerContent.replace(/^<br\s*\/?>/, '')}</p>
            </div>
          </div>
        `.trim();
      }
    );

    // Sanitize against dangerous scripts and event handlers
    const sanitizedHtml = rawHtml
      .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
      .replace(/on\w+="[^"]*"/gi, '')
      .replace(/on\w+='[^']*'/gi, '')
      .replace(/javascript:[^"']*/gi, '');

    return sanitizedHtml;
  } catch (err) {
    console.error('Markdown parse error:', err);
    return `<p>${escapeHtml(content)}</p>`;
  }
}

/**
 * Strips Markdown syntax for clean plain text excerpts
 */
export function stripMarkdown(content) {
  if (!content) return '';
  return content
    .replace(/^#+\s+/gm, '')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/\*(.*?)\*/g, '$1')
    .replace(/~~(.*?)~~/g, '$1')
    .replace(/`{1,3}(.*?)`{1,3}/gs, '$1')
    .replace(/\[(.*?)\]\(.*?\)/g, '$1')
    .replace(/!\[(.*?)\]\(.*?\)/g, '')
    .replace(/>\s*/g, '')
    .replace(/[-*+]\s+/g, '')
    .replace(/^\d+\.\s+/gm, '')
    .replace(/\|/g, ' ')
    .replace(/\n+/g, ' ')
    .trim();
}

/**
 * Convert HTML from WYSIWYG editor to standard Markdown
 */
export function htmlToMarkdown(html) {
  if (!html) return '';

  if (typeof DOMParser === 'undefined') {
    return html
      .replace(/<h1[^>]*>(.*?)<\/h1>/gi, '\n\n# $1\n\n')
      .replace(/<h2[^>]*>(.*?)<\/h2>/gi, '\n\n## $1\n\n')
      .replace(/<h3[^>]*>(.*?)<\/h3>/gi, '\n\n### $1\n\n')
      .replace(/<strong[^>]*>(.*?)<\/strong>/gi, '**$1**')
      .replace(/<b[^>]*>(.*?)<\/b>/gi, '**$1**')
      .replace(/<em[^>]*>(.*?)<\/em>/gi, '*$1*')
      .replace(/<i[^>]*>(.*?)<\/i>/gi, '*$1*')
      .replace(/<blockquote[^>]*>([\s\S]*?)<\/blockquote>/gi, (m, c) => '\n\n> ' + c.replace(/<p[^>]*>([\s\S]*?)<\/p>/gi, '$1\n').trim().replace(/\n/g, '\n> ') + '\n\n')
      .replace(/<p[^>]*>(.*?)<\/p>/gi, '\n\n$1\n\n')
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<[^>]+>/g, '')
      .replace(/\n{3,}/g, '\n\n')
      .trim();
  }

  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');

  function walk(node) {
    if (node.nodeType === Node.TEXT_NODE) {
      return node.nodeValue;
    }

    if (node.nodeType !== Node.ELEMENT_NODE) {
      return '';
    }

    const tag = node.tagName.toLowerCase();
    const childrenText = Array.from(node.childNodes).map(walk).join('');

    switch (tag) {
      case 'h1':
        return `\n\n# ${childrenText.trim()}\n\n`;
      case 'h2':
        return `\n\n## ${childrenText.trim()}\n\n`;
      case 'h3':
        return `\n\n### ${childrenText.trim()}\n\n`;
      case 'h4':
        return `\n\n#### ${childrenText.trim()}\n\n`;
      case 'h5':
        return `\n\n##### ${childrenText.trim()}\n\n`;
      case 'h6':
        return `\n\n###### ${childrenText.trim()}\n\n`;
      case 'strong':
      case 'b':
        return childrenText ? `**${childrenText}**` : '';
      case 'em':
      case 'i':
        return childrenText ? `*${childrenText}*` : '';
      case 'u':
        return childrenText ? `<u>${childrenText}</u>` : '';
      case 's':
      case 'strike':
      case 'del':
        return childrenText ? `~~${childrenText}~~` : '';
      case 'code':
        if (node.parentElement && node.parentElement.tagName.toLowerCase() === 'pre') {
          return childrenText;
        }
        return childrenText ? `\`${childrenText}\`` : '';
      case 'pre': {
        const lang = node.getAttribute('data-lang') || '';
        return `\n\n\`\`\`${lang}\n${childrenText.trim()}\n\`\`\`\n\n`;
      }
      case 'blockquote':
        return `\n\n> ${childrenText.trim().replace(/\n/g, '\n> ')}\n\n`;
      case 'ul': {
        const items = Array.from(node.children)
          .filter(c => c.tagName.toLowerCase() === 'li')
          .map(li => {
            const isTask = li.querySelector('input[type="checkbox"]');
            if (isTask) {
              const checked = isTask.checked ? 'x' : ' ';
              const text = Array.from(li.childNodes)
                .filter(n => n !== isTask)
                .map(walk)
                .join('')
                .trim();
              return `- [${checked}] ${text}`;
            }
            return `- ${Array.from(li.childNodes).map(walk).join('').trim()}`;
          })
          .join('\n');
        return `\n\n${items}\n\n`;
      }
      case 'ol': {
        const items = Array.from(node.children)
          .filter(c => c.tagName.toLowerCase() === 'li')
          .map((li, idx) => `${idx + 1}. ${Array.from(li.childNodes).map(walk).join('').trim()}`)
          .join('\n');
        return `\n\n${items}\n\n`;
      }
      case 'p':
        return `\n\n${childrenText.trim()}\n\n`;
      case 'div':
        if (node.classList.contains('md-callout')) {
          const type = node.className.match(/md-callout-([a-z]+)/)?.[1]?.toUpperCase() || 'NOTE';
          const body = node.querySelector('.md-callout-body')?.innerText?.trim() || childrenText.trim();
          return `\n\n> [!${type}]\n> ${body.replace(/\n/g, '\n> ')}\n\n`;
        }
        return `\n${childrenText}\n`;
      case 'hr':
        return '\n\n---\n\n';
      case 'br':
        return '\n';
      case 'a': {
        const href = node.getAttribute('href') || '#';
        return `[${childrenText.trim() || href}](${href})`;
      }
      case 'img': {
        const src = node.getAttribute('src') || '';
        const alt = node.getAttribute('alt') || '图片';
        return `![${alt}](${src})`;
      }
      case 'table': {
        const rows = Array.from(node.querySelectorAll('tr'));
        if (rows.length === 0) return '';
        const result = [];
        rows.forEach((r, idx) => {
          const cells = Array.from(r.children).map(c => c.innerText.trim().replace(/\|/g, '\\|'));
          result.push(`| ${cells.join(' | ')} |`);
          if (idx === 0) {
            result.push(`| ${cells.map(() => '---').join(' | ')} |`);
          }
        });
        return `\n\n${result.join('\n')}\n\n`;
      }
      default:
        return childrenText;
    }
  }

  const raw = walk(doc.body);
  // Clean up excess newlines
  return raw.replace(/\n{3,}/g, '\n\n').trim();
}

/**
 * Basic HTML escaper
 */
function escapeHtml(str) {
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * Built-in practical brainstorm post templates
 */
export const FORUM_TEMPLATES = [
  {
    id: 'stripe-crossborder',
    title: '独立出海 · 跨境支付与合规结汇避坑实战',
    category: 'BIZ',
    content: `# 独立开发者出海支付与合规结汇避坑复盘

## 1. 背景与业务场景
- **业务类型**：一人微型 SaaS / 工具出海
- **目标市场**：北美与欧洲市场
- **支付工具**：Stripe + 万里汇 (WorldFirst) 香港企业对公账户

## 2. 踩坑与合规痛点
> [!WARNING]
> 跨境银行在流水达到 \$10,000 以上时会触发随机合规审计，若无法在 7 天内提供符合要求的人工服务协议与对账单，结算账户将被临时冷冻！

- **阻断问题 1**：个人账户直接挂载海外商业账户导致的税务稽查与风控抽检
- **阻断问题 2**：汇率波动过大造成汇损与提现手续费吞噬微利
- **阻断问题 3**：VAT 增值税代扣代缴与跨国数字税发票合规

## 3. 破局实操与解决方案
1. **公司实体搭建**：注册香港有限责任公司 + 香港本地对公商业账户
2. **三流合一凭证建立**：
   - 业务订单流（Stripe Dashboard 导出）
   - 合同履约流（在线用户 Terms of Service 电子存证）
   - 资金结算流（银行流水对账单明细）
3. **资金安全结汇链路**：
   \`\`\`
   海外买家信用卡 -> Stripe 结算 -> 香港商业账户 -> 跨境结汇通 -> 境内合规完税入账
   \`\`\`

## 4. 核心数据与收益实测
| 指标项 | 优化前 | 规范后 |
|---|---|---|
| 资金结算结算时效 | T+7 天（常被风控卡留） | T+1 日内自动结汇 |
| 综合交易损耗 | 4.8% (中间行+汇损) | 1.9% (企业合规通道) |
| 合规审查阻断率 | 35% 发生率 | 0% (已通过 2 次年检) |

> [!TIP]
> 建议每季度末及时导出 Stripe 报表与税务底稿备查，一人公司必须做好风险防线隔离！`,
  },
  {
    id: 'fullstack-architecture',
    title: '一人公司全栈开发技术选型与高并发实测',
    category: 'DEV',
    content: `# 一人公司全栈技术选型与架构复盘

## 1. 核心诉求与技术目标
作为独立超级个体，运维时间必须压缩在 5% 以下，架构必须满足**极致轻量**、**高开发吞吐**与**零专职运维**。

## 2. 技术栈清单
- **后端**：FastAPI (Python 3.12 异步) + Uvicorn
- **前端**：Vue 3 + Vite + VisionOS 液态毛玻璃设计系统
- **数据库**：PostgreSQL 16 + pgvector (配合单机 SQLite 本地高速缓存)
- **调度治理**：轻量级微内核插件流水线 + DAG 事件总线

## 3. 架构设计与避坑
\`\`\`python
# 示例：微内核合规拦截算子
async def compliance_guard_pipeline(context: dict) -> bool:
    content = context.get("content", "")
    if len(content) < 10:
        raise ValueError("正文字数不足，无法形成有效技术风暴帖")
    # 执行异步敏感词与防刷限流校验
    return True
\`\`\`

> [!NOTE]
> 永远不要在初创验证阶段引入复杂的 Kubernetes 分布式集群，单台高配云主机 + Docker Compose 足以支撑 10 万 MAU。

## 4. 经验建议与讨论点
- 欢迎各位创客就 ORM 选型（SQLAlchemy vs Tortoise）与微内核插件机制展开交流探讨！`,
  },
  {
    id: 'tax-compliance',
    title: '小规模纳税人季度免税申报与电子税务局实操指南',
    category: 'TAX',
    content: `# 2026 小规模纳税人免税申报与财税合规避坑

## 1. 适用群体
适用于年应税销售额在 500 万元以下、季度销售额在 30 万元以内的初创一人科技公司或工作室。

## 2. 申报核心避坑点
> [!IMPORTANT]
> 电子税务局填报《增值税及附加税费申报表》时，免税收入切勿误填入“应税销售额”一栏，否则税务系统将直接生成缴税凭单！

### 申报规范流程：
1. **登录新版电子税务局**：选择企业法定代表人或财务人员身份实名登录
2. **核对发票汇总数据**：确认本季度开具普票总金额未超过 30 万元限额
3. **选择减免税政策代码**：勾选“小微企业免征增值税政策”
4. **零附加税确认**：增值税免征后，城建税、教育费附加与地方教育附加同步全免

## 3. 真实核算对照表
| 项目 | 季度销售额 28 万元 | 季度销售额 35 万元 |
|---|---|---|
| 增值税征收率 | 1% (免征额内) | 1% (全额计税) |
| 应纳增值税额 | ¥0.00 | ¥3,500.00 |
| 附加税费 | ¥0.00 | ¥420.00 |
| 经营合规性 | 凭证齐全，零申报 | 需开票纳税，可抵扣进项 |

> [!TIP]
> 记得在每年 6 月 30 日前完成企业年报公示，逾期会被列入经营异常名录！`,
  },
];
