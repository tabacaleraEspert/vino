import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { useData } from '../context/DataContext';
import { useNavigate, useLocation, Outlet } from 'react-router';
import { TopBar, BottomBar, ConfirmDialog } from './fina/shared';
import { HomeEditorial } from './fina/HomeEditorial';
import { GastosScreen } from './fina/GastosScreen';
import { CatsScreen } from './fina/CatsScreen';
import { ReglasScreen } from './fina/ReglasScreen';
import { ChatScreen } from './fina/ChatScreen';
import { NewExpenseSheet, CategoryEditSheet, Drawer, NotificationsPanel, PlansSheet, StoriesViewer } from './fina/Sheets';

export function RootLayout() {
  const { user, logout } = useAuth();
  const { refresh } = useData();
  const navigate = useNavigate();
  const location = useLocation();

  // Child routes (e.g. /admin, /settings) render via Outlet instead of tabs
  const isChildRoute = location.pathname !== '/';

  const [tab, setTab] = useState<string>('home');
  const [drawer, setDrawer] = useState(false);
  const [notifOpen, setNotifOpen] = useState(false);
  const [expenseOpen, setExpenseOpen] = useState(false);
  const [editingTx, setEditingTx] = useState<any>(null);
  const [deletingTx, setDeletingTx] = useState<any>(null);
  const [catSheetOpen, setCatSheetOpen] = useState(false);
  const [editingCat, setEditingCat] = useState<any>(null);
  const [plansOpen, setPlansOpen] = useState(false);
  const [storiesOpen, setStoriesOpen] = useState(false);

  // Theme
  const [theme, setTheme] = useState<string>(() => {
    try { return localStorage.getItem('fina-theme') || 'light'; } catch { return 'light'; }
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    try { localStorage.setItem('fina-theme', theme); } catch {}
  }, [theme]);

  // Helpers
  const closeTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  function openNew() {
    setEditingTx(null);
    setExpenseOpen(true);
  }

  function openEdit(tx: any) {
    setEditingTx(tx);
    setExpenseOpen(true);
  }

  function closeSheet() {
    setExpenseOpen(false);
    closeTimerRef.current = setTimeout(() => setEditingTx(null), 350);
  }

  function closeCatSheet() {
    setCatSheetOpen(false);
    setTimeout(() => setEditingCat(null), 350);
  }

  function handleLogout() {
    logout();
    navigate('/login');
  }

  function confirmDelete() {
    // TODO: call delete API for deletingTx
    setDeletingTx(null);
  }

  function cancelDelete() {
    setDeletingTx(null);
  }

  useEffect(() => {
    return () => {
      if (closeTimerRef.current) clearTimeout(closeTimerRef.current);
    };
  }, []);

  // Screens
  const screens: Record<string, React.ReactNode> = {
    home: <HomeEditorial onTab={setTab} />,
    gastos: <GastosScreen onTab={setTab} onEditTx={openEdit} onDeleteTx={(tx: any) => setDeletingTx(tx)} />,
    chat: <ChatScreen />,
    cats: (
      <CatsScreen
        onEditCat={(cat: any) => { setEditingCat(cat); setCatSheetOpen(true); }}
        onCreateCat={() => { setEditingCat(null); setCatSheetOpen(true); }}
        onEditBudget={() => {}}
      />
    ),
    reglas: <ReglasScreen />,
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100dvh',
      background: 'var(--bg)',
      position: 'relative',
      overflow: 'hidden',
      maxWidth: 512,
      margin: '0 auto',
      paddingTop: 'env(safe-area-inset-top, 0px)',
    }}>
      <TopBar
        onMenu={() => setDrawer(true)}
        onNotif={() => setNotifOpen(true)}
        onRefresh={refresh}
        balance={tab === 'gastos' ? undefined : undefined}
      />

      <div style={{ flex: 1, minHeight: 0, position: 'relative', overflowY: 'auto', overflowX: 'hidden' }}>
        {isChildRoute ? <Outlet /> : screens[tab]}
      </div>

      {!isChildRoute && <BottomBar tab={tab} onTab={setTab} />}

      {/* Overlays */}
      <Drawer
        open={drawer}
        onClose={() => setDrawer(false)}
        theme={theme}
        onTheme={setTheme}
        onLogout={handleLogout}
        onOpenPlans={() => setPlansOpen(true)}
        onOpenStories={() => setStoriesOpen(true)}
      />
      <PlansSheet open={plansOpen} onClose={() => setPlansOpen(false)} />
      <StoriesViewer open={storiesOpen} onClose={() => setStoriesOpen(false)} onNav={(t) => setTab(t)} />
      <NotificationsPanel open={notifOpen} onClose={() => setNotifOpen(false)} />
      <NewExpenseSheet open={expenseOpen} onClose={closeSheet} initial={editingTx} onDelete={setDeletingTx} />
      <CategoryEditSheet open={catSheetOpen} onClose={closeCatSheet} initial={editingCat} />
      <ConfirmDialog
        open={!!deletingTx}
        danger
        title="Eliminar movimiento"
        onConfirm={confirmDelete}
        onCancel={cancelDelete}
      />

      {/* Floating action button */}
      <button onClick={openNew} style={{
        position: 'absolute',
        right: 16,
        bottom: 100,
        width: 54,
        height: 54,
        borderRadius: 54,
        background: 'var(--lime)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        boxShadow: '0 6px 18px rgba(0,0,0,0.25)',
        zIndex: 70,
        border: 'none',
        cursor: 'pointer',
      }}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none">
          <path d="M12 5v14M5 12h14" stroke="var(--ink-stable)" strokeWidth="2.6" strokeLinecap="round" />
        </svg>
      </button>
    </div>
  );
}
