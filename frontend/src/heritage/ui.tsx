import { useEffect, useRef, type ReactNode } from "react";
import { AlertCircle, X } from "lucide-react";
export function DataState({
  loading,
  error,
  empty,
  retry,
}: {
  loading?: boolean;
  error?: Error | null;
  empty?: string;
  retry?: () => void;
}) {
  if (loading)
    return (
      <div className="fh-state" role="status">
        Loading data…
      </div>
    );
  if (error)
    return (
      <div className="fh-state fh-error" role="alert">
        <AlertCircle size={20} />
        <h3>Data unavailable</h3>
        <p>{error.message}</p>
        {retry && (
          <button className="fh-button" onClick={retry}>
            Retry
          </button>
        )}
      </div>
    );
  return (
    <div className="fh-state">
      <h3>{empty || "No results available."}</h3>
      <p>No sample results have been substituted.</p>
    </div>
  );
}
export function Dialog({
  title,
  children,
  onClose,
  className = "",
  restoreFocus,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  className?: string;
  restoreFocus?: () => HTMLElement | null;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  const focusTarget = useRef(restoreFocus);
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const dialog = ref.current;
    dialog?.showModal();
    return () => {
      dialog?.close();
      (focusTarget.current?.() || previous)?.focus();
    };
  }, []);
  return (
    <dialog
      className={`fh-dialog ${className}`}
      ref={ref}
      aria-label={title}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === ref.current) onClose();
      }}
    >
      <button className="fh-close" aria-label="Close dialog" onClick={onClose}>
        <X size={20} />
      </button>
      {children}
    </dialog>
  );
}
export function StoryImage({ src, alt }: { src: string; alt: string }) {
  return (
    <img
      src={src}
      alt={alt}
      loading="lazy"
      onError={(event) => {
        event.currentTarget.style.display = "none";
        event.currentTarget.parentElement?.classList.add(
          "fh-image-unavailable",
        );
      }}
    />
  );
}
