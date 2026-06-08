<script setup>
// Inline stroke icon set on a 16px grid (ported 1:1 from the design prototype).
const ICONS = {
  grid:   'M2 2h5v5H2zM9 2h5v5H9zM2 9h5v5H2zM9 9h5v5H9z',
  trend:  'M2 12l3.5-4 2.5 2L13 4',
  survey: 'M3 2h10v12l-5-2.5L3 14z',
  alert:  'M8 2l6 11H2zM8 7v3M8 11.5h.01',
  clock:  'M8 2a6 6 0 100 12A6 6 0 008 2zM8 5v3l2 1',
  bell:   'M4 7a4 4 0 018 0c0 3 1 4 1 4H3s1-1 1-4zM6.5 13a1.5 1.5 0 003 0',
  lock:   'M3 7h10v6H3zM5.5 7V5a2.5 2.5 0 015 0v2',
  arrow:  'M3 8h9M8.5 4l4 4-4 4',
  check:  'M3 8.5l3 3 7-7',
  refresh:'M13 8a5 5 0 11-1.5-3.5M13 2v3h-3',
  up:     'M6 10V2M3 5l3-3 3 3',
  down:   'M6 2v8M3 7l3 3 3-3',
  info:   'M8 2a6 6 0 100 12A6 6 0 008 2zM8 7.5v3M8 5h.01',
  x:      'M4 4l8 8M12 4l-8 8',
  user:   'M8 8a2.5 2.5 0 100-5 2.5 2.5 0 000 5zM3 14a5 5 0 0110 0',
  mail:   'M2 4h12v8H2zM2 4l6 4 6-4',
  logout: 'M6 14H3V2h3M10 11l3-3-3-3M13 8H6',
  eye:    'M1 8s2.5-5 7-5 7 5 7 5-2.5 5-7 5-7-5-7-5zM8 10a2 2 0 100-4 2 2 0 000 4',
  copy:   'M5 2h7v9H5zM3 5H2v9h7v-2',
  search: 'M6.5 11a4.5 4.5 0 100-9 4.5 4.5 0 000 9zM11 11l2.5 2.5',
  dots:   'M4 8h.01M8 8h.01M12 8h.01',
  archive:'M2 4h12v2H2zM3 6l1 8h8l1-8M6 10h4',
  finish: 'M3 8l3 3 7-7M3 14h10',
  spark:  'M8 2l1.6 3.8L13.5 7l-3.9 1.2L8 12l-1.6-3.8L2.5 7l3.9-1.2zM12.5 11l.6 1.4 1.4.6-1.4.6-.6 1.4-.6-1.4-1.4-.6 1.4-.6z',
}

defineProps({
  name: { type: String, required: true },
  size: { type: [Number, String], default: 16 },
  stroke: { type: [Number, String], default: 1.5 },
  fill: { type: String, default: 'none' },
})
</script>

<template>
  <svg :width="size" :height="size" viewBox="0 0 16 16" :fill="fill"
       stroke="currentColor" :stroke-width="stroke" stroke-linecap="round"
       stroke-linejoin="round" aria-hidden="true">
    <path :d="ICONS[name] || ''" />
  </svg>
</template>
