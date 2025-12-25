import { useState, useEffect } from 'react';
import API from '../services/api';
import Navbar from '../components/Navbar';
import { useAuth } from '../context/AuthContext';

const CustomerDashboard = () => {
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [profile, setProfile] = useState({ email: '', phone: '' });
  const [editingProfile, setEditingProfile] = useState(false);

  useEffect(() => {
    fetchOrders();
    // Profile would be fetched from user data or separate endpoint
  }, []);

  const fetchOrders = async () => {
    try {
      const res = await API.get('/orders/my-orders');
      setOrders(res.data);
    } catch (err) {
      console.error('Error fetching orders:', err);
    }
  };

  const handleProfileUpdate = async (e) => {
    e.preventDefault();
    // Note: You may need to create a profile update endpoint
    // For now, this is a placeholder
    setEditingProfile(false);
  };

  return (
    <>
      <Navbar />
      <div className="max-w-4xl mx-auto p-8">
        <h1 className="text-3xl font-bold mb-8">Customer Dashboard</h1>
        <p className="text-gray-600 mb-6">Welcome, {user?.username}!</p>

        {/* Profile Section */}
        <div className="bg-white shadow rounded-lg p-6 mb-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-2xl font-semibold">Profile</h2>
            <button
              onClick={() => setEditingProfile(!editingProfile)}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              {editingProfile ? 'Cancel' : 'Edit'}
            </button>
          </div>
          
          {editingProfile ? (
            <form onSubmit={handleProfileUpdate}>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Email</label>
                <input
                  type="email"
                  value={profile.email}
                  onChange={(e) => setProfile({ ...profile, email: e.target.value })}
                  className="w-full p-2 border rounded"
                />
              </div>
              <div className="mb-4">
                <label className="block text-sm font-medium mb-2">Phone</label>
                <input
                  type="tel"
                  value={profile.phone}
                  onChange={(e) => setProfile({ ...profile, phone: e.target.value })}
                  className="w-full p-2 border rounded"
                />
              </div>
              <button
                type="submit"
                className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
              >
                Save Changes
              </button>
            </form>
          ) : (
            <div>
              <p className="text-gray-600"><strong>Email:</strong> {profile.email || 'Not set'}</p>
              <p className="text-gray-600"><strong>Phone:</strong> {profile.phone || 'Not set'}</p>
            </div>
          )}
        </div>

        {/* Order History Section */}
        <div className="bg-white shadow rounded-lg p-6">
          <h2 className="text-2xl font-semibold mb-4">Order History</h2>
          {orders.length === 0 ? (
            <p className="text-gray-600">No orders yet</p>
          ) : (
            <div className="space-y-4">
              {orders.map((order) => (
                <div key={order.id} className="border p-4 rounded">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <p className="font-semibold">Order #{order.id}</p>
                      <p className="text-sm text-gray-600">
                        {order.restaurant_name}
                      </p>
                      <p className="text-sm text-gray-600">
                        {new Date(order.created_at).toLocaleString()}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="font-bold text-lg">${order.total}</p>
                      <p className={`text-sm ${
                        order.status === 'completed' ? 'text-green-600' :
                        order.status === 'cancelled' ? 'text-red-600' :
                        'text-blue-600'
                      }`}>
                        {order.status.toUpperCase()}
                      </p>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm font-semibold">Items:</p>
                    <ul className="text-sm text-gray-600 ml-4">
                      {order.items?.map((item, idx) => (
                        <li key={idx}>
                          {item.quantity}x {item.menu_item.name} - ${item.price_at_time}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
};

export default CustomerDashboard;

