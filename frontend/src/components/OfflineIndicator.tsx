import { useState, useEffect } from 'react';
import { Wifi, WifiOff, X } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import styles from './OfflineIndicator.module.css';

export default function OfflineIndicator() {
  const [isOnline, setIsOnline] = useState<boolean>(true);
  const [showBanner, setShowBanner] = useState<boolean>(false);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      setShowBanner(true);
      // Auto-hide online confirmation after 4 seconds
      const timer = setTimeout(() => setShowBanner(false), 4000);
      return () => clearTimeout(timer);
    };

    const handleOffline = () => {
      setIsOnline(false);
      setShowBanner(true);
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
          className={styles.bannerPosition}
        >
          <div className={`${styles.banner} ${isOnline ? styles.bannerOnline : styles.bannerOffline}`}>
            <div className={styles.contentGroup}>
              <div className={`${styles.iconWrap} ${isOnline ? styles.iconWrapOnline : styles.iconWrapOffline}`}>
                {isOnline ? <Wifi className="w-4.5 h-4.5" /> : <WifiOff className="w-4.5 h-4.5" />}
              </div>
              <div>
                <p className={styles.textTitle}>
                  {isOnline ? 'Connection Restored' : 'Operating in Offline Resilience Mode'}
                </p>
                <p className={styles.textSubtitle}>
                  {isOnline
                    ? 'Syncing localized changes with central database'
                    : 'Changes will queue until connection is established'}
                </p>
              </div>
            </div>
            <button
              id="close-offline-banner-btn"
              onClick={() => setShowBanner(false)}
              className={styles.closeBtn}
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
