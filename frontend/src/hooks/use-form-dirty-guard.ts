import { useState, useCallback } from "react";
import type { UseFormReturn } from "react-hook-form";

interface UseFormDirtyGuardOptions {
  form: UseFormReturn<any>;
  onClose: () => void;
}

interface UseFormDirtyGuardResult {
  /** Call this instead of directly calling onClose */
  handleClose: () => void;
  /** Whether the confirmation dialog is open */
  showConfirm: boolean;
  /** Confirm discard — closes the dialog */
  confirmDiscard: () => void;
  /** Cancel discard — keeps the dialog open */
  cancelDiscard: () => void;
}

export function useFormDirtyGuard({
  form,
  onClose,
}: UseFormDirtyGuardOptions): UseFormDirtyGuardResult {
  const [showConfirm, setShowConfirm] = useState(false);

  const handleClose = useCallback(() => {
    if (form.formState.isDirty) {
      setShowConfirm(true);
    } else {
      onClose();
    }
  }, [form.formState.isDirty, onClose]);

  const confirmDiscard = useCallback(() => {
    setShowConfirm(false);
    form.reset();
    onClose();
  }, [form, onClose]);

  const cancelDiscard = useCallback(() => {
    setShowConfirm(false);
  }, []);

  return { handleClose, showConfirm, confirmDiscard, cancelDiscard };
}

