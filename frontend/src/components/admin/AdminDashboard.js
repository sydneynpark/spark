import { Link, useNavigate } from 'react-router-dom';
import ApiService from '../../services/api';

function AdminDashboard() {
  const navigate = useNavigate();

  function handleLogout() {
    ApiService.clearAdminToken();
    navigate('/admin/login');
  }

  return (
    <div className="admin-page admin-dashboard">
      <div className="admin-dashboard-header">
        <h2>Admin</h2>
        <button className="admin-logout-button" onClick={handleLogout}>Log Out</button>
      </div>
      <div className="admin-action-list">
        <Link className="admin-action-button" to="/admin/books/new">Upload Book Review</Link>
        <Link className="admin-action-button" to="/admin/photos/upload">Upload Bird Photos</Link>
      </div>
    </div>
  );
}

export default AdminDashboard;
