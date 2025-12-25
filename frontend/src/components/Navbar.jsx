import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <nav className="bg-gray-800 text-white p-4">
      <div className="max-w-7xl mx-auto flex justify-between items-center">
        <Link to="/" className="text-xl font-bold">Restaurant App</Link>
        <div className="space-x-6">
          {!user && <Link to="/" className="hover:text-gray-300">Menu</Link>}
          
          {/* Superadmin Navigation */}
          {user?.role === 'superadmin' && (
            <>
              <Link to="/superadmin" className="hover:text-gray-300 font-semibold">Superadmin Panel</Link>
            </>
          )}
          
          {/* Restaurant Admin Navigation */}
          {user?.role === 'restaurant_admin' && (
            <>
              <Link to="/admin" className="hover:text-gray-300 font-semibold">Restaurant Admin</Link>
            </>
          )}
          
          {/* Customer Navigation */}
          {user?.role === 'customer' && (
            <>
              <Link to="/dashboard" className="hover:text-gray-300">My Dashboard</Link>
            </>
          )}
          
          {user ? (
            <>
              <span className="text-gray-400">|</span>
              <span className="text-sm text-gray-400">Logged in as: {user.username}</span>
              <button onClick={handleLogout} className="hover:text-gray-300">Logout</button>
            </>
          ) : (
            <>
              <Link to="/login" className="hover:text-gray-300">Login</Link>
              <Link to="/signup" className="hover:text-gray-300">Sign Up</Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
};

export default Navbar;