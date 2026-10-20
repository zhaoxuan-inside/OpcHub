# OpcHub 前后端低代码元数据引擎实现规范 (Low-Code Engine Spec)

> **Document Type**: Technical Component Architecture Specification  
> **Inherits**: `opchub_system_architecture.md`  
> **Target**: 解决政策、Perks、橱窗多变异构信息的高效录入、无发版渲染与敏捷上线

---

## 1. 动态卡片 Schema 定义示例 (JSON Schema Contract)

后端向前端返回业务实体时，通过带上 `ui_schema` 描述该实体卡片的呈现方式：

```json
{
  "entity_id": "pol_hz_2026_091",
  "entity_type": "policy",
  "schema_version": "v1.2",
  "ui_schema": {
    "card_type": "standard_editorial",
    "badge": {
      "type": "free",
      "text": "真金现金直补"
    },
    "header": {
      "title_field": "title",
      "meta_fields": ["issuer", "region", "deadline_countdown"]
    },
    "highlights": [
      {
        "widget": "WhitepaperQuoteWidget",
        "label": "100字白话",
        "value_field": "whitepaper_summary"
      }
    ],
    "footer": {
      "left_metric": {
        "widget": "CheckmarkTextWidget",
        "text": "门槛：高校毕业5年内"
      },
      "actions": [
        {
          "widget": "DrawerTriggerButton",
          "text": "官方解读与申报细则 →",
          "action_type": "open_drawer",
          "target_id": "pol_hz_2026_091"
        }
      ]
    }
  },
  "data": {
    "title": "大学生及青年创业一次性现金直补 ¥10,000",
    "issuer": "杭州市人社局",
    "region": "杭州市",
    "deadline_countdown": "剩 18 天截止",
    "whitepaper_summary": "毕业 5 年内创办个体工商户或科技企业，正常经营连续纳税满 6 个月即可直接申领 10,000 元现金补贴。"
  }
}
```

---

## 2. 后端 Python Pydantic 动态校验器实现模式

```python
from typing import Any, Dict
from pydantic import BaseModel, Field
import jsonschema

class BaseDynamicEntity(BaseModel):
    id: str
    entity_code: str
    status: str
    schema_version: str
    attributes: Dict[str, Any] = Field(default_factory=dict)

    def validate_against_schema(self, json_schema: Dict[str, Any]):
        """在写入 PostgreSQL JSONB 之前，强制通过元数据注册表的 JSON Schema 校验"""
        jsonschema.validate(instance=self.attributes, schema=json_schema)
```

---

## 3. 前端 Vue 3 动态卡片渲染引擎实现模式

前端通过动态组件 `<component :is="...">` 结合小部件注册表实现低代码渲染：

```vue
<!-- DynamicCardRenderer.vue -->
<template>
  <div class="card" :class="schema.card_type">
    <!-- Header -->
    <div class="card-head">
      <span class="card-title">{{ data[schema.header.title_field] }}</span>
      <BadgeWidget :type="schema.badge.type" :text="schema.badge.text" />
    </div>

    <!-- Highlights / Widgets -->
    <div v-for="(hl, idx) in schema.highlights" :key="idx">
      <component 
        :is="widgetRegistry[hl.widget]" 
        :label="hl.label" 
        :value="data[hl.value_field]" 
      />
    </div>

    <!-- Footer Actions -->
    <div class="card-footer">
      <component 
        v-if="schema.footer.left_metric"
        :is="widgetRegistry[schema.footer.left_metric.widget]" 
        :text="schema.footer.left_metric.text" 
      />
      <div class="actions">
        <component 
          v-for="(act, aIdx) in schema.footer.actions" 
          :key="aIdx"
          :is="widgetRegistry[act.widget]"
          :config="act"
          :data="data"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps } from 'vue';
import BadgeWidget from '@/components/widgets/BadgeWidget.vue';
import WhitepaperQuoteWidget from '@/components/widgets/WhitepaperQuoteWidget.vue';
import DrawerTriggerButton from '@/components/widgets/DrawerTriggerButton.vue';
import CheckmarkTextWidget from '@/components/widgets/CheckmarkTextWidget.vue';

const props = defineProps<{
  schema: any;
  data: any;
}>();

// 原子部件映射字典
const widgetRegistry: Record<string, any> = {
  BadgeWidget,
  WhitepaperQuoteWidget,
  DrawerTriggerButton,
  CheckmarkTextWidget
};
</script>
```

---

## 4. 业务敏捷收益
- **零 DDL 扩展**：新增政策类型（如算力补贴券、海外落户补贴）仅需在元数据表中增加一条 Schema 规则；
- **免发版生效**：修改或增加卡片上的按钮（如将“查看指引”改为“一键领取代金券”），直接通过后端配置生效，前端立即动态渲染新组件。
