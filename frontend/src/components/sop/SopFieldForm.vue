<template>
  <!--
    A single fillable field of a document node.
    Renders the label, the plain-language help, a copyable example and the common
    pitfalls, so a first-time maker can fill it without reading regulatory prose.
  -->
  <div class="sop-field" :class="{ 'sop-field-invalid': showError }">
    <div class="sop-field-head">
      <label class="sop-field-label" :for="fieldId">
        {{ field.label }}
        <span v-if="field.required" class="sop-field-req">*</span>
      </label>
      <span v-if="field.source" class="sop-field-source">{{ field.source }}</span>
    </div>

    <!-- Select -->
    <select
      v-if="field.type === 'select'"
      :id="fieldId"
      class="sop-field-input"
      :value="modelValue"
      @change="$emit('update:modelValue', $event.target.value)"
    >
      <option value="" disabled>请选择{{ field.label }}</option>
      <option v-for="opt in field.options || []" :key="opt" :value="opt">{{ opt }}</option>
    </select>

    <!-- Textarea -->
    <textarea
      v-else-if="field.type === 'text'"
      :id="fieldId"
      class="sop-field-input sop-field-textarea"
      rows="3"
      :placeholder="field.example || ''"
      :value="modelValue"
      @input="$emit('update:modelValue', $event.target.value)"
    ></textarea>

    <!-- Number / currency -->
    <input
      v-else-if="field.type === 'number' || field.type === 'currency'"
      :id="fieldId"
      class="sop-field-input"
      type="number"
      :step="field.type === 'currency' ? '100' : '1'"
      :min="field.type === 'currency' ? '0' : undefined"
      :placeholder="field.example || ''"
      :value="modelValue"
      @input="$emit('update:modelValue', $event.target.value === '' ? '' : Number($event.target.value))"
    />

    <!-- Date -->
    <input
      v-else-if="field.type === 'date'"
      :id="fieldId"
      class="sop-field-input"
      type="date"
      :value="modelValue"
      @input="$emit('update:modelValue', $event.target.value)"
    />

    <!-- String -->
    <input
      v-else
      :id="fieldId"
      class="sop-field-input"
      type="text"
      :placeholder="field.example || ''"
      :value="modelValue"
      @input="$emit('update:modelValue', $event.target.value)"
    />

    <!-- Plain-language guidance -->
    <div v-if="field.help" class="sop-field-help">{{ field.help }}</div>

    <div v-if="field.example" class="sop-field-example">
      <span class="sop-field-example-label">示例</span>
      <button type="button" class="sop-field-example-value" @click="useExample">
        {{ field.example }}
      </button>
    </div>

    <ul v-if="(field.pitfalls || []).length" class="sop-field-pitfalls">
      <li v-for="(pitfall, idx) in field.pitfalls" :key="idx">{{ pitfall }}</li>
    </ul>

    <p v-if="showError" class="sop-field-error">请填写{{ field.label }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  field: { type: Object, required: true },
  modelValue: { type: [String, Number], default: '' },
  showError: { type: Boolean, default: false },
});

const emit = defineEmits(['update:modelValue']);

const fieldId = computed(() => `sop-field-${props.field.key}`);

function useExample() {
  emit('update:modelValue', props.field.example);
}
</script>

<style scoped>
.sop-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sop-field-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
}

.sop-field-label {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-primary);
}

.sop-field-req {
  color: var(--status-danger);
  margin-left: 2px;
}

.sop-field-source {
  font-size: 11px;
  color: var(--text-tertiary);
  font-family: var(--font-mono, monospace);
}

.sop-field-input {
  width: 100%;
  padding: 9px 12px;
  border-radius: var(--radius-sm, 10px);
  border: 1px solid var(--glass-border-subtle);
  background: var(--glass-surface-subtle);
  color: var(--text-primary);
  font-size: 13px;
  box-sizing: border-box;
  outline: none;
  transition: all 0.2s ease;
}

.sop-field-input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 8px var(--accent-glow);
  background: var(--glass-surface);
}

.sop-field-textarea {
  resize: vertical;
  line-height: 1.6;
  font-family: inherit;
}

.sop-field-invalid .sop-field-input {
  border-color: var(--status-danger);
}

.sop-field-help {
  font-size: 12px;
  line-height: 1.6;
  color: var(--text-secondary);
}

.sop-field-example {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 11.5px;
}

.sop-field-example-label {
  flex-shrink: 0;
  color: var(--text-tertiary);
  font-family: var(--font-mono, monospace);
  font-size: 10.5px;
  padding: 1px 6px;
  border-radius: 5px;
  background: var(--glass-surface-subtle);
  border: 1px solid var(--glass-border-subtle);
}

.sop-field-example-value {
  border: none;
  background: none;
  padding: 0;
  cursor: pointer;
  color: var(--accent);
  font-size: 11.5px;
  text-align: left;
  line-height: 1.5;
  text-decoration: underline;
  text-decoration-style: dotted;
  text-underline-offset: 2px;
}

.sop-field-pitfalls {
  margin: 2px 0 0;
  padding-left: 16px;
  font-size: 11.5px;
  line-height: 1.6;
  color: var(--status-warning);
}

.sop-field-error {
  margin: 0;
  font-size: 11.5px;
  color: var(--status-danger);
}
</style>
