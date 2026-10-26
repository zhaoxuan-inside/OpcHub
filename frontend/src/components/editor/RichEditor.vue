<template>
  <div class="rich-editor" :class="{ 'is-empty': isEmpty && !focused, 'is-auto-grow': autoGrow }">
    <!-- Slim icon-only toolbar: formatting groups on the left, mode + count on the right -->
    <div class="re-toolbar" role="toolbar">
      <div class="re-tool-groups">
        <div class="re-group">
          <button type="button" class="re-btn" title="撤销 (Ctrl+Z)" @click.prevent="undo">
            <svg viewBox="0 0 24 24"><path d="M3 7v6h6"/><path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"/></svg>
          </button>
          <button type="button" class="re-btn" title="重做 (Ctrl+Y)" @click.prevent="redo">
            <svg viewBox="0 0 24 24"><path d="M21 7v6h-6"/><path d="M3 17a9 9 0 0 1 9-9 9 9 0 0 1 6 2.3L21 13"/></svg>
          </button>
        </div>

        <span class="re-divider"></span>

        <div class="re-group">
          <div class="re-menu-wrap" @keydown.esc.stop="closeMenus">
            <button type="button" class="re-btn re-btn-wide" title="标题 / 正文" @click.prevent="toggleMenu('heading')">
              <span class="re-heading-label">{{ headingLabel }}</span>
              <svg viewBox="0 0 24 24" class="re-caret"><polyline points="6 9 12 15 18 9"/></svg>
            </button>
            <div v-if="openMenu === 'heading'" class="re-menu">
              <button type="button" class="re-menu-item" @click.prevent="applyHeading('p')">正文</button>
              <button type="button" class="re-menu-item" @click.prevent="applyHeading('h1')">标题一</button>
              <button type="button" class="re-menu-item" @click.prevent="applyHeading('h2')">标题二</button>
              <button type="button" class="re-menu-item" @click.prevent="applyHeading('h3')">标题三</button>
            </div>
          </div>
        </div>

        <span class="re-divider"></span>

        <div class="re-group">
          <button type="button" class="re-btn" title="加粗 (Ctrl+B)" @click.prevent="format('bold')">
            <svg viewBox="0 0 24 24" class="sw2"><path d="M6 4h8a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"/><path d="M6 12h9a4 4 0 0 1 4 4 4 4 0 0 1-4 4H6z"/></svg>
          </button>
          <button type="button" class="re-btn" title="斜体 (Ctrl+I)" @click.prevent="format('italic')">
            <svg viewBox="0 0 24 24" class="sw2"><line x1="19" y1="4" x2="10" y2="4"/><line x1="14" y1="20" x2="5" y2="20"/><line x1="15" y1="4" x2="9" y2="20"/></svg>
          </button>
          <button type="button" class="re-btn" title="下划线 (Ctrl+U)" @click.prevent="format('underline')">
            <svg viewBox="0 0 24 24" class="sw2"><path d="M6 3v7a6 6 0 0 0 6 6 6 6 0 0 0 6-6V3"/><line x1="4" y1="21" x2="20" y2="21"/></svg>
          </button>
          <button type="button" class="re-btn" title="删除线" @click.prevent="format('strikethrough')">
            <svg viewBox="0 0 24 24" class="sw2"><line x1="5" y1="12" x2="19" y2="12"/><path d="M16 6C16 4 14 3 12 3C9 3 8 5 8 7C8 13 16 11 16 17C16 19 14 21 12 21C9 21 8 20 8 18"/></svg>
          </button>
          <button type="button" class="re-btn" title="行内代码" @click.prevent="format('inlineCode')">
            <svg viewBox="0 0 24 24"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
          </button>
        </div>

        <span class="re-divider"></span>

        <div class="re-group">
          <button type="button" class="re-btn" title="无序列表" @click.prevent="format('ul')">
            <svg viewBox="0 0 24 24"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
          </button>
          <button type="button" class="re-btn" title="有序列表" @click.prevent="format('ol')">
            <svg viewBox="0 0 24 24"><line x1="10" y1="6" x2="21" y2="6"/><line x1="10" y1="12" x2="21" y2="12"/><line x1="10" y1="18" x2="21" y2="18"/><path d="M4 6h1v4"/><path d="M4 10h2"/><path d="M6 18H4c0-1 2-2 2-3s-1-1.5-2-1"/></svg>
          </button>
          <button type="button" class="re-btn" title="待办清单" @click.prevent="format('tasklist')">
            <svg viewBox="0 0 24 24"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
          </button>
          <button type="button" class="re-btn" title="引用块" @click.prevent="format('quote')">
            <svg viewBox="0 0 24 24"><path d="M3 21c3 0 7-1 7-8V5c0-1.25-.756-2.017-2-2H4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"/><path d="M15 21c3 0 7-1 7-8V5c0-1.25-.757-2.017-2-2h-4c-1.25 0-2 .75-2 1.972V11c0 1.25.75 2 2 2 1 0 1 0 1 1v1c0 1-1 2-2 2s-1 .008-1 1.031V20c0 1 0 1 1 1z"/></svg>
          </button>
          <button type="button" class="re-btn" title="分割线" @click.prevent="format('hr')">
            <svg viewBox="0 0 24 24"><line x1="3" y1="12" x2="21" y2="12"/></svg>
          </button>
        </div>

        <span class="re-divider"></span>

        <div class="re-group">
          <button type="button" class="re-btn" title="代码块" @click.prevent="format('codeblock')">
            <svg viewBox="0 0 24 24"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="m10 10-2 2 2 2"/><path d="m14 14 2-2-2-2"/></svg>
          </button>
          <button type="button" class="re-btn" title="表格" @click.prevent="insertTable">
            <svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/><path d="M9 3v18"/><path d="M15 3v18"/></svg>
          </button>
          <button type="button" class="re-btn" title="超链接" @click.prevent="insertLink">
            <svg viewBox="0 0 24 24"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/></svg>
          </button>
          <div class="re-menu-wrap" @keydown.esc.stop="closeMenus">
            <button type="button" class="re-btn re-btn-accent" title="高亮提示框" @click.prevent="toggleMenu('callout')">
              <OpcIcon name="bulb" :size="14" />
            </button>
            <div v-if="openMenu === 'callout'" class="re-menu">
              <button
                v-for="c in CALLOUTS"
                :key="c.key"
                type="button"
                class="re-menu-item"
                @click.prevent="insertCallout(c.key)"
              >
                <span class="re-menu-dot" :style="{ background: c.color }"></span>
                {{ c.label }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div class="re-toolbar-right">
        <span class="re-count">{{ wordCount }} 字</span>
        <div class="re-mode-switch">
          <button
            type="button"
            class="re-mode-btn"
            :class="{ active: mode === 'wysiwyg' }"
            title="富文本模式"
            @click.prevent="setMode('wysiwyg')"
          >
            <OpcIcon name="pen" :size="13" />
          </button>
          <button
            type="button"
            class="re-mode-btn"
            :class="{ active: mode === 'markdown' }"
            title="Markdown 源码模式"
            @click.prevent="setMode('markdown')"
          >
            <OpcIcon name="code" :size="13" />
          </button>
        </div>
      </div>
    </div>

    <!-- Editing surface: WYSIWYG by default, Markdown source on demand -->
    <div class="re-canvas">
      <div
        v-show="mode === 'wysiwyg'"
        ref="surfaceRef"
        class="re-surface markdown-rendered-content"
        contenteditable="true"
        :data-placeholder="placeholder"
        @input="onWysiwygInput"
        @focus="focused = true"
        @blur="onWysiwygBlur"
        @keydown="onSurfaceKeydown"
      ></div>
      <textarea
        v-show="mode === 'markdown'"
        ref="textareaRef"
        v-model="proxy"
        class="re-textarea"
        :placeholder="placeholder"
        spellcheck="false"
        @focus="focused = true"
        @blur="focused = false"
        @keydown="onTextareaKeydown"
      ></textarea>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { htmlToMarkdown, renderMarkdown } from '@/utils/markdown';

/**
 * RichEditor —— 全平台统一的发布正文编辑器。
 *
 * 设计约束：
 * - 单一数据源：v-model 永远是 Markdown 字符串，与论坛/文书现有存储格式一致；
 * - 双模式：默认富文本（contenteditable），可切 Markdown 源码；
 * - 工具栏仅图标 + tooltip，正文画布占据页面心智，无图片/上传入口
 *   （平台素材只允许内置图标，由 IconPicker 承担）。
 */

const CALLOUTS = [
  { key: 'TIP', label: '经验诀窍', color: 'var(--status-success, #34c759)' },
  { key: 'WARNING', label: '避坑预警', color: 'var(--status-warning, #ff9f0a)' },
  { key: 'NOTE', label: '提示说明', color: 'var(--accent, #0071e3)' },
  { key: 'IMPORTANT', label: '关键要点', color: 'var(--status-danger, #ff3b30)' },
  { key: 'CAUTION', label: '高危阻断', color: 'var(--text-primary)' },
];

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '开始撰写正文……支持标题、列表、代码块、表格与高亮提示框。' },
  minHeight: { type: Number, default: 320 },
  startMode: { type: String, default: 'wysiwyg' }, // 'wysiwyg' | 'markdown'
  // Grow with content (no inner scrollbar) and dock the toolbar while the page scrolls.
  autoGrow: { type: Boolean, default: false },
});

const emit = defineEmits(['update:modelValue']);

const mode = ref(props.startMode);
const focused = ref(false);
const openMenu = ref('');
const surfaceRef = ref(null);
const textareaRef = ref(null);

// Markdown-mode history (WYSIWYG relies on the browser's native undo).
const historyStack = ref([]);
const historyIndex = ref(-1);

const proxy = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
});

const wordCount = computed(() => props.modelValue.replace(/\s+/g, '').length);
const isEmpty = computed(() => !props.modelValue || !props.modelValue.trim());

const headingLabel = computed(() => (mode.value === 'markdown' ? 'MD' : '标题'));

/* ------------------------- WYSIWYG ↔ Markdown sync ------------------------- */

function surfaceMarkdown() {
  return surfaceRef.value ? htmlToMarkdown(surfaceRef.value.innerHTML) : '';
}

function renderSurface() {
  if (surfaceRef.value) {
    surfaceRef.value.innerHTML = renderMarkdown(props.modelValue);
  }
}

function syncFromModel() {
  if (mode.value === 'wysiwyg' && surfaceRef.value && surfaceMarkdown() !== props.modelValue) {
    renderSurface();
  }
}

function onWysiwygInput() {
  // Browsers leave a stray <br>/<p> behind when the user deletes everything;
  // clear it so the placeholder re-appears.
  if (surfaceRef.value) {
    const html = surfaceRef.value.innerHTML;
    if (html === '<br>' || html === '<div><br></div>') {
      surfaceRef.value.innerHTML = '';
    }
  }
  const md = surfaceMarkdown();
  if (md !== props.modelValue) {
    recordHistory(md);
    emit('update:modelValue', md);
  }
}

function onWysiwygBlur() {
  focused.value = false;
  onWysiwygInput();
}

function fitTextarea() {
  const ta = textareaRef.value;
  if (!props.autoGrow || !ta || mode.value !== 'markdown') return;
  ta.style.height = 'auto';
  ta.style.height = `${ta.scrollHeight}px`;
}

watch(() => props.modelValue, () => {
  syncFromModel();
  nextTick(fitTextarea);
});

watch(mode, (m) => {
  closeMenus();
  if (m === 'wysiwyg') {
    nextTick(renderSurface);
  } else {
    nextTick(() => {
      fitTextarea();
      textareaRef.value?.focus();
    });
  }
});

onMounted(() => {
  if (mode.value === 'wysiwyg') renderSurface();
  recordHistory(props.modelValue);
});

/* ------------------------------- Formatting -------------------------------- */

function recordHistory(snapshot) {
  const value = snapshot ?? props.modelValue;
  if (historyStack.value[historyIndex.value] === value) return;
  historyStack.value = historyStack.value.slice(0, historyIndex.value + 1);
  historyStack.value.push(value);
  historyIndex.value = historyStack.value.length - 1;
}

function undo() {
  if (mode.value === 'wysiwyg') {
    document.execCommand('undo', false, null);
    onWysiwygInput();
    return;
  }
  if (historyIndex.value > 0) {
    historyIndex.value--;
    emit('update:modelValue', historyStack.value[historyIndex.value]);
  }
}

function redo() {
  if (mode.value === 'wysiwyg') {
    document.execCommand('redo', false, null);
    onWysiwygInput();
    return;
  }
  if (historyIndex.value < historyStack.value.length - 1) {
    historyIndex.value++;
    emit('update:modelValue', historyStack.value[historyIndex.value]);
  }
}

function setMode(next) {
  if (mode.value === next) return;
  if (mode.value === 'wysiwyg') onWysiwygBlur();
  recordHistory();
  mode.value = next;
}

/* Menus */

function toggleMenu(name) {
  openMenu.value = openMenu.value === name ? '' : name;
}

function closeMenus() {
  openMenu.value = '';
}

function onSurfaceKeydown(e) {
  if (e.key === 'Escape') closeMenus();
  if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === 'z') {
    e.preventDefault();
    undo();
  } else if ((e.ctrlKey || e.metaKey) && (e.key.toLowerCase() === 'y' || (e.key.toLowerCase() === 'z' && e.shiftKey))) {
    e.preventDefault();
    redo();
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
    e.preventDefault();
    format('bold');
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'i') {
    e.preventDefault();
    format('italic');
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'u') {
    e.preventDefault();
    format('underline');
  }
}

function onTextareaKeydown(e) {
  if (e.key === 'Tab') {
    e.preventDefault();
    const ta = e.target;
    const { selectionStart: start, selectionEnd: end, value } = ta;
    emit('update:modelValue', value.substring(0, start) + '  ' + value.substring(end));
    nextTick(() => {
      ta.selectionStart = ta.selectionEnd = start + 2;
    });
  } else if ((e.ctrlKey || e.metaKey) && !e.shiftKey && e.key.toLowerCase() === 'z') {
    // Native textarea undo already works; keep history stack in sync lazily.
    nextTick(() => recordHistory());
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
    e.preventDefault();
    format('bold');
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'i') {
    e.preventDefault();
    format('italic');
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'u') {
    e.preventDefault();
    format('underline');
  }
}

/* Markdown-mode text surgery is handled inline in applyMarkdownFormat */

/* WYSIWYG command path + shared entry */

function format(type) {
  closeMenus();
  if (mode.value === 'wysiwyg') {
    execWysiwyg(type);
    return;
  }
  applyMarkdownFormat(type);
}

function execWysiwyg(type) {
  const commands = {
    bold: 'bold',
    italic: 'italic',
    underline: 'underline',
    strikethrough: 'strikeThrough',
    ul: 'insertUnorderedList',
    ol: 'insertOrderedList',
  };

  if (commands[type]) {
    document.execCommand(commands[type], false, null);
  } else if (type === 'h1' || type === 'h2' || type === 'h3') {
    document.execCommand('formatBlock', false, `<${type}>`);
  } else if (type === 'p') {
    document.execCommand('formatBlock', false, '<p>');
  } else if (type === 'quote') {
    document.execCommand('formatBlock', false, '<blockquote>');
  } else if (type === 'hr') {
    document.execCommand('insertHorizontalRule', false, null);
  } else if (type === 'inlineCode') {
    const sel = window.getSelection();
    if (sel && sel.rangeCount) {
      const range = sel.getRangeAt(0);
      const code = document.createElement('code');
      code.innerText = sel.toString() || 'code';
      range.deleteContents();
      range.insertNode(code);
    }
  } else if (type === 'codeblock') {
    const sel = window.getSelection();
    if (sel && sel.rangeCount) {
      const range = sel.getRangeAt(0);
      const pre = document.createElement('pre');
      const code = document.createElement('code');
      code.innerText = sel.toString() || '// 代码块';
      pre.appendChild(code);
      range.deleteContents();
      range.insertNode(pre);
    }
  } else {
    return;
  }
  onWysiwygInput();
}

function applyMarkdownFormat(type) {
  const value = props.modelValue;
  const ta = textareaRef.value;
  const start = ta?.selectionStart ?? value.length;
  const end = ta?.selectionEnd ?? value.length;
  const selected = value.substring(start, end);
  const before = value.substring(0, start);
  const after = value.substring(end);

  let replacement = '';
  let cursor = 0;

  switch (type) {
    case 'bold': replacement = `**${selected || '粗体文本'}**`; cursor = selected ? replacement.length : 2; break;
    case 'italic': replacement = `*${selected || '斜体文本'}*`; cursor = selected ? replacement.length : 1; break;
    case 'underline': replacement = `<u>${selected || '下划线文本'}</u>`; cursor = selected ? replacement.length : 3; break;
    case 'strikethrough': replacement = `~~${selected || '删除线文本'}~~`; cursor = selected ? replacement.length : 2; break;
    case 'inlineCode': replacement = `\`${selected || 'code'}\``; cursor = selected ? replacement.length : 1; break;
    case 'h1': replacement = `# ${selected || '标题内容'}\n`; cursor = replacement.length; break;
    case 'h2': replacement = `## ${selected || '标题内容'}\n`; cursor = replacement.length; break;
    case 'h3': replacement = `### ${selected || '标题内容'}\n`; cursor = replacement.length; break;
    case 'p': replacement = `${selected}\n`; cursor = replacement.length; break;
    case 'ul': replacement = `\n- ${selected || '列表项'}\n`; cursor = replacement.length; break;
    case 'ol': replacement = `\n1. ${selected || '列表项'}\n`; cursor = replacement.length; break;
    case 'tasklist': replacement = `\n- [ ] ${selected || '待办事项'}\n`; cursor = replacement.length; break;
    case 'quote': replacement = `\n> ${selected || '引用内容'}\n`; cursor = replacement.length; break;
    case 'hr': replacement = `\n\n---\n\n`; cursor = replacement.length; break;
    case 'codeblock': replacement = `\n\`\`\`\n${selected || '// 代码内容'}\n\`\`\`\n`; cursor = replacement.length; break;
    default: return;
  }

  emit('update:modelValue', before + replacement + after);
  recordHistory();
  nextTick(() => {
    if (ta) {
      ta.focus();
      ta.setSelectionRange(start + cursor, start + cursor);
    }
  });
}

function applyHeading(level) {
  closeMenus();
  format(level === 'p' ? 'p' : level);
}

function insertLink() {
  closeMenus();
  const url = prompt('链接地址：', 'https://');
  if (!url) return;
  const text = prompt('链接文字（可选）：', url.replace(/^https?:\/\//, '')) || url;
  const md = `[${text}](${url})`;

  if (mode.value === 'wysiwyg') {
    const sel = window.getSelection();
    if (sel && sel.rangeCount) {
      const range = sel.getRangeAt(0);
      const a = document.createElement('a');
      a.href = url;
      a.innerText = text;
      range.deleteContents();
      range.insertNode(a);
    }
    onWysiwygInput();
    return;
  }
  insertRawMd(md);
}

function insertRawMd(md) {
  const ta = textareaRef.value;
  const value = props.modelValue;
  const at = ta?.selectionStart ?? value.length;
  emit('update:modelValue', value.substring(0, at) + md + value.substring(at));
  recordHistory();
}

function insertTable() {
  closeMenus();
  const md = '\n\n| 项目 | 说明 | 备注 |\n|---|---|---|\n| 示例行 | 双击填写 | 可增删行 |\n\n';
  if (mode.value === 'wysiwyg') {
    document.execCommand('insertHTML', false, renderMarkdown(md));
    onWysiwygInput();
    return;
  }
  insertRawMd(md);
}

function insertCallout(type) {
  closeMenus();
  const md = `\n\n> [!${type}]\n> 在这里写下需要高亮提醒读者的关键内容。\n\n`;
  if (mode.value === 'wysiwyg') {
    document.execCommand('insertHTML', false, renderMarkdown(md));
    onWysiwygInput();
    return;
  }
  insertRawMd(md);
}

function focusEditor() {
  if (mode.value === 'wysiwyg') surfaceRef.value?.focus();
  else textareaRef.value?.focus();
}

defineExpose({ focusEditor });
</script>

<style scoped>
.rich-editor {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-md);
  background: var(--glass-surface-subtle);
  overflow: hidden;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.rich-editor:focus-within {
  border-color: rgba(0, 113, 227, 0.45);
  box-shadow: 0 0 0 3px rgba(0, 113, 227, 0.08);
}

/* ------------------------------- Toolbar ---------------------------------- */

.re-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 5px 8px;
  border-bottom: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface);
  flex-wrap: wrap;
}

.re-tool-groups {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-wrap: wrap;
}

.re-group {
  display: flex;
  align-items: center;
  gap: 2px;
}

.re-divider {
  width: 1px;
  height: 16px;
  background: var(--glass-border);
  margin: 0 5px;
}

.re-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  min-width: 27px;
  height: 27px;
  padding: 0 5px;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.re-btn:hover {
  background: var(--glass-surface-hover);
  color: var(--text-primary);
}

.re-btn svg {
  width: 14px;
  height: 14px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.re-btn svg.sw2 {
  stroke-width: 2.3;
}

.re-btn svg.re-caret {
  width: 10px;
  height: 10px;
  stroke-width: 2.4;
}

.re-btn-accent {
  color: var(--accent);
}

.re-btn-accent:hover {
  color: var(--accent);
  background: var(--accent-glass);
}

.re-btn-wide {
  padding: 0 8px;
}

.re-heading-label {
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
}

/* Dropdown menus (heading / callout) */

.re-menu-wrap {
  position: relative;
}

.re-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  min-width: 132px;
  padding: 6px;
  border-radius: var(--radius-sm, 10px);
  border: 1px solid var(--glass-border);
  background: var(--glass-surface-solid, #fff);
  box-shadow: var(--glass-shadow-hover, 0 12px 32px rgba(0, 0, 0, 0.14));
  display: flex;
  flex-direction: column;
  gap: 2px;
  z-index: 60;
  animation: re-menu-in 0.16s ease;
}

@keyframes re-menu-in {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}

.re-menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border: none;
  border-radius: 7px;
  background: transparent;
  color: var(--text-primary);
  font-size: 12.5px;
  text-align: left;
  cursor: pointer;
  white-space: nowrap;
}

.re-menu-item:hover {
  background: var(--accent-glass);
  color: var(--accent);
}

.re-menu-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* Right side: count + mode switch */

.re-toolbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.re-count {
  font-size: 11px;
  color: var(--text-tertiary);
  font-family: var(--font-mono, monospace);
  white-space: nowrap;
}

.re-mode-switch {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 2px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.045);
}

[data-theme='dark'] .re-mode-switch {
  background: rgba(255, 255, 255, 0.07);
}

.re-mode-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 24px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text-tertiary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.re-mode-btn.active {
  background: var(--glass-surface-solid, #fff);
  color: var(--accent);
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
}

/* -------------------------------- Canvas ---------------------------------- */

.re-canvas {
  display: flex;
  min-height: v-bind("minHeight + 'px'");
}

.re-surface {
  flex: 1;
  padding: 18px 20px 22px;
  min-height: v-bind("minHeight + 'px'");
  outline: none;
  overflow-y: auto;
  max-height: 640px;
  cursor: text;
}

.re-surface:empty::before {
  content: attr(data-placeholder);
  color: var(--text-tertiary);
  pointer-events: none;
  display: block;
  font-style: italic;
}

.re-textarea {
  flex: 1;
  min-height: v-bind("minHeight + 'px'");
  max-height: 640px;
  padding: 16px 20px;
  border: none;
  outline: none;
  resize: vertical;
  background: transparent;
  color: var(--text-primary);
  font-family: var(--font-mono, monospace);
  font-size: 13.5px;
  line-height: 1.7;
}

/* ------------------------------ Auto-grow -------------------------------- */

/* `clip` (not hidden) keeps the rounded corners without becoming a scroll
   container, which would otherwise pin the sticky toolbar to the editor itself. */
.rich-editor.is-auto-grow {
  overflow: clip;
}

.is-auto-grow .re-toolbar {
  position: sticky;
  top: var(--create-sticky-top, 0px);
  z-index: 5;
  padding: 6px 10px;
  background: var(--glass-surface-solid);
  border-radius: calc(var(--radius-md) - 1px) calc(var(--radius-md) - 1px) 0 0;
}

.is-auto-grow .re-surface {
  max-height: none;
  overflow: visible;
  padding: 20px 24px 28px;
  line-height: 1.75;
}

.is-auto-grow .re-textarea {
  max-height: none;
  overflow: hidden;
  resize: none;
  padding: 20px 24px 28px;
}

/* Keep rendered surface typography compact inside the editor */
.re-surface h1:first-child,
.re-surface h2:first-child,
.re-surface h3:first-child,
.re-surface p:first-child {
  margin-top: 0;
}

@media (max-width: 720px) {
  .re-toolbar {
    padding: 5px 6px;
  }

  .re-count {
    display: none;
  }

  /* The page header wraps to several rows on small screens, so its height is unknown. */
  .is-auto-grow .re-toolbar {
    position: static;
  }

  .is-auto-grow .re-surface,
  .is-auto-grow .re-textarea {
    padding: 16px 16px 22px;
  }
}
</style>
