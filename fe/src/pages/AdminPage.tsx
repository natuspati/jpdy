import UserManagement from '@/components/admin/UserManagement';

const AdminPage = () => (
  <div className="lg:h-full">
    <div className="grid grid-cols-1 gap-6 lg:h-full lg:grid-cols-[3fr_2fr] lg:grid-rows-[minmax(0,1fr)]">
      <UserManagement />
    </div>
  </div>
);

export default AdminPage;
