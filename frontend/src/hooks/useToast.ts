import { useState, useCallback, useEffect } from 'react';

export type ToastType = 'success' | 'error' | 'info' | 'warning';

export interface ToastMessage {
  id: string;
  message: string;
  type: ToastType;
  duration?: number;
}

// Global listener registry for contextless toasts
type ToastListener = (toast: ToastMessage) => void;
const listeners = new Set<ToastListener>();

export function emitToast(message: string, type: ToastType = 'info', duration: number = 3000) {
  const toast: ToastMessage = {
    id: Math.random().toString(36).substring(2, 9),
    message,
    type,
    duration,
  };
  listeners.forEach((listener) => listener(toast));
}

export default function useToast() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = useCallback((message: string, type: ToastType = 'info', duration: number = 3000) => {
    const id = Math.random().toString(36).substring(2, 9);
    const newToast: ToastMessage = { id, message, type, duration };
    setToasts((prev) => [...prev, newToast]);
  }, []);

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  useEffect(() => {
    const handleGlobalToast = (toast: ToastMessage) => {
      setToasts((prev) => [...prev, toast]);
    };

    listeners.add(handleGlobalToast);
    return () => {
      listeners.delete(handleGlobalToast);
    };
  }, []);

  return {
    toasts,
    removeToast,
    showToast: addToast,
    success: useCallback((msg: string, dur?: number) => addToast(msg, 'success', dur), [addToast]),
    error: useCallback((msg: string, dur?: number) => addToast(msg, 'error', dur), [addToast]),
    info: useCallback((msg: string, dur?: number) => addToast(msg, 'info', dur), [addToast]),
    warning: useCallback((msg: string, dur?: number) => addToast(msg, 'warning', dur), [addToast]),
  };
}
