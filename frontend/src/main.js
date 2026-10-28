import { createApp } from 'vue';
import App from './App.vue';
import router from './router';
import OpcIcon from './components/OpcIcon.vue';
import WorkspaceHeader from './components/layout/WorkspaceHeader.vue';
import './style.css';

/**
 * One-time migration for the old hash-based navigation.
 * Old links looked like /#forum?post_id=xxx; HTML5 history links are /forum/xxx.
 */
function migrateLegacyHash() {
  const raw = window.location.hash.replace(/^#\/?/, '').trim();
  if (!raw) return;
  const [segment, queryString = ''] = raw.split('?');
  const params = new URLSearchParams(queryString);
  const map = {
    home: '/',
    forum: '/forum',
    product: '/products',
    policy: '/policies',
    demand: '/demands',
    sop: '/sop',
    perks: '/perks',
    membership: '/membership',
    compliance: '/compliance',
    profile: '/profile',
    'change-password': '/change-password',
    'backend-orch': '/admin/orchestration',
    console: '/admin/orchestration',
    'frontend-orch': '/admin/layout',
    ops: '/admin/ops',
    moderation: '/admin/moderation',
  };
  const base = map[segment];
  if (!base) return;
  let target = base;
  if (segment === 'forum' && params.get('post_id')) {
    target = `/forum/${encodeURIComponent(params.get('post_id'))}`;
    params.delete('post_id');
  }
  const rest = params.toString();
  if (rest) target += `?${rest}`;
  window.history.replaceState(null, '', target);
}

migrateLegacyHash();

const app = createApp(App);
app.component('OpcIcon', OpcIcon);
app.component('WorkspaceHeader', WorkspaceHeader);
app.use(router);
app.mount('#app');
