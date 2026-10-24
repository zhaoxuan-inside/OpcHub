<template>
  <form :id="id" class="publish-form" @submit.prevent="$emit('submit')">
    <PublishNotice v-if="showNotice" />

    <section v-for="(group, gi) in groups" :key="gi" class="publish-section">
      <h2 v-if="group.title" class="publish-section-title">{{ group.title }}</h2>
      <div class="publish-grid">
        <div
          v-for="field in visibleFields(group.fields)"
          :key="field.key"
          class="publish-field"
          :class="{ 'span-2': field.span === 2 || field.type === 'richtext' }"
        >
          <label v-if="field.type !== 'richtext'" class="publish-label" :for="`${id}-${field.key}`">
            {{ field.label }}
            <span v-if="field.required" class="req">*</span>
          </label>
          <div v-else class="publish-label publish-label-block">
            {{ field.label }}
            <span v-if="field.required" class="req">*</span>
          </div>

          <RichEditor
            v-if="field.type === 'richtext'"
            :id="`${id}-${field.key}`"
            v-model="model[field.key]"
            :placeholder="field.placeholder"
            :min-height="field.minHeight || 300"
          />

          <IconPicker
            v-else-if="field.type === 'icon'"
            :id="`${id}-${field.key}`"
            v-model="model[field.key]"
          />

          <textarea
            v-else-if="field.type === 'textarea'"
            :id="`${id}-${field.key}`"
            v-model="model[field.key]"
            :rows="field.rows || 4"
            :required="field.required"
            :maxlength="field.maxlength"
            class="glass-input publish-textarea"
            :placeholder="field.placeholder"
          ></textarea>

          <select
            v-else-if="field.type === 'select'"
            :id="`${id}-${field.key}`"
            v-model="model[field.key]"
            class="glass-input glass-select"
          >
            <option
              v-for="opt in field.options"
              :key="optionValue(opt)"
              :value="optionValue(opt)"
            >
              {{ optionLabel(opt) }}
            </option>
          </select>

          <input
            v-else
            :id="`${id}-${field.key}`"
            v-model="model[field.key]"
            :type="field.type || 'text'"
            :required="field.required"
            :placeholder="field.placeholder"
            :min="field.min"
            :max="field.max"
            :step="field.step"
            :maxlength="field.maxlength"
            class="glass-input"
          />

          <span v-if="field.hint" class="publish-hint">{{ field.hint }}</span>
        </div>
      </div>
    </section>
  </form>
</template>

<script setup>
import { computed } from 'vue';
import PublishNotice from '@/components/PublishNotice.vue';
import RichEditor from '@/components/editor/RichEditor.vue';
import IconPicker from '@/components/editor/IconPicker.vue';

const props = defineProps({
  id: { type: String, required: true },
  model: { type: Object, required: true },
  fields: { type: Array, required: true },
  showNotice: { type: Boolean, default: true },
});

defineEmits(['submit']);

const groups = computed(() => {
  const result = [];
  let current = { title: '', fields: [] };
  for (const item of props.fields) {
    if (item.section) {
      if (item.visible && !item.visible(props.model)) continue;
      if (current.fields.length) result.push(current);
      current = { title: item.section, fields: [] };
    } else {
      current.fields.push(item);
    }
  }
  if (current.fields.length) result.push(current);
  return result;
});

function visibleFields(fields) {
  return fields.filter((field) => !field.visible || field.visible(props.model));
}

function optionValue(opt) {
  return typeof opt === 'object' && opt !== null ? opt.value : opt;
}

function optionLabel(opt) {
  return typeof opt === 'object' && opt !== null ? opt.label : opt;
}
</script>

<style scoped>
.publish-form {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.publish-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.publish-section-title {
  margin: 0;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--text-tertiary);
  text-transform: uppercase;
}

.publish-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 18px;
}

.publish-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.publish-field.span-2 {
  grid-column: 1 / -1;
}

.publish-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  line-height: 1.4;
}

.publish-label-block {
  display: block;
}

.publish-hint {
  font-size: 11px;
  line-height: 1.5;
  color: var(--text-tertiary);
}

.publish-textarea {
  min-height: 96px;
  line-height: 1.6;
  resize: vertical;
}

@media (max-width: 720px) {
  .publish-grid {
    grid-template-columns: 1fr;
  }
}
</style>
