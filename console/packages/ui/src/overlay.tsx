/** 浮层原语：Toast（轻提示队列）与 Modal（对话框）。零第三方依赖。
 *
 * ToastProvider 挂在应用根部；useToast().toast({title, description?, tone?})
 * 推送自动消退提示。Modal 受控开合，Esc/遮罩点击关闭。
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { cn } from "./primitives";
import { Button } from "./primitives";

// ---------------------------------------------------------------------------
// Toast
// ---------------------------------------------------------------------------
type ToastTone = "neutral" | "success" | "warning" | "destructive";
interface ToastItem {
  id: number;
  title: string;
  description?: string;
  tone: ToastTone;
}

interface ToastContextValue {
  toast: (item: { title: string; description?: string; tone?: ToastTone }) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);
const TOAST_TTL_MS = 4200;

const toneStyles: Record<ToastTone, string> = {
  neutral: "border-border bg-card text-card-foreground",
  success: "border-success/40 bg-card text-card-foreground",
  warning: "border-warning/50 bg-card text-card-foreground",
  destructive: "border-destructive/50 bg-card text-card-foreground",
};

const toneDot: Record<ToastTone, string> = {
  neutral: "bg-muted-foreground",
  success: "bg-success",
  warning: "bg-warning",
  destructive: "bg-destructive",
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const toast = useCallback(
    ({ title, description, tone = "neutral" }: { title: string; description?: string; tone?: ToastTone }) => {
      const id = nextId.current++;
      setItems((prev) => [...prev.slice(-4), { id, title, description, tone }]);
      window.setTimeout(() => {
        setItems((prev) => prev.filter((t) => t.id !== id));
      }, TOAST_TTL_MS);
    },
    [],
  );

  const value = useMemo(() => ({ toast }), [toast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      <div
        aria-live="polite"
        className="pointer-events-none fixed bottom-5 right-5 z-50 flex w-80 flex-col gap-2"
      >
        {items.map((t) => (
          <div
            key={t.id}
            className={cn(
              "pointer-events-auto flex items-start gap-2.5 rounded-lg border px-3.5 py-2.5 shadow-md",
              toneStyles[t.tone],
            )}
          >
            <span className={cn("mt-1.5 size-2 shrink-0 rounded-full", toneDot[t.tone])} />
            <div className="min-w-0">
              <div className="text-sm font-medium">{t.title}</div>
              {t.description && (
                <div className="mt-0.5 break-words text-xs text-muted-foreground">{t.description}</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast 必须在 ToastProvider 内使用");
  return ctx;
}

// ---------------------------------------------------------------------------
// Modal
// ---------------------------------------------------------------------------
export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
  width = "max-w-lg",
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  description?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  width?: string;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div
        className="absolute inset-0 bg-foreground/25 backdrop-blur-[2px]"
        onClick={onClose}
        aria-hidden
      />
      <div
        role="dialog"
        aria-modal="true"
        className={cn(
          "relative flex max-h-[85vh] w-full flex-col rounded-lg border border-border bg-card shadow-lg",
          width,
        )}
      >
        <div className="flex flex-col gap-1 px-5 pt-4 pb-3">
          <div className="text-sm font-semibold tracking-tight">{title}</div>
          {description && <div className="text-xs text-muted-foreground">{description}</div>}
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-4">{children}</div>
        {footer && (
          <div className="flex items-center justify-end gap-2 border-t border-border px-5 py-3">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

export function ModalActions({
  onCancel,
  cancelLabel = "取消",
  children,
  busy,
}: {
  onCancel: () => void;
  cancelLabel?: string;
  children: ReactNode;
  busy?: boolean;
}) {
  return (
    <>
      <Button variant="secondary" onClick={onCancel} disabled={busy}>
        {cancelLabel}
      </Button>
      {children}
    </>
  );
}
