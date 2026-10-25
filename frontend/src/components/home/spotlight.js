/**
 * 卡片鼠标聚光助手：把指针坐标写入 --mouse-x/--mouse-y，
 * 供全局 .glass-card::after / .glass-box 光斑效果消费。
 */
export function trackCardSpotlight(e) {
  const rect = e.currentTarget.getBoundingClientRect();
  const x = e.clientX - rect.left;
  const y = e.clientY - rect.top;
  e.currentTarget.style.setProperty('--mouse-x', `${x}px`);
  e.currentTarget.style.setProperty('--mouse-y', `${y}px`);
}
