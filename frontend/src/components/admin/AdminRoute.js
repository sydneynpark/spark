import { useState, useEffect } from 'react';
import { Navigate } from 'react-router-dom';
import ApiService from '../../services/api';

// Guards /admin/* routes: confirms the stored token is still valid with the
// backend before rendering, and bounces to the login page otherwise. There's
// no homepage link into any of this -- the admin area is reached by going
// straight to the URL.
function AdminRoute({ children }) {
  const [status, setStatus] = useState('checking'); // 'checking' | 'authed' | 'unauthed'

  useEffect(() => {
    let cancelled = false;
    ApiService.verifyAdminSession().then(ok => {
      if (!cancelled) setStatus(ok ? 'authed' : 'unauthed');
    });
    return () => { cancelled = true; };
  }, []);

  if (status === 'checking') return <div className="admin-page"><p>Checking session...</p></div>;
  if (status === 'unauthed') return <Navigate to="/admin/login" replace />;
  return children;
}

export default AdminRoute;
