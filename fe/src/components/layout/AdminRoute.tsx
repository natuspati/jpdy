import { type ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';

import AdminKeyModal from '@/components/admin/AdminKeyModal';
import Spinner from '@/components/ui/Spinner';
import { useAuth } from '@/hooks/useAuth';
import { useMe } from '@/hooks/useMe';

const AdminRoute = ({ children }: { children: ReactNode }) => {
  const { isAuthed } = useAuth();
  const { data: me, isError } = useMe();
  const location = useLocation();

  if (!isAuthed) return <Navigate to="/" replace state={{ from: location.pathname }} />;
  if (isError) return <Navigate to="/" replace />;
  // Never flash the key modal at an admin while the role is still loading.
  if (!me) return <Spinner />;
  if (me.role === 'admin') return <>{children}</>;
  if (me.admin_key_attempted) return <Navigate to="/" replace />;
  return <AdminKeyModal />;
};

export default AdminRoute;
