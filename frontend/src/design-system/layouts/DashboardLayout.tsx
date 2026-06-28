import { Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import { tokens } from '../tokens';
import type { ReactNode } from 'react';

interface DashboardLayoutProps {
  sidebarContent: ReactNode;
  topbarContent: ReactNode;
  sidebarOpen?: boolean;
}

export function DashboardLayout({ sidebarContent, topbarContent, sidebarOpen = true }: DashboardLayoutProps) {
  const location = useLocation();

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      background: tokens.colors.base,
      color: tokens.colors.text,
      overflow: 'hidden',
    }}>
      {/* Sidebar */}
      <div style={{
        width: sidebarOpen ? 240 : 60,
        minWidth: sidebarOpen ? 240 : 60,
        transition: `width ${tokens.animation.slow}`,
        background: tokens.colors.surface,
        borderRight: `1px solid ${tokens.colors.border}`,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}>
        {sidebarContent}
      </div>

      {/* Main area */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
      }}>
        {/* Topbar */}
        <div style={{
          height: 48,
          minHeight: 48,
          background: tokens.colors.surface,
          borderBottom: `1px solid ${tokens.colors.border}`,
          display: 'flex',
          alignItems: 'center',
          padding: `0 ${tokens.spacing.xl}`,
          gap: tokens.spacing.lg,
        }}>
          {topbarContent}
        </div>

        {/* Page content */}
        <div style={{
          flex: 1,
          overflow: 'auto',
          padding: tokens.spacing['3xl'],
        }}>
          <AnimatePresence mode="wait">
            <motion.div
              key={location.pathname}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.15, ease: 'easeOut' }}
            >
              <Outlet />
            </motion.div>
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
