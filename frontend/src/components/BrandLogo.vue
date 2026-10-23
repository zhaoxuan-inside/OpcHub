<template>
  <svg
    xmlns="http://www.w3.org/2000/svg"
    :width="size"
    :height="size"
    viewBox="0 0 1024 1024"
    class="brand-logo-svg"
    style="display: inline-block; vertical-align: middle; flex-shrink: 0;"
  >
    <defs>
      <linearGradient id="sky-grad" x1="0%" y1="85%" x2="100%" y2="10%">
        <stop offset="0%" stop-color="#BFE3FF" />
        <stop offset="30%" stop-color="#8CCBFF" />
        <stop offset="65%" stop-color="#4A90D9" />
        <stop offset="100%" stop-color="#2689EC" />
      </linearGradient>

      <radialGradient id="glow-rad" cx="23%" cy="70%" r="70%">
        <stop offset="0%" stop-color="#BFE3FF" stop-opacity=".95" />
        <stop offset="48%" stop-color="#A5C8F5" stop-opacity=".45" />
        <stop offset="100%" stop-color="#A5C8F5" stop-opacity="0" />
      </radialGradient>

      <linearGradient id="sea-grad" x1="12%" y1="0%" x2="85%" y2="100%">
        <stop offset="0%" stop-color="#4A90D9" />
        <stop offset="32%" stop-color="#0071E3" />
        <stop offset="72%" stop-color="#0A4B9C" />
        <stop offset="100%" stop-color="#8CCBFF" />
      </linearGradient>

      <radialGradient id="sun-rad" cx="30%" cy="22%" r="85%">
        <stop offset="0%" stop-color="#FFFFFF" />
        <stop offset="55%" stop-color="#EAF4FF" />
        <stop offset="100%" stop-color="#A5C8F5" />
      </radialGradient>

      <linearGradient id="rim-grad" x1="0%" y1="100%" x2="100%" y2="0%">
        <stop offset="0%" stop-color="#8CCBFF" />
        <stop offset="52%" stop-color="#EAF4FF" />
        <stop offset="100%" stop-color="#2689EC" />
      </linearGradient>

      <filter id="blur-filter">
        <feGaussianBlur stdDeviation="14" />
      </filter>

      <clipPath id="logo-clip">
        <rect x="60" y="60" width="904" height="904" rx="190" />
      </clipPath>
    </defs>

    <g clip-path="url(#logo-clip)">
      <rect x="60" y="60" width="904" height="904" fill="url(#sky-grad)" />
      <rect x="60" y="60" width="904" height="904" fill="url(#glow-rad)" />

      <path
        d="M100 795 C190 355 570 130 964 70 L964 964 L60 964Z"
        fill="#2689EC"
        opacity=".17"
      />

      <path
        d="M80 120 C370 50 690 50 950 100"
        stroke="#FFFFFF"
        stroke-opacity=".45"
        stroke-width="44"
        fill="none"
        filter="url(#blur-filter)"
      />

      <circle cx="575" cy="555" r="162" fill="url(#sun-rad)" />

      <path
        d="M30 760 C310 605 680 495 1000 510 L1000 1000 L30 1000Z"
        fill="url(#sea-grad)"
      />

      <path
        d="M30 760 C310 605 680 495 1000 510"
        fill="none"
        stroke="#FFFFFF"
        stroke-opacity=".65"
        stroke-width="24"
        filter="url(#blur-filter)"
      />

      <path
        d="M30 760 C310 605 680 495 1000 510"
        fill="none"
        stroke="#FFFFFF"
        stroke-width="10"
        stroke-linecap="round"
      />

      <path
        d="M530 600 C700 655 855 750 965 915 L965 965 L530 965Z"
        fill="#174990"
        opacity=".13"
      />

      <rect
        x="72"
        y="72"
        width="880"
        height="880"
        rx="180"
        fill="none"
        stroke="#FFFFFF"
        stroke-opacity=".34"
        stroke-width="18"
      />
    </g>

    <rect
      x="60"
      y="60"
      width="904"
      height="904"
      rx="190"
      fill="none"
      stroke="url(#rim-grad)"
      stroke-width="8"
    />

    <rect
      x="69"
      y="69"
      width="886"
      height="886"
      rx="182"
      fill="none"
      stroke="#FFFFFF"
      stroke-opacity=".55"
      stroke-width="4"
    />
  </svg>
</template>

<script setup>
defineProps({
  size: {
    type: [Number, String],
    default: 24,
  },
});
</script>
