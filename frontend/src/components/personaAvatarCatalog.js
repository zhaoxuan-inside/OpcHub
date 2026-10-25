/**
 * 内置画像头像目录（20 种常见创客用户画像 · 人物头像）
 *
 * 风格对齐 Notion 内置头像：扁平人像 —— 柔和底色 + 圆脸 + 发型/胡须/眼镜/帽饰/服饰组合，
 * 每个画像是一个「人」，而非职业图标。全部为内联 SVG（64x64 视窗），零外部图片依赖。
 * glyph 绘制顺序：颈 → 躯干 → 耳 → 头 → 五官 → 发型/帽饰 → 配饰。
 */
export const PERSONA_AVATARS = [
  {
    id: 'dev',
    label: '独立开发者',
    color: '#7B8CFF',
    glyph: '<rect x="29" y="35" width="6" height="9" rx="2.5" fill="#F2C9A4"/><path d="M13 64 c0-10.5 8.5-15.5 19-15.5 s19 5 19 15.5 Z" fill="#46507A"/><circle cx="20" cy="27" r="2.1" fill="#F2C9A4"/><circle cx="44" cy="27" r="2.1" fill="#F2C9A4"/><circle cx="32" cy="26.5" r="12.5" fill="#F2C9A4"/><circle cx="27.2" cy="26.5" r="1.7" fill="#33383F"/><circle cx="36.8" cy="26.5" r="1.7" fill="#33383F"/><path d="M28.6 31.4 q3.4 2.6 6.8 0" fill="none" stroke="#33383F" stroke-width="1.7" stroke-linecap="round"/><path d="M20.2 24.8 c-0.4-8.4 4.6-13 11.8-13 s12.2 4.6 11.8 13 c-2.6-4.2-6.4-6-11.8-6 s-9.2 1.8-11.8 6 Z" fill="#2E2A28"/><circle cx="27.2" cy="26.6" r="3.9" fill="none" stroke="#33383F" stroke-width="1.5"/><circle cx="36.8" cy="26.6" r="3.9" fill="none" stroke="#33383F" stroke-width="1.5"/><path d="M31.1 26.2 h1.8 M23.3 25.4 l-3-0.8 M40.7 25.4 l3-0.8" fill="none" stroke="#33383F" stroke-width="1.5" stroke-linecap="round"/>',
  },
  {
    id: 'designer',
    label: '产品设计师',
    color: '#FF8A7A',
    glyph: '<rect x="29" y="35" width="6" height="9" rx="2.5" fill="#D19B6E"/><path d="M13 64 c0-10.5 8.5-15.5 19-15.5 s19 5 19 15.5 Z" fill="#F2E7DC"/><circle cx="20" cy="27" r="2.1" fill="#D19B6E"/><circle cx="44" cy="27" r="2.1" fill="#D19B6E"/><circle cx="20" cy="30.5" r="1.3" fill="#E5B84B"/><circle cx="44" cy="30.5" r="1.3" fill="#E5B84B"/><circle cx="32" cy="26.5" r="12.5" fill="#D19B6E"/><circle cx="27.2" cy="26.5" r="1.7" fill="#33383F"/><circle cx="36.8" cy="26.5" r="1.7" fill="#33383F"/><path d="M28.6 31.4 q3.4 2.6 6.8 0" fill="none" stroke="#33383F" stroke-width="1.7" stroke-linecap="round"/><path d="M20.2 24.8 c-0.4-8.4 4.6-13 11.8-13 s12.2 4.6 11.8 13 c-2.6-4.2-6.4-6-11.8-6 s-9.2 1.8-11.8 6 Z" fill="#4A3728"/><circle cx="32" cy="10.2" r="4.2" fill="#4A3728"/>',
  },
  {
    id: 'writer',
    label: '内容创作者',
    color: '#E8A33D',
    glyph: '<rect x="29" y="35" width="6" height="9" rx="2.5" fill="#E8B48C"/><path d="M13 64 c0-10.5 8.5-15.5 19-15.5 s19 5 19 15.5 Z" fill="#6B4F3A"/><circle cx="20" cy="27" r="2.1" fill="#E8B48C"/><circle cx="44" cy="27" r="2.1" fill="#E8B48C"/><circle cx="32" cy="26.5" r="12.5" fill="#E8B48C"/><circle cx="27.2" cy="26.5" r="1.7" fill="#33383F"/><circle cx="36.8" cy="26.5" r="1.7" fill="#33383F"/><path d="M28.6 31.4 q3.4 2.6 6.8 0" fill="none" stroke="#33383F" stroke-width="1.7" stroke-linecap="round"/><path d="M20.2 24.6 c-0.3-8.2 4.7-12.6 11.8-12.6 s12.1 4.4 11.8 12.6 c-3.8-5-8.2-6.4-12.6-5.4 c-1.4 2.6-4 3.4-6.2 2.6 c-1.8-0.6-3.4 0.4-4.8 2.8 Z" fill="#4A3728"/><path d="M22.6 29.5 c0.8 6.8 4.8 9.6 9.4 9.6 s8.6-2.8 9.4-9.6 c-2.2 3-5.4 4.2-9.4 4.2 s-7.2-1.2-9.4-4.2 Z" fill="#4A3728"/>',
  },
  {
    id: 'founder',
    label: '创业者',
    color: '#6FCF97',
    glyph: '<rect x="29" y="35" width="6" height="9" rx="2.5" fill="#E8B48C"/><path d="M13 64 c0-10.5 8.5-15.5 19-15.5 s19 5 19 15.5 Z" fill="#2F3B4A"/><circle cx="20" cy="27" r="2.1" fill="#E8B48C"/><circle cx="44" cy="27" r="2.1" fill="#E8B48C"/><circle cx="32" cy="26.5" r="12.5" fill="#E8B48C"/><circle cx="27.2" cy="26.5" r="1.7" fill="#33383F"/><circle cx="36.8" cy="26.5" r="1.7" fill="#33383F"/><path d="M28.6 31.4 q3.4 2.6 6.8 0" fill="none" stroke="#33383F" stroke-width="1.7" stroke-linecap="round"/><path d="M20.2 24.8 c-0.4-8.4 4.6-13 11.8-13 s12.2 4.6 11.8 13 c-2.6-4.2-6.4-6-11.8-6 s-9.2 1.8-11.8 6 Z" fill="#2E2A28"/><path d="M22.6 29.5 c0.8 6.8 4.8 9.6 9.4 9.6 s8.6-2.8 9.4-9.6 c-2.2 3-5.4 4.2-9.4 4.2 s-7.2-1.2-9.4-4.2 Z" fill="#2E2A28"/>',
  },
  {
    id: 'ecommerce',
    label: '电商卖家',
    color: '#B58CFF',
    glyph: '<rect x="29" y="35" width="6" height="9" rx="2.5" fill="#B07A4F"/><path d="M13 64 c0-10.5 8.5-15.5 19-15.5 s19 5 19 15.5 Z" fill="#E8E3DC"/><circle cx="32" cy="26.5" r="12.5" fill="#B07A4F"/><circle cx="27.2" cy="26.5" r="1.7" fill="#26221F"/><circle cx="36.8" cy="26.5" r="1.7" fill="#26221F"/><path d="M28.6 31.4 q3.4 2.6 6.8 0" fill="none" stroke="#26221F" stroke-width="1.7" stroke-linecap="round"/><circle cx="24.2" cy="30" r="1.9" fill="#D98A6E" opacity="0.55"/><circle cx="39.8" cy="30" r="1.9" fill="#D98A6E" opacity="0.55"/><path d="M19.6 25 c-0.3-8.6 4.8-13 12.4-13 s12.7 4.4 12.4 13 v13.5 a3 3 0 0 1 -6 0 v-12.8 h-12.8 v12.8 a3 3 0 0 1 -6 0 Z" fill="#2E2A28"/>',
  },
  {
    id: 'consultant',
    label: '咨询顾问',
    color: '#4FA3D9',
    glyph: '<rect x="29" y="35" width="6" height="9" rx="2.5" fill="#F2C9A4"/><path d="M13 64 c0-10.5 8.5-15.5 19-15.5 s19 5 19 15.5 Z" fill="#4A4A55"/><circle cx="20" cy="27" r="2.1" fill="#F2C9A4"/><circle cx="44" cy="27" r="2.1" fill="#F2C9A4"/><circle cx="32" cy="26.5" r="12.5" fill="#F2C9A4"/><circle cx="27.2" cy="26.5" r="1.7" fill="#33383F"/><circle cx="36.8" cy="26.5" r="1.7" fill="#33383F"/><path d="M28.6 31.4 q3.4 2.6 6.8 0" fill="none" stroke="#33383F" stroke-width="1.7" stroke-linecap="round"/><path d="M20.2 24.6 c-0.3-8.2 4.7-12.6 11.8-12.6 s12.1 4.4 11.8 12.6 c-3.8-5-8.2-6.4-12.6-5.4 c-1.4 2.6-4 3.4-6.2 2.6 c-1.8-0.6-3.4 0.4-4.8 2.8 Z" fill="#B9BDC4"/><circle cx="27.2" cy="26.6" r="3.9" fill="none" stroke="#33383F" stroke-width="1.5"/><circle cx="36.8" cy="26.6" r="3.9" fill="none" stroke="#33383F" stroke-width="1.5"/><path d="M31.1 26.2 h1.8 M23.3 25.4 l-3-0.8 M40.7 25.4 l3-0.8" fill="none" stroke="#33383F" stroke-width="1.5" stroke-linecap="round"/>',
  },
  {
    id: 'photographer',
    label: '摄影师',
    color: '#607387',
    glyph: '<rect x="29" y="35" width="6" height="9" rx="2.5" fill="#D19B6E"/><path d="M13 64 c0-10.5 8.5-15.5 19-15.5 s19 5 19 15.5 Z" fill="#37414D"/><circle cx="20" cy="27" r="2.1" fill="#D19B6E"/><circle cx="44" cy="27" r="2.1" fill="#D19B6E"/><circle cx="32" cy="26.5" r="12.5" fill="#D19B6E"/><circle cx="27.2" cy="26.5" r="1.7" fill="#2A2622"/><circle cx="36.8" cy="26.5" r="1.7" fill="#2A2622"/><path d="M28.6 32.2 q3.4 2.6 6.8 0" fill="none" stroke="#2A2622" stroke-width="1.7" stroke-linecap="round"/><path d="M20.8 23.2 c-0.2-7.6 4.5-11.4 11.2-11.4 s11.4 3.8 11.2 11.4 c-3-3.4-6.6-4.8-11.2-4.8 s-8.2 1.4-11.2 4.8 Z" fill="#4A3728"/><path d="M28.4 29.4 q3.6-1.6 7.2 0 q-1.2 1.9-3.6 1.3 q-2.4 0.6-3.6-1.3 Z" fill="#4A3728"/>',
  },
  {
    id: 'illustrator',
    label: '插画师',
    color: '#FF7BAC',
    glyph: '<rect x="29" y="35" width="6" height="9" rx="2.5" fill="#F2C9A4"/><path d="M13 64 c0-10.5 8.5-15.5 19-15.5 s19 5 19 15.5 Z" fill="#7A3A55"/><circle cx="20" cy="27" r="2.1" fill="#F2C9A4"/><circle cx="44" cy="27" r="2.1" fill="#F2C9A4"/><circle cx="20" cy="30.5" r="1.3" fill="#E5B84B"/><circle cx="44" cy="30.5" r="1.3" fill="#E5B84B"/><circle cx="32" cy="26.5" r="12.5" fill="#F2C9A4"/><circle cx="27.2" cy="26.5" r="1.7" fill="#33383F"/><circle cx="36.8" cy="26.5" r="1.7" fill="#33383F"/><path d="M28.6 31.4 q3.4 2.6 6.8 0" fill="none" stroke="#33383F" stroke-width="1.7" stroke-linecap="round"/><circle cx="24.2" cy="30" r="1.9" fill="#F0997F" opacity="0.5"/><circle cx="39.8" cy="30" r="1.9" fill="#F0997F" opacity="0.5"/><path d="M19.9 23.8 c-0.3-8 4.7-12 12.1-12 s12.4 4 12.1 12 Z" fill="#A34A2E"/>',
  },
  {
    id: 'video',
    label: '视频博主',
    color: '#E4586B',
    glyph: '<rect x="29" y="35" width="6" height="9" rx="2.5" fill="#E8B48C"/><path d="M13 64 c0-10.5 8.5-15.5 19-15.5 s19 5 19 15.5 Z" fill="#3A3A3A"/><circle cx="20" cy="27" r="2.1" fill="#E8B48C"/><circle cx="44" cy="27" r="2.1" fill="#E8B48C"/><circle cx="32" cy="26.5" r="12.5" fill="#E8B48C"/><circle cx="27.2" cy="26.5" r="1.7" fill="#33383F"/><circle cx="36.8" cy="26.5" r="1.7" fill="#33383F"/><path d="M28.6 31.4 q3.4 2.6 6.8 0" fill="none" stroke="#33383F" stroke-width="1.7" stroke-linecap="round"/><path d="M20.6 21.8 c0-7.4 4.8-11.2 11.4-11.2 s11.4 3.8 11.4 11.2 Z" fill="#E3B25C"/><rect x="19.4" y="20.2" width="25.2" height="4.6" rx="2.3" fill="#C89244"/><circle cx="32" cy="8.6" r="2.6" fill="#C89244"/>',
  },
  {
    id: 'musician',
    label: '音乐人',
    color: '#8E7CFF',
    glyph: '<rect x="29" y="35" width="6" height="9" rx="2.5" fill="#8D5A3B"/><path d="M13 64 c0-10.5 8.5-15.5 19-15.5 s19 5 19 15.5 Z" fill="#F2E9DC"/><circle cx="20" cy="27" r="2.1" fill="#8D5A3B"/><circle cx="44" cy="27" r="2.1" fill="#8D5A3B"/><circle cx="20" cy="30.5" r="1.3" fill="#E5B84B"/><circle cx="44" cy="30.5" r="1.3" fill="#E5B84B"/><circle cx="32" cy="26.5" r="12.5" fill="#8D5A3B"/><circle cx="27.2" cy="26.5" r="1.7" fill="#241F1C"/><circle cx="36.8" cy="26.5" r="1.7" fill="#241F1C"/><path d="M28.6 31.4 q3.4 2.6 6.8 0" fill="none" stroke="#241F1C" stroke-width="1.7" stroke-linecap="round"/><circle cx="23.5" cy="19" r="3.4" fill="#3A3340"/><circle cx="28.5" cy="15" r="3.6" fill="#3A3340"/><circle cx="35.5" cy="15" r="3.6" fill="#3A3340"/><circle cx="40.5" cy="19" r="3.4" fill="#3A3340"/><circle cx="21.6" cy="23.8" r="3" fill="#3A3340"/><circle cx="42.4" cy="23.8" r="3" fill="#3A3340"/>',
  },
  {
    id: 'teacher',
    label: '知识讲师',
    color: '#3E8E7E',
    glyph: '<rect x="29" y="35" width="6" height="9" rx="2.5" fill="#E8B48C"/><path d="M13 64 c0-10.5 8.5-15.5 19-15.5 s19 5 19 15.5 Z" fill="#546A5F"/><circle cx="20" cy="27" r="2.1" fill="#E8B48C"/><circle cx="44" cy="27" r="2.1" fill="#E8B48C"/><circle cx="32" cy="26.5" r="12.5" fill="#E8B48C"/><circle cx="27.2" cy="26.5" r="1.7" fill="#33383F"/><circle cx="36.8" cy="26.5" r="1.7" fill="#33383F"/><path d="M28.6 31.4 q3.4 2.6 6.8 0" fill="none" stroke="#33383F" stroke-width="1.7" stroke-linecap="round"/><path d="M20.2 24.8 c-0.4-8.4 4.6-13 11.8-13 s12.2 4.6 11.8 13 c-2.6-4.2-6.4-6-11.8-6 s-9.2 1.8-11.8 6 Z" fill="#B9BDC4"/><circle cx="32" cy="10.2" r="4.2" fill="#B9BDC4"/><circle cx="27.2" cy="26.6" r="3.9" fill="none" stroke="#33383F" stroke-width="1.5"/><circle cx="36.8" cy="26.6" r="3.9" fill="none" stroke="#33383F" stroke-width="1.5"/><path d="M31.1 26.2 h1.8 M23.3 25.4 l-3-0.8 M40.7 25.4 l3-0.8" fill="none" stroke="#33383F" stroke-width="1.5" stroke-linecap="round"/>',
  },
  {
    id: 'finance',
    label: '财税顾问',
    color: '#1F8A70',
    glyph: '<rect x="29" y="35" width="6" height="9" rx="2.5" fill="#F2C9A4"/><path d="M13 64 c0-10.5 8.5-15.5 19-15.5 s19 5 19 15.5 Z" fill="#2E3B45"/><circle cx="20" cy="27" r="2.1" fill="#F2C9A4"/><circle cx="44" cy="27" r="2.1" fill="#F2C9A4"/><circle cx="32" cy="26.5" r="12.5" fill="#F2C9A4"/><circle cx="27.2" cy="26.5" r="1.7" fill="#33383F"/><circle cx="36.8" cy="26.5" r="1.7" fill="#33383F"/><path d="M28.6 31.4 q3.4 2.6 6.8 0" fill="none" stroke="#33383F" stroke-width="1.7" stroke-linecap="round"/><path d="M20.2 24.6 c-0.3-8.2 4.7-12.6 11.8-12.6 s12.1 4.4 11.8 12.6 c-3.8-5-8.2-6.4-12.6-5.4 c-1.4 2.6-4 3.4-6.2 2.6 c-1.8-0.6-3.4 0.4-4.8 2.8 Z" fill="#2E2A28"/><circle cx="27.2" cy="26.6" r="3.9" fill="none" stroke="#33383F" stroke-width="1.5"/><circle cx="36.8" cy="26.6" r="3.9" fill="none" stroke="#33383F" stroke-width="1.5"/><path d="M31.1 26.2 h1.8 M23.3 25.4 l-3-0.8 M40.7 25.4 l3-0.8" fill="none" stroke="#33383F" stroke-width="1.5" stroke-linecap="round"/>',
  },
  {
    id: 'legal',
    label: '法律顾问',
    color: '#5568D9',
    glyph: '<rect x="29" y="35" width="6" height="9" rx="2.5" fill="#B07A4F"/><path d="M13 64 c0-10.5 8.5-15.5 19-15.5 s19 5 19 15.5 Z" fill="#262B3A"/><circle cx="20" cy="27" r="2.1" fill="#B07A4F"/><circle cx="44" cy="27" r="2.1" fill="#B07A4F"/><circle cx="32" cy="26.5" r="12.5" fill="#B07A4F"/><circle cx="27.2" cy="26.5" r="1.7" fill="#26221F"/><circle cx="36.8" cy="26.5" r="1.7" fill="#26221F"/><path d="M28.6 32.2 q3.4 2.6 6.8 0" fill="none" stroke="#26221F" stroke-width="1.7" stroke-linecap="round"/><path d="M20.2 24.8 c-0.4-8.4 4.6-13 11.8-13 s12.2 4.6 11.8 13 c-2.6-4.2-6.4-6-11.8-6 s-9.2 1.8-11.8 6 Z" fill="#2E2A28"/><path d="M28.4 29.4 q3.6-1.6 7.2 0 q-1.2 1.9-3.6 1.3 q-2.4 0.6-3.6-1.3 Z" fill="#2E2A28"/>',
  },
  {
    id: 'crossborder',
    label: '跨境卖家',
    color: '#35A3C4',
    glyph: '<rect x="29" y="35" width="6" height="9" rx="2.5" fill="#8D5A3B"/><path d="M13 64 c0-10.5 8.5-15.5 19-15.5 s19 5 19 15.5 Z" fill="#E8DCC8"/><circle cx="20" cy="27" r="2.1" fill="#8D5A3B"/><circle cx="44" cy="27" r="2.1" fill="#8D5A3B"/><circle cx="32" cy="26.5" r="12.5" fill="#8D5A3B"/><circle cx="27.2" cy="26.5" r="1.7" fill="#241F1C"/><circle cx="36.8" cy="26.5" r="1.7" fill="#241F1C"/><path d="M28.6 31.4 q3.4 3 6.8 0" fill="none" stroke="#241F1C" stroke-width="1.7" stroke-linecap="round"/><path d="M20.2 24.8 c-0.4-8.4 4.6-13 11.8-13 s12.2 4.6 11.8 13 c-2.6-4.2-6.4-6-11.8-6 s-9.2 1.8-11.8 6 Z" fill="#2E2A28"/>',
  },
  {
    id: 'researcher',
    label: '独立研究员',
    color: '#4C8FA6',
    glyph: '<rect x="29" y="35" width="6" height="9" rx="2.5" fill="#E8B48C"/><path d="M13 64 c0-10.5 8.5-15.5 19-15.5 s19 5 19 15.5 Z" fill="#556258"/><circle cx="20" cy="27" r="2.1" fill="#E8B48C"/><circle cx="44" cy="27" r="2.1" fill="#E8B48C"/><circle cx="32" cy="26.5" r="12.5" fill="#E8B48C"/><circle cx="27.2" cy="26.5" r="1.7" fill="#33383F"/><circle cx="36.8" cy="26.5" r="1.7" fill="#33383F"/><path d="M28.6 31.4 q3.4 2.6 6.8 0" fill="none" stroke="#33383F" stroke-width="1.7" stroke-linecap="round"/><path d="M22.6 29.5 c0.8 6.8 4.8 9.6 9.4 9.6 s8.6-2.8 9.4-9.6 c-2.2 3-5.4 4.2-9.4 4.2 s-7.2-1.2-9.4-4.2 Z" fill="#B9BDC4"/><circle cx="23.5" cy="19" r="3.4" fill="#B9BDC4"/><circle cx="28.5" cy="15" r="3.6" fill="#B9BDC4"/><circle cx="35.5" cy="15" r="3.6" fill="#B9BDC4"/><circle cx="40.5" cy="19" r="3.4" fill="#B9BDC4"/><circle cx="21.6" cy="23.8" r="3" fill="#B9BDC4"/><circle cx="42.4" cy="23.8" r="3" fill="#B9BDC4"/><circle cx="27.2" cy="26.6" r="3.9" fill="none" stroke="#33383F" stroke-width="1.5"/><circle cx="36.8" cy="26.6" r="3.9" fill="none" stroke="#33383F" stroke-width="1.5"/><path d="M31.1 26.2 h1.8 M23.3 25.4 l-3-0.8 M40.7 25.4 l3-0.8" fill="none" stroke="#33383F" stroke-width="1.5" stroke-linecap="round"/>',
  },
  {
    id: 'craftsman',
    label: '手工艺人',
    color: '#C97B4E',
    glyph: '<rect x="29" y="35" width="6" height="9" rx="2.5" fill="#D19B6E"/><path d="M13 64 c0-10.5 8.5-15.5 19-15.5 s19 5 19 15.5 Z" fill="#5A5148"/><circle cx="20" cy="27" r="2.1" fill="#D19B6E"/><circle cx="44" cy="27" r="2.1" fill="#D19B6E"/><circle cx="32" cy="26.5" r="12.5" fill="#D19B6E"/><circle cx="27.2" cy="26.5" r="1.7" fill="#2A2622"/><circle cx="36.8" cy="26.5" r="1.7" fill="#2A2622"/><path d="M28.6 31.4 q3.4 2.6 6.8 0" fill="none" stroke="#2A2622" stroke-width="1.7" stroke-linecap="round"/><path d="M20.6 21.6 c0-7.4 4.8-11.2 11.4-11.2 s11.4 3.8 11.4 11.2 Z" fill="#6B7A4A"/><rect x="20" y="20" width="24" height="3.4" rx="1.7" fill="#57633B"/><path d="M43 19.2 c4.6 0.3 7.2 2 7.4 4.2 l-8.6 0.8 Z" fill="#57633B"/>',
  },
  {
    id: 'fitness',
    label: '健身教练',
    color: '#D9534F',
    glyph: '<rect x="29" y="35" width="6" height="9" rx="2.5" fill="#B07A4F"/><path d="M13 64 c0-10.5 8.5-15.5 19-15.5 s19 5 19 15.5 Z" fill="#2F3338"/><circle cx="20" cy="27" r="2.1" fill="#B07A4F"/><circle cx="44" cy="27" r="2.1" fill="#B07A4F"/><circle cx="32" cy="26.5" r="12.5" fill="#B07A4F"/><circle cx="27.2" cy="26.5" r="1.7" fill="#26221F"/><circle cx="36.8" cy="26.5" r="1.7" fill="#26221F"/><path d="M28.2 31 q3.8 3.8 7.6 0" fill="none" stroke="#26221F" stroke-width="1.8" stroke-linecap="round"/><path d="M20.8 23.2 c-0.2-7.6 4.5-11.4 11.2-11.4 s11.4 3.8 11.2 11.4 c-3-3.4-6.6-4.8-11.2-4.8 s-8.2 1.4-11.2 4.8 Z" fill="#2E2A28"/>',
  },
  {
    id: 'foodie',
    label: '美食创作者',
    color: '#F2994A',
    glyph: '<rect x="29" y="35" width="6" height="9" rx="2.5" fill="#E8B48C"/><path d="M13 64 c0-10.5 8.5-15.5 19-15.5 s19 5 19 15.5 Z" fill="#FFFFFF"/><circle cx="20" cy="27" r="2.1" fill="#E8B48C"/><circle cx="44" cy="27" r="2.1" fill="#E8B48C"/><circle cx="20" cy="30.5" r="1.3" fill="#E5B84B"/><circle cx="44" cy="30.5" r="1.3" fill="#E5B84B"/><circle cx="32" cy="26.5" r="12.5" fill="#E8B48C"/><circle cx="27.2" cy="26.5" r="1.7" fill="#33383F"/><circle cx="36.8" cy="26.5" r="1.7" fill="#33383F"/><path d="M28.6 31.4 q3.4 2.6 6.8 0" fill="none" stroke="#33383F" stroke-width="1.7" stroke-linecap="round"/><circle cx="24.2" cy="30" r="1.9" fill="#F0997F" opacity="0.5"/><circle cx="39.8" cy="30" r="1.9" fill="#F0997F" opacity="0.5"/><path d="M19.9 23.8 c-0.3-8 4.7-12 12.1-12 s12.4 4 12.1 12 Z" fill="#4A3728"/>',
  },
  {
    id: 'traveler',
    label: '旅行博主',
    color: '#C9A26B',
    glyph: '<rect x="29" y="35" width="6" height="9" rx="2.5" fill="#D19B6E"/><path d="M13 64 c0-10.5 8.5-15.5 19-15.5 s19 5 19 15.5 Z" fill="#4E6E58"/><circle cx="20" cy="27" r="2.1" fill="#D19B6E"/><circle cx="44" cy="27" r="2.1" fill="#D19B6E"/><circle cx="20" cy="30.5" r="1.3" fill="#E5B84B"/><circle cx="44" cy="30.5" r="1.3" fill="#E5B84B"/><circle cx="32" cy="26.5" r="12.5" fill="#D19B6E"/><circle cx="27.2" cy="26.5" r="1.7" fill="#2A2622"/><circle cx="36.8" cy="26.5" r="1.7" fill="#2A2622"/><path d="M28.6 31.4 q3.4 2.6 6.8 0" fill="none" stroke="#2A2622" stroke-width="1.7" stroke-linecap="round"/><path d="M20.2 24.8 c-0.4-8.4 4.6-13 11.8-13 s12.2 4.6 11.8 13 c-2.6-4.2-6.4-6-11.8-6 s-9.2 1.8-11.8 6 Z" fill="#2E2A28"/><path d="M43.5 21.5 c5.2 1.4 7.2 6.4 6 12 c-0.9-4.6-2.9-7.6-6.6-8.8 Z" fill="#2E2A28"/>',
  },
  {
    id: 'farmer',
    label: '新农人',
    color: '#7CB342',
    glyph: '<rect x="29" y="35" width="6" height="9" rx="2.5" fill="#B07A4F"/><path d="M13 64 c0-10.5 8.5-15.5 19-15.5 s19 5 19 15.5 Z" fill="#8A6B4A"/><circle cx="20" cy="27" r="2.1" fill="#B07A4F"/><circle cx="44" cy="27" r="2.1" fill="#B07A4F"/><circle cx="32" cy="26.5" r="12.5" fill="#B07A4F"/><circle cx="27.2" cy="26.5" r="1.7" fill="#26221F"/><circle cx="36.8" cy="26.5" r="1.7" fill="#26221F"/><path d="M28.6 31.4 q3.4 3 6.8 0" fill="none" stroke="#26221F" stroke-width="1.7" stroke-linecap="round"/><path d="M20.6 21.6 c0-7.4 4.8-11.2 11.4-11.2 s11.4 3.8 11.4 11.2 Z" fill="#D9B36A"/><rect x="20" y="20" width="24" height="3.4" rx="1.7" fill="#B8934E"/><path d="M43 19.2 c4.6 0.3 7.2 2 7.4 4.2 l-8.6 0.8 Z" fill="#B8934E"/>',
  },
];

export const PERSONA_AVATAR_MAP = Object.fromEntries(PERSONA_AVATARS.map((p) => [p.id, p]));

const FALLBACK_PALETTE = PERSONA_AVATARS.map((p) => p.color);

/**
 * 昵称首字兜底色：按名称稳定散列到目录色板，保证同一昵称颜色恒定。
 */
export function fallbackColorFor(name) {
  const key = String(name || '');
  let hash = 0;
  for (let i = 0; i < key.length; i++) {
    hash = (hash * 31 + key.charCodeAt(i)) >>> 0;
  }
  return FALLBACK_PALETTE[hash % FALLBACK_PALETTE.length];
}
