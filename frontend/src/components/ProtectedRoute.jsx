import { useAuth } from '../context/AuthContext';
import { Navigate } from 'react-router-dom';

const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, token, loading } = useAuth();

  // Show loading while checking auth
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Loading...</p>
      </div>
    );
  }

  // Redirect to login if no token
  if (!token) {
    return <Navigate to="/login" replace />;
  }

  // Redirect if user doesn't have required role
  if (allowedRoles && user && !allowedRoles.includes(user.role)) {
    // Redirect based on user's actual role
    if (user.role === 'superadmin') {
      return <Navigate to="/superadmin" replace />;
    } else if (user.role === 'restaurant_admin') {
      return <Navigate to="/admin" replace />;
    } else if (user.role === 'customer') {
      return <Navigate to="/dashboard" replace />;
    }
    return <Navigate to="/" replace />;
  }

  // If user is null but token exists, token might be invalid
  if (!user && token) {
    return <Navigate to="/login" replace />;
  }

  return children;
};

export default ProtectedRoute;