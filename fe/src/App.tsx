import { Navigate, Route, Routes } from 'react-router-dom';

import AppShell from '@/components/layout/AppShell';
import RequireAuth from '@/components/layout/RequireAuth';
import HomePage from '@/pages/HomePage';
import RegisterPage from '@/pages/RegisterPage';
import CategoriesPage from '@/pages/CategoriesPage';
import CategoryEditPage from '@/pages/CategoryEditPage';
import LobbyPage from '@/pages/LobbyPage';
import NotFoundPage from '@/pages/NotFoundPage';

const App = () => (
  <AppShell>
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/categories"
        element={
          <RequireAuth>
            <CategoriesPage />
          </RequireAuth>
        }
      />
      <Route
        path="/categories/:id"
        element={
          <RequireAuth>
            <CategoryEditPage />
          </RequireAuth>
        }
      />
      <Route
        path="/lobby/:id"
        element={
          <RequireAuth>
            <LobbyPage />
          </RequireAuth>
        }
      />
      <Route path="/404" element={<NotFoundPage />} />
      <Route path="*" element={<Navigate to="/404" replace />} />
    </Routes>
  </AppShell>
);

export default App;
