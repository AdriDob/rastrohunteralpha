import { Outlet, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { useStore } from '../../lib/store';
import { useIsMobile } from '../../lib/useIsMobile';
import AssistantPanel from '../AssistantPanel';
import { DesktopSidebar, MobileBottomBar } from './Sidebar';
import CommandPalette from '../CommandPalette';
import KeyboardShortcutsDialog from '../KeyboardShortcuts';
import { NotificationToaster, useSmartNotifications } from '../SmartNotifications';

const btnSmallStyle: React.CSSProperties = {
  background: 'transparent', border: 'none', color: '#7c8299', cursor: 'pointer',
  fontSize: 14, padding: '4px 6px', borderRadius: 4,
};

export default function Layout() {
  const isMobile = useIsMobile();
  const { sidebarOpen, sidebarCollapsed, assistantOpen, setAssistantOpen } = useStore();
  const location = useLocation();

  useSmartNotifications();

  const isExpanded = sidebarOpen && !sidebarCollapsed;

  return (
    <div style={{
      display: 'flex', flexDirection: isMobile ? 'column' : 'row',
      height: '100vh', overflow: 'hidden',
    }}>
      <NotificationToaster />
      <KeyboardShortcutsDialog />
      <CommandPalette />

      {isMobile ? (
        <>
          <main style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
            <AnimatePresence mode="wait">
              <motion.div
                key={location.pathname}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.15, ease: 'easeOut' }}
                style={{ flex: 1 }}
              >
                <Outlet />
              </motion.div>
            </AnimatePresence>
          </main>
          <MobileBottomBar />
        </>
      ) : (
        <>
          <DesktopSidebar isExpanded={isExpanded} />
          <main style={{
            flex: 1, overflow: 'auto', padding: '24px 32px',
            display: 'flex', flexDirection: 'column', gap: 16,
            transition: 'margin-right 0.2s ease',
            marginRight: assistantOpen ? 320 : 0,
          }}>
            <AnimatePresence mode="wait">
              <motion.div
                key={location.pathname}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -6 }}
                transition={{ duration: 0.15, ease: 'easeOut' }}
                style={{ flex: 1 }}
              >
                <Outlet />
              </motion.div>
            </AnimatePresence>
          </main>
        </>
      )}

      {/* Global AI Copilot Panel (desktop overlay) */}
      {!isMobile && (
        <div style={{
          position: 'fixed', top: 0, right: 0, bottom: 0,
          width: 320, zIndex: 100,
          transform: assistantOpen ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.2s ease',
          display: 'flex', flexDirection: 'column',
          background: '#1a1d29', borderLeft: '1px solid #2a2e3d',
          overflow: 'auto',
        }}>
          <div style={{
            padding: '12px 14px', borderBottom: '1px solid #2a2e3d',
            display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexShrink: 0,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span style={{ fontSize: 16 }}>🧠</span>
              <span style={{ fontWeight: 700, fontSize: 13, color: '#e0e0e0' }}>AI Copilot</span>
            </div>
            <button
              onClick={() => setAssistantOpen(false)}
              style={{ ...btnSmallStyle, fontSize: 16 }}
              onMouseEnter={e => { e.currentTarget.style.color = '#fff'; }}
              onMouseLeave={e => { e.currentTarget.style.color = '#7c8299'; }}
            >✕</button>
          </div>
          <div style={{ flex: 1, overflow: 'auto', padding: '12px 0' }}>
            <AssistantPanel title="Global Context" compact={false} currentPath={location.pathname} />
          </div>
        </div>
      )}
    </div>
  );
}
