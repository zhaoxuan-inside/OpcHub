<template>
  <span
    class="persona-avatar"
    :style="{ width: size + 'px', height: size + 'px' }"
    :title="persona ? `${persona.label} · 画像头像` : '默认头像'"
    aria-hidden="true"
  >
    <svg v-if="persona" viewBox="0 0 64 64" width="100%" height="100%">
      <circle cx="32" cy="32" r="32" :fill="persona.color" />
      <g v-html="persona.glyph"></g>
    </svg>
    <span
      v-else
      class="persona-avatar-initial"
      :style="{
        background: fallbackColor,
        fontSize: Math.round(size * 0.42) + 'px',
        borderRadius: '50%',
      }"
    >
      {{ initial }}
    </span>
  </span>
</template>

<script setup>
import { computed } from 'vue';
import { PERSONA_AVATAR_MAP, fallbackColorFor } from '@/components/personaAvatarCatalog';

const props = defineProps({
  /** 内置画像头像标识；空或未收录时回退为昵称首字圆标 */
  id: { type: String, default: '' },
  /** 用于首字兜底与兜底色散列的昵称/邮箱 */
  name: { type: String, default: '' },
  /** 渲染直径（px） */
  size: { type: Number, default: 36 },
});

const persona = computed(() => PERSONA_AVATAR_MAP[props.id] || null);
const initial = computed(() => (props.name || 'M').trim().charAt(0).toUpperCase());
const fallbackColor = computed(() => fallbackColorFor(props.name));
</script>

<style scoped>
.persona-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  line-height: 1;
}
.persona-avatar svg {
  display: block;
  width: 100%;
  height: 100%;
}
.persona-avatar-initial {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: #fff;
  font-weight: 800;
}
</style>
