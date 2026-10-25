/**
 * 排他编辑锁 composable —— 后端编排工作台三层资产共用。
 *
 * 语义：
 * - 变更（创建/删除/版本保存/发布）前必须先 acquire 拿到目标资产的锁；
 * - 持有期间每 60s 心跳续期（TTL 15 分钟），失联后自动过期释放；
* - 锁状态与锁定人通过列表行的 lock_status 同步展示（attach）。
 */
import { computed, onBeforeUnmount, ref } from 'vue';
import { dispatchGateway } from '@/api/gateway';

const HEARTBEAT_MS = 60 * 1000;

export function resolveUid(userSession) {
  return (
    userSession?.uid
    || userSession?.user?.uid
    || userSession?.session?.uid
    || localStorage.getItem('opchub_current_uid')
    || ''
  );
}

export function useAssetLock(userSession, entityType, emit) {
  const entityKey = ref('');
  const lockInfo = ref(null);
  const isBusy = ref(false);
  let heartbeatTimer = null;

  const myUid = computed(() => resolveUid(userSession));
  const heldByMe = computed(() => !!lockInfo.value && lockInfo.value.holder_id === myUid.value);
  const heldByOther = computed(() => !!lockInfo.value && lockInfo.value.holder_id !== myUid.value);
  const holderLabel = computed(() => {
    if (!lockInfo.value) return '';
    const { holder_name: name, holder_id: id } = lockInfo.value;
    return name && name !== id ? `${name}（${id}）` : id;
  });
  const remainingSeconds = computed(() => {
    if (!lockInfo.value) return 0;
    const ms = new Date(lockInfo.value.expires_at).getTime() - Date.now();
    return Math.max(0, Math.round(ms / 1000));
  });

  function toast(payload) {
    emit && emit('toast', payload);
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer);
      heartbeatTimer = null;
    }
  }

  function startHeartbeat() {
    stopHeartbeat();
    heartbeatTimer = setInterval(async () => {
      if (!heldByMe.value || !entityKey.value) return;
      const res = await dispatchGateway(
        'orchestration.locks.acquire',
        { entity_type: entityType, entity_key: entityKey.value },
        { silent: true },
      );
      if (res.ok && res.data) {
        lockInfo.value = res.data;
      } else {
        // 心跳失败（被接管/会话过期）：立刻刷新状态提示
        lockInfo.value = null;
        stopHeartbeat();
        toast({ title: '编辑锁已失效', message: '续期失败，锁可能已被释放或接管，请重新获取。', type: 'ERROR' });
      }
    }, HEARTBEAT_MS);
  }

  /** 从列表行同步锁状态（展示用，不发起请求） */
  function attach(key, lockFromRow) {
    entityKey.value = key || '';
    lockInfo.value = lockFromRow || null;
  }

  /** 获取（或续期）排他锁；成功返回 true */
  async function acquire(key, { quiet = false } = {}) {
    if (!key || isBusy.value) return false;
    isBusy.value = true;
    try {
      const res = await dispatchGateway(
        'orchestration.locks.acquire',
        { entity_type: entityType, entity_key: key },
        { silent: true },
      );
      if (res.ok && res.data) {
        entityKey.value = key;
        lockInfo.value = res.data;
        startHeartbeat();
        return true;
      }
      if (!quiet) {
        toast({ title: '获取编辑锁失败', message: res.error || '该资产可能正被他人锁定。', type: 'ERROR' });
      }
      return false;
    } finally {
      isBusy.value = false;
    }
  }

  async function release({ quiet = false } = {}) {
    if (!entityKey.value) return;
    const res = await dispatchGateway(
      'orchestration.locks.release',
      { entity_type: entityType, entity_key: entityKey.value },
      { silent: true },
    );
    if (res.ok) {
      lockInfo.value = null;
      stopHeartbeat();
    } else if (!quiet) {
      toast({ title: '释放编辑锁失败', message: res.error || '请稍后重试。', type: 'ERROR' });
    }
  }

  onBeforeUnmount(stopHeartbeat);

  return {
    entityKey,
    lockInfo,
    isBusy,
    heldByMe,
    heldByOther,
    holderLabel,
    remainingSeconds,
    attach,
    acquire,
    release,
  };
}

/** 统一的目录写操作分发：{action, payload} → orchestration.catalog.* 路由 */
export async function catalogWrite(action, payload, { silent = false } = {}) {
  const route = `orchestration.${action}`;
  return dispatchGateway(route, { action, payload }, { silent });
}
