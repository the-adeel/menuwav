import { useState, useEffect } from 'react';
import API from '../services/api';
import Navbar from '../components/Navbar';
import { QRCodeSVG } from 'qrcode.react';

const RestaurantAdmin = () => {
  const [restaurant, setRestaurant] = useState(null);
  const [menus, setMenus] = useState([]);
  const [newMenuName, setNewMenuName] = useState('');
  const [newItem, setNewItem] = useState({ name: '', description: '', price: '', menuId: '' });
  const [qrCodes, setQrCodes] = useState([]);
  const [numberOfTables, setNumberOfTables] = useState(1);
  const [orders, setOrders] = useState([]);
  const [orderStatusFilter, setOrderStatusFilter] = useState('');
  const [tableFilter, setTableFilter] = useState('');
  const [activeTab, setActiveTab] = useState('menu'); // 'menu', 'qr', 'orders'

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const res = await API.get('/restaurants/my-restaurant');
      setRestaurant(res.data);
      
      // Fetch menus
      const menuRes = await API.get(`/restaurants/${res.data.id}`);
      setMenus(menuRes.data.menus || []);
      
      // Fetch QR codes
      const qrRes = await API.get(`/restaurants/${res.data.id}/qr/list`);
      setQrCodes(qrRes.data);
      
      // Fetch orders
      fetchOrders(res.data.id);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchOrders = async (restaurantId) => {
    try {
      const params = new URLSearchParams();
      if (orderStatusFilter) params.append('status', orderStatusFilter);
      if (tableFilter) params.append('table_number', tableFilter);
      
      const res = await API.get(`/restaurants/${restaurantId}/orders?${params.toString()}`);
      setOrders(res.data);
    } catch (err) {
      console.error('Error fetching orders:', err);
    }
  };

  const createMenu = async (e) => {
    e.preventDefault();
    try {
      await API.post(`/menus/${restaurant.id}/menus`, { name: newMenuName });
      setNewMenuName('');
      fetchData();
    } catch (err) {
      alert('Failed to create menu');
    }
  };

  const addItem = async (e) => {
    e.preventDefault();
    try {
      await API.post(`/menus/${restaurant.id}/menus/${newItem.menuId}/items`, {
        name: newItem.name,
        description: newItem.description,
        price: parseFloat(newItem.price),
      });
      setNewItem({ name: '', description: '', price: '', menuId: '' });
      fetchData();
    } catch (err) {
      alert('Failed to add item');
    }
  };

  const generateTableQR = async () => {
    try {
      const res = await API.post(`/restaurants/${restaurant.id}/qr/generate-table`, {
        number_of_tables: numberOfTables,
      });
      setQrCodes([...qrCodes, ...res.data]);
      alert(`Generated ${res.data.length} QR codes for tables`);
    } catch (err) {
      alert('Failed to generate QR codes');
    }
  };

  const generateRestaurantQR = async () => {
    try {
      const res = await API.post(`/restaurants/${restaurant.id}/qr/generate-restaurant`);
      setQrCodes([...qrCodes, res.data]);
      alert('Restaurant QR code generated');
    } catch (err) {
      alert('Failed to generate QR code');
    }
  };

  const deleteQRCode = async (qrId) => {
    if (!window.confirm('Are you sure you want to delete this QR code?')) {
      return;
    }

    try {
      await API.delete(`/restaurants/${restaurant.id}/qr/${qrId}`);
      setQrCodes(qrCodes.filter(qr => qr.id !== qrId));
      alert('QR code deleted successfully');
    } catch (err) {
      alert('Failed to delete QR code');
    }
  };

  const updateOrderStatus = async (orderId, newStatus) => {
    try {
      await API.patch(`/orders/${orderId}/status`, { status: newStatus });
      fetchOrders(restaurant.id);
    } catch (err) {
      alert('Failed to update order status');
    }
  };

  useEffect(() => {
    if (restaurant && activeTab === 'orders') {
      fetchOrders(restaurant.id);
    }
  }, [orderStatusFilter, tableFilter, activeTab]);

  if (!restaurant) {
    return (
      <>
        <Navbar />
        <div className="p-8 text-center">Loading...</div>
      </>
    );
  }

  return (
    <>
      <Navbar />
      <div className="max-w-6xl mx-auto p-8">
        <h1 className="text-3xl font-bold mb-8">Restaurant Admin Panel - {restaurant.name}</h1>

        {/* Tabs */}
        <div className="flex gap-4 mb-6 border-b">
          <button
            onClick={() => setActiveTab('menu')}
            className={`pb-2 px-4 ${activeTab === 'menu' ? 'border-b-2 border-blue-600 font-semibold' : ''}`}
          >
            Menu Management
          </button>
          <button
            onClick={() => setActiveTab('qr')}
            className={`pb-2 px-4 ${activeTab === 'qr' ? 'border-b-2 border-blue-600 font-semibold' : ''}`}
          >
            QR Codes
          </button>
          <button
            onClick={() => setActiveTab('orders')}
            className={`pb-2 px-4 ${activeTab === 'orders' ? 'border-b-2 border-blue-600 font-semibold' : ''}`}
          >
            Orders
          </button>
        </div>

        {/* Menu Management Tab */}
        {activeTab === 'menu' && (
          <>
            <div className="bg-white shadow rounded-lg p-6 mb-8">
              <h2 className="text-2xl font-semibold mb-4">Create New Menu</h2>
              <form onSubmit={createMenu} className="flex gap-4">
                <input
                  type="text"
                  value={newMenuName}
                  onChange={(e) => setNewMenuName(e.target.value)}
                  placeholder="Menu name (e.g., Lunch Menu)"
                  className="flex-1 p-2 border rounded"
                  required
                />
                <button type="submit" className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700">
                  Create Menu
                </button>
              </form>
            </div>

            <div className="space-y-8">
              {menus.map((menu) => (
                <div key={menu.id} className="bg-white shadow rounded-lg p-6">
                  <h3 className="text-xl font-bold mb-4">{menu.name}</h3>
                  <form onSubmit={addItem} className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                    <input
                      type="text"
                      placeholder="Item name"
                      value={newItem.name}
                      onChange={(e) => setNewItem({ ...newItem, name: e.target.value, menuId: menu.id })}
                      className="p-2 border rounded"
                      required
                    />
                    <input
                      type="text"
                      placeholder="Description (optional)"
                      value={newItem.description}
                      onChange={(e) => setNewItem({ ...newItem, description: e.target.value })}
                      className="p-2 border rounded"
                    />
                    <input
                      type="number"
                      step="0.01"
                      placeholder="Price"
                      value={newItem.price}
                      onChange={(e) => setNewItem({ ...newItem, price: e.target.value })}
                      className="p-2 border rounded"
                      required
                    />
                    <button type="submit" className="bg-green-600 text-white py-2 rounded hover:bg-green-700">
                      Add Item
                    </button>
                  </form>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {menu.items?.map((item) => (
                      <div key={item.id} className="border p-4 rounded">
                        <p className="font-semibold">{item.name}</p>
                        <p className="text-sm text-gray-600">{item.description}</p>
                        <p className="text-green-600 font-bold">${item.price}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* QR Codes Tab */}
        {activeTab === 'qr' && (
          <div className="space-y-6">
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-2xl font-semibold mb-4">Generate QR Codes</h2>
              
              <div className="mb-6">
                <h3 className="text-lg font-semibold mb-2">Generate Per Table</h3>
                <div className="flex gap-4">
                  <input
                    type="number"
                    min="1"
                    value={numberOfTables}
                    onChange={(e) => setNumberOfTables(parseInt(e.target.value))}
                    placeholder="Number of tables"
                    className="p-2 border rounded"
                  />
                  <button
                    onClick={generateTableQR}
                    className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700"
                  >
                    Generate Table QR Codes
                  </button>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-semibold mb-2">Generate Restaurant QR</h3>
                <button
                  onClick={generateRestaurantQR}
                  className="bg-green-600 text-white px-6 py-2 rounded hover:bg-green-700"
                >
                  Generate Restaurant QR Code
                </button>
              </div>
            </div>

            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-2xl font-semibold mb-4">Generated QR Codes</h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {qrCodes.map((qr) => (
                  <div key={qr.id} className="border p-4 rounded text-center relative">
                    <button
                      onClick={() => deleteQRCode(qr.id)}
                      className="absolute top-2 right-2 bg-red-500 text-white px-2 py-1 rounded text-xs hover:bg-red-600"
                    >
                      Delete
                    </button>
                    <p className="font-semibold mb-2">
                      {qr.qr_type === 'table' ? `Table ${qr.table_number}` : 'Restaurant QR'}
                    </p>
                    <QRCodeSVG value={qr.qr_data} size={200} />
                    <p className="text-xs text-gray-600 mt-2 break-all">{qr.qr_data}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Orders Tab */}
        {activeTab === 'orders' && (
          <div className="space-y-6">
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-2xl font-semibold mb-4">Orders</h2>
              
              <div className="flex gap-4 mb-4">
                <select
                  value={orderStatusFilter}
                  onChange={(e) => setOrderStatusFilter(e.target.value)}
                  className="p-2 border rounded"
                >
                  <option value="">All Statuses</option>
                  <option value="pending">Pending</option>
                  <option value="confirmed">Confirmed</option>
                  <option value="preparing">Preparing</option>
                  <option value="ready">Ready</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
                <input
                  type="number"
                  value={tableFilter}
                  onChange={(e) => setTableFilter(e.target.value)}
                  placeholder="Filter by table number"
                  className="p-2 border rounded"
                />
              </div>

              <div className="space-y-4">
                {orders.map((order) => (
                  <div key={order.id} className="border p-4 rounded">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <p className="font-semibold">Order #{order.id}</p>
                        <p className="text-sm text-gray-600">
                          {new Date(order.created_at).toLocaleString()}
                        </p>
                        {order.table_number && (
                          <p className="text-sm text-gray-600">Table: {order.table_number}</p>
                        )}
                        {order.customer_username && (
                          <p className="text-sm text-gray-600">Customer: {order.customer_username}</p>
                        )}
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
                    <div className="mb-2">
                      <p className="text-sm font-semibold">Items:</p>
                      <ul className="text-sm text-gray-600 ml-4">
                        {order.items?.map((item, idx) => (
                          <li key={idx}>
                            {item.quantity}x {item.menu_item.name} - ${item.price_at_time}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <div className="flex gap-2">
                      <select
                        value={order.status}
                        onChange={(e) => updateOrderStatus(order.id, e.target.value)}
                        className="p-2 border rounded text-sm"
                      >
                        <option value="pending">Pending</option>
                        <option value="confirmed">Confirmed</option>
                        <option value="preparing">Preparing</option>
                        <option value="ready">Ready</option>
                        <option value="completed">Completed</option>
                        <option value="cancelled">Cancelled</option>
                      </select>
                    </div>
                  </div>
                ))}
                {orders.length === 0 && <p className="text-gray-600">No orders found</p>}
              </div>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

export default RestaurantAdmin;