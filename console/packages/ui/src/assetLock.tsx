/** 编排资产排他编辑锁（三平台通用底座）。
 *
 * 语义对齐后端 locks.py：TTL 15 分钟，持有期间每 60s 心跳续期（acquire 即续期），
 * 失联自动过期。三态横幅：我持有（可释放）/ 他人持有（可尝试接管）/ 空闲。
 */
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { dispatch } from "@opchub/console-api";
import { Badge, Button } from "./primitives";
import { useToast } from "./overlay";

const HEARTBEAT_MS = 60 * 1000;

export type AssetKind = "operator" | "subgraph" | "scenario";

export interface AssetLockState {
  entity_type: string;
  entity_key: string;
  holder_id: string;
  holder_name?: string;
  expires_at?: string;
}

interface UseAssetLockOptions {
  myUserId?: string;
}

export function useAssetLock(entityType: AssetKind, options: UseAssetLockOptions = {}) {
  const { toast } = useToast();
  const qc = useQueryClient();
  const [entityKey, setEntityKey] = useState("");
  const [lock, setLock] = useState<AssetLockState | null>(null);
  const [busy, setBusy] = useState(false);
  const heartbeatRef = useRef<number | null>(null);

  const stopHeartbeat = useCallback(() => {
    if (heartbeatRef.current !== null) {
      window.clearInterval(heartbeatRef.current);
      heartbeatRef.current = null;
    }
  }, []);

  const startHeartbeat = useCallback(
    (key: string) => {
      stopHeartbeat();
      heartbeatRef.current = window.setInterval(async () => {
        // 心跳即 acquire 续期；失败说明锁已失效/被接管，立刻落地提示
        try {
          const res = await dispatch<AssetLockState>("orchestration.locks.acquire", {
            entity_type: entityType,
            entity_key: key,
          });
          setLock(res);
        } catch {
          setLock(null);
          stopHeartbeat();
          toast({
            title: "编辑锁已失效",
            description: "续期失败，锁可能已被释放或接管，请重新获取。",
            tone: "warning",
          });
          qc.invalidateQueries({ queryKey: ["catalog"] });
        }
      }, HEARTBEAT_MS);
    },
    [entityType, qc, stopHeartbeat, toast],
  );

  const acquire = useCallback(
    async (key: string) => {
      setBusy(true);
      try {
        const res = await dispatch<AssetLockState>("orchestration.locks.acquire", {
          entity_type: entityType,
          entity_key: key,
        });
        setEntityKey(key);
        setLock(res);
        startHeartbeat(key);
        qc.invalidateQueries({ queryKey: ["catalog"] });
        return res;
      } catch (err) {
        setEntityKey(key);
        setLock(null);
        throw err;
      } finally {
        setBusy(false);
      }
    },
    [entityType, qc, startHeartbeat],
  );

  const release = useCallback(async () => {
    if (!entityKey) return;
    setBusy(true);
    try {
      await dispatch("orchestration.locks.release", {
        entity_type: entityType,
        entity_key: entityKey,
      });
    } finally {
      stopHeartbeat();
      setLock(null);
      setBusy(false);
      qc.invalidateQueries({ queryKey: ["catalog"] });
    }
  }, [entityKey, entityType, qc, stopHeartbeat]);

  // 行内锁状态同步（列表刷新带来他人持锁信息时调用）
  const attach = useCallback((key: string, lockFromRow?: AssetLockState | null) => {
    setEntityKey(key);
    setLock(lockFromRow || null);
  }, []);

  // 切换资产 / 卸载：停止心跳
  useEffect(() => {
    return () => stopHeartbeat();
  }, [stopHeartbeat]);

  const heldByMe = useMemo(
    () => Boolean(lock && options.myUserId && lock.holder_id === options.myUserId),
    [lock, options.myUserId],
  );
  const heldByOther = useMemo(() => Boolean(lock && !heldByMe), [lock, heldByMe]);
  const holderLabel = lock ? lock.holder_name || lock.holder_id : "";
  const remainingSeconds = useMemo(() => {
    if (!lock?.expires_at) return 0;
    const ms = new Date(lock.expires_at).getTime() - Date.now();
    return Number.isFinite(ms) ? Math.max(0, Math.round(ms / 1000)) : 0;
  }, [lock]);

  return {
    entityKey,
    lock,
    heldByMe,
    heldByOther,
    holderLabel,
    remainingSeconds,
    busy,
    acquire,
    release,
    attach,
  };
}

export function AssetLockBanner({
  assetLabel,
  heldByMe,
  heldByOther,
  holderLabel,
  remainingSeconds,
  busy,
  onAcquire,
  onRelease,
}: {
  assetLabel: string;
  heldByMe: boolean;
  heldByOther: boolean;
  holderLabel: string;
  remainingSeconds: number;
  busy?: boolean;
  onAcquire: () => void;
  onRelease: () => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-border bg-muted/30 px-3.5 py-2.5">
      <div className="flex items-center gap-2 text-sm">
        {heldByMe ? (
          <>
            <Badge tone="success">编辑中</Badge>
            <span className="text-muted-foreground">
              你持有「{assetLabel}」的编辑锁{remainingSeconds > 0 ? ` · 剩 ${Math.ceil(remainingSeconds / 60)} 分钟` : ""}
              （每 60 秒自动续期）
            </span>
          </>
        ) : heldByOther ? (
          <>
            <Badge tone="warning">被锁定</Badge>
            <span className="text-muted-foreground">
              「{assetLabel}」正由 {holderLabel} 编辑，可尝试在其失联后接管
            </span>
          </>
        ) : (
          <>
            <Badge>空闲</Badge>
            <span className="text-muted-foreground">获取编辑锁后才能修改「{assetLabel}」</span>
          </>
        )}
      </div>
      {heldByMe ? (
        <Button variant="secondary" className="h-7 text-xs" onClick={onRelease} disabled={busy}>
          释放锁
        </Button>
      ) : (
        <Button variant="secondary" className="h-7 text-xs" onClick={onAcquire} disabled={busy}>
          {heldByOther ? "尝试获取锁" : "锁定并编辑"}
        </Button>
      )}
    </div>
  );
}
