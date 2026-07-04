import { useState, useEffect } from 'react';
import { Wifi, WifiOff, X } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

export default function OfflineIndicator() {
  const [isOnline, setIsOnline] = useState<boolean>(true);
  const [showBanner, setShowBanner] = useState<boolean>(false);
  const [hasChanged, setHasChanged] = useState<boolean>(false);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setShowBanner(true);
      setHasChanged(true);
      // Auto-hide online confirmation after 4 seconds
      const timer = setTimeout(() => setShowBanner(false), 4000);
      return () => clearTimeout(timer);
    };

    const handleOffline = () => {
      setIsOnline(false);
      setShowBanner(true);
      setHasChanged(true);
    };

    setIsOnline(navigator.onLine);
    if (!navigator.onLine) {
      setShowBanner(true);
    }

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  if (!showBanner && isOnline) return null;

  return (
    <AnimatePresence>
      {showBanner && (
        <motion.div
          id="wimlogic-offline-banner"
          initial={{ opacity: 0, y: -50 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -50 }}
          transition={{ duration: 0.3, ease: 'easeOut' }}
          className="fixed top-4 left-1/2 -translate-x-1/2 z-50 w-full max-w-md px-4"
        >
          <div
            className={`flex items-center justify-between p-3.5 rounded-xl border shadow-lg ${
              isOnline
                ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                : 'bg-amber-50 border-amber-200 text-amber-900'
            }`}
          >
            <div className="flex items-center gap-3">
              {isOnline ? (
                <div className="p-1.5 rounded-lg bg-emerald-100 text-emerald-700">
                  <Wifi className="w-4.5 h-4.5" />
                </div>
              ) : (
                <div className="p-1.5 rounded-lg bg-amber-100 text-amber-700 animate-pulse">
                  <WifiOff className="w-4.5 h-4.5" />
                </div>
              )}
              <div>
                <p className="text-sm font-semibold tracking-tight">
                  {isOnline ? 'Connection Restored' : 'Operating in Offline Resilience Mode'}
                </p>
                <p className="text-xs opacity-80 mt-0.5">
                  {isOnline
                    ? 'Syncing localized changes with central database'
                    : 'Changes will queue until connection is established'}
                </p>
              </div>
            </div>
            <button
              id="close-offline-banner-btn"
              onClick={() => setShowBanner(false)}
              className="p-1 rounded-md opacity-60 hover:opacity-100 transition-opacity focus:outline-none"
              aria-label="Close notification"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
