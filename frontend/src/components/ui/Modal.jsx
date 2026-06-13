import { useEffect } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";
import clsx from "clsx";

export default function Modal({ open, onClose, children, wide = false }) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;
  return createPortal(
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/60 p-4 backdrop-blur-sm sm:p-8"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        className={clsx(
          "card relative my-auto w-full shadow-pop animate-[pt-modal-in_0.18s_ease-out]",
          wide ? "max-w-6xl" : "max-w-2xl"
        )}
      >
        <button
          onClick={onClose}
          aria-label="Close"
          className="absolute right-3.5 top-3.5 z-10 rounded-lg p-1.5 text-muted transition-colors hover:bg-raised hover:text-fg"
        >
          <X size={18} />
        </button>
        {children}
      </div>
      <style>{`@keyframes pt-modal-in { from { opacity: 0; transform: translateY(10px) scale(0.985); } to { opacity: 1; transform: none; } }`}</style>
    </div>,
    document.body
  );
}
