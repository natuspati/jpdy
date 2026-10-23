import GameStats from '@/components/admin/GameStats';
import ServerManagement from '@/components/admin/ServerManagement';
import UserManagement from '@/components/admin/UserManagement';

const AdminPage = () => (
  <div className="lg:h-full">
    <div className="grid grid-cols-1 gap-6 lg:h-full lg:grid-cols-[3fr_2fr] lg:grid-rows-[minmax(0,1fr)]">
      <UserManagement />
      <div className="grid min-h-0 grid-cols-1 gap-6 lg:grid-rows-2">
        <ServerManagement />
        <GameStats />
      </div>
    </div>
  </div>
);

export default AdminPage;
