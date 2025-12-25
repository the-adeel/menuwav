import { useState, useEffect } from 'react';
import API from '../services/api';
import Navbar from '../components/Navbar';
import { useAuth } from '../context/AuthContext';

const SuperAdmin = () => {
  const { user } = useAuth();
  const [name, setName] = useState('');
  const [message, setMessage] = useState('');
  const [pendingRestaurants, setPendingRestaurants] = useState([]);
  const [allRestaurants, setAllRestaurants] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('pending'); // 'pending', 'all', 'create'

  useEffect(() => {
    fetchPendingRestaurants();
    fetchAllRestaurants();
  }, []);

  const fetchPendingRestaurants = async () => {
    try {
      const res = await API.get('/restaurants/pending');
      setPendingRestaurants(res.data);
    } catch (err) {
      console.error('Error fetching pending restaurants:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchAllRestaurants = async () => {
    try {
      const res = await API.get('/restaurants/');
      setAllRestaurants(res.data);
    } catch (err) {
      console.error('Error fetching all restaurants:', err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const res = await API.post('/restaurants/', { name });
      setMessage(`Restaurant "${res.data.name}" created successfully! ID: ${res.data.id}`);
      setName('');
    } catch (err) {
      setMessage('Failed to create restaurant');
    }
  };

  const handleApprove = async (restaurantId) => {
    try {
      await API.post(`/restaurants/${restaurantId}/approve`);
      setMessage('Restaurant approved successfully!');
      // Refresh both lists
      await fetchPendingRestaurants();
      await fetchAllRestaurants();
      setLoading(false);
    } catch (err) {
      setMessage('Failed to approve restaurant: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleDisapprove = async (restaurantId) => {
    if (!window.confirm('Are you sure you want to disapprove this restaurant? This will delete the restaurant and the owner user.')) {
      return;
    }
    try {
      await API.post(`/restaurants/${restaurantId}/disapprove`);
      setMessage('Restaurant disapproved and deleted successfully!');
      // Refresh both lists
      await fetchPendingRestaurants();
      await fetchAllRestaurants();
      setLoading(false);
    } catch (err) {
      setMessage('Failed to disapprove restaurant: ' + (err.response?.data?.detail || err.message));
    }
  };

  if (!user || user.role !== 'superadmin') {
    return (
      <>
        <Navbar />
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <h1 className="text-2xl font-bold text-red-600 mb-4">Access Denied</h1>
            <p className="text-gray-600">You don't have permission to access this page.</p>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <Navbar />
      <div className="max-w-6xl mx-auto p-8">
        <div className="mb-6">
          <h1 className="text-3xl font-bold mb-2">Superadmin Panel</h1>
          <p className="text-gray-600">Manage restaurants and system settings</p>
        </div>
        
        {message && (
          <div className={`mb-4 p-4 rounded ${message.includes('success') ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
            {message}
            <button 
              onClick={() => setMessage('')} 
              className="float-right text-sm underline"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-4 mb-6 border-b">
          <button
            onClick={() => setActiveTab('pending')}
            className={`pb-2 px-4 ${activeTab === 'pending' ? 'border-b-2 border-blue-600 font-semibold' : ''}`}
          >
            Pending Restaurants ({pendingRestaurants.length})
          </button>
          <button
            onClick={() => setActiveTab('all')}
            className={`pb-2 px-4 ${activeTab === 'all' ? 'border-b-2 border-blue-600 font-semibold' : ''}`}
          >
            All Restaurants ({allRestaurants.length})
          </button>
          <button
            onClick={() => setActiveTab('create')}
            className={`pb-2 px-4 ${activeTab === 'create' ? 'border-b-2 border-blue-600 font-semibold' : ''}`}
          >
            Create Restaurant
          </button>
        </div>

        {/* Pending Restaurants Tab */}
        {activeTab === 'pending' && (
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-2xl font-semibold mb-4">Pending Restaurant Approvals</h2>
            {loading ? (
              <p>Loading...</p>
            ) : pendingRestaurants.length === 0 ? (
              <p className="text-gray-600">No pending restaurants</p>
            ) : (
              <div className="space-y-4">
                {pendingRestaurants.map((restaurant) => (
                  <div key={restaurant.id} className="border p-4 rounded hover:shadow-md transition">
                    <h3 className="text-xl font-bold">{restaurant.name}</h3>
                    <p className="text-sm text-gray-600">Owner: {restaurant.owner_username}</p>
                    {restaurant.address && <p className="text-sm text-gray-600">Address: {restaurant.address}</p>}
                    {restaurant.phone && <p className="text-sm text-gray-600">Phone: {restaurant.phone}</p>}
                    {restaurant.email && <p className="text-sm text-gray-600">Email: {restaurant.email}</p>}
                    <div className="mt-4 flex gap-2">
                      <button
                        onClick={() => handleApprove(restaurant.id)}
                        className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                      >
                        Approve
                      </button>
                      <button
                        onClick={() => handleDisapprove(restaurant.id)}
                        className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
                      >
                        Disapprove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* All Restaurants Tab */}
        {activeTab === 'all' && (
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-2xl font-semibold mb-4">All Restaurants</h2>
            {allRestaurants.length === 0 ? (
              <p className="text-gray-600">No restaurants found</p>
            ) : (
              <div className="space-y-4">
                {allRestaurants.map((restaurant) => {
                  const isApproved = restaurant.is_approved === true || restaurant.is_approved === 'true';
                  return (
                    <div key={restaurant.id} className="border p-4 rounded">
                      <div className="flex justify-between items-start">
                        <div>
                          <h3 className="text-xl font-bold">{restaurant.name}</h3>
                          <p className="text-sm text-gray-600">ID: {restaurant.id}</p>
                          {restaurant.owner_username && (
                            <p className="text-sm text-gray-600">Owner: {restaurant.owner_username}</p>
                          )}
                          <p className={`text-sm ${isApproved ? 'text-green-600' : 'text-yellow-600'}`}>
                            Status: {isApproved ? 'Approved' : 'Pending'}
                          </p>
                        </div>
                        {!isApproved && (
                          <div className="flex gap-2">
                            <button
                              onClick={() => handleApprove(restaurant.id)}
                              className="bg-green-600 text-white px-3 py-1 rounded text-sm hover:bg-green-700"
                            >
                              Approve
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

        {/* Create Restaurant Tab */}
        {activeTab === 'create' && (
          <div className="bg-white shadow rounded-lg p-6">
            <h2 className="text-2xl font-semibold mb-4">Create New Restaurant</h2>
            <p className="text-gray-600 mb-4">Create a restaurant manually (restaurants can also sign up and wait for approval)</p>
            <form onSubmit={handleSubmit}>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Restaurant name"
                className="w-full p-3 border rounded mb-4"
                required
              />
              <button type="submit" className="w-full bg-purple-600 text-white py-3 rounded hover:bg-purple-700">
                Create Restaurant
              </button>
            </form>
          </div>
        )}
      </div>
    </>
  );
};

export default SuperAdmin;