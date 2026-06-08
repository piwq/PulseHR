<script setup>
import { ref } from 'vue'
import PhCard from './PhCard.vue'
import PhCountUp from './PhCountUp.vue'
import PhIcon from './PhIcon.vue'

defineProps({
  label:     { type: String, required: true },
  hint:      { type: String, default: undefined },
  unit:      { type: String, default: undefined },
  scaleHint: { type: String, default: undefined },
  to:        { type: Number, required: true },
  dec:       { type: Number, default: 0 },
  plus:      { type: Boolean, default: false },
  deltaDir:  { type: String, default: undefined },
  deltaText: { type: String, default: undefined },
})

const show = ref(false)
</script>

<template>
  <PhCard hover :pad="false">
    <div class="card__pad" style="padding:16px 18px">

      <div class="kpi__label">
        {{ label }}
        <span v-if="scaleHint" class="mono xs" style="color:var(--text-faint)">{{ scaleHint }}</span>
        <span v-if="hint" class="hint-wrap"
          @mouseenter="show = true" @mouseleave="show = false"
          @focus="show = true"     @blur="show = false">
          <button class="hint-btn" tabindex="0" aria-label="Подробнее">i</button>
          <div v-show="show" class="hint-box" role="tooltip">{{ hint }}</div>
        </span>
      </div>
      <div class="kpi__val">
        <PhCountUp :to="to" :dec="dec" :plus="plus" />
        <span v-if="unit" class="unit">{{ unit }}</span>
      </div>
      <div v-if="deltaText" class="kpi__delta" :class="deltaDir === 'up' ? 'delta-up' : 'delta-down'">
        <PhIcon :name="deltaDir === 'up' ? 'up' : 'down'" :size="12" :stroke="1.7" />{{ deltaText }}
      </div>
    </div>
  </PhCard>
</template>

<style scoped>
.hint-wrap {
  display: inline-flex; position: relative;
  vertical-align: middle; margin-left: 5px;
}
.hint-btn {
  width: 18px; height: 18px; border-radius: 50%;
  border: 1px solid var(--line-strong);
  background: var(--bg-raised); color: var(--text-muted);
  font-size: 11px; font-style: italic; font-family: Georgia, serif;
  font-weight: 700; line-height: 1; cursor: default;
  display: flex; align-items: center; justify-content: center;
  transition: border-color .12s, color .12s;
}
.hint-wrap:hover .hint-btn {
  border-color: var(--accent); color: var(--accent-text);
}
.hint-box {
  position: absolute; right: 0; bottom: calc(100% + 8px);
  width: 220px; padding: 10px 12px;
  background: var(--bg-base); border: 1px solid var(--line-strong);
  border-radius: 10px; box-shadow: 0 8px 24px rgba(0,0,0,.35);
  font-size: 12px; line-height: 1.5; color: var(--text-secondary);
  font-family: var(--font); font-style: normal; font-weight: 400;
  pointer-events: none; z-index: 500;
}
/* Arrow */
.hint-box::after {
  content: ''; position: absolute;
  bottom: -5px; right: 6px;
  width: 8px; height: 8px;
  background: var(--bg-base);
  border-right: 1px solid var(--line-strong);
  border-bottom: 1px solid var(--line-strong);
  transform: rotate(45deg);
}
</style>
