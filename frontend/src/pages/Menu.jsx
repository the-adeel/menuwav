import { useState, useEffect } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import API from '../services/api';
import { useAuth } from '../context/AuthContext';

const Menu = () => {
  const { restaurantId } = useParams();
  const [searchParams] = useSearchParams();
  const tableNumber = searchParams.get('table');
  const navigate = useNavigate();
  const { user, token } = useAuth();
  
  const [menuData, setMenuData] = useState([]);
  const [restaurant, setRestaurant] = useState(null);
  const [cart, setCart] = useState([]);
  const [loading, setLoading] = useState(true);
  const [orderPlaced, setOrderPlaced] = useState(false);

  useEffect(() => {
    fetchMenu();
  }, [restaurantId]);

  const fetchMenu = async () => {
    try {
      const res = await API.get(`/menus/${restaurantId}/public`);
      setMenuData(res.data);
      
      // Fetch restaurant info
      const restaurantRes = await API.get(`/restaurants/${restaurantId}`);
      setRestaurant(restaurantRes.data);
    } catch (err) {
      console.error('Error fetching menu:', err);
    } finally {
      setLoading(false);
    }
  };

  const addToCart = (menuItem) => {
    const existingItem = cart.find(item => item.menu_item_id === menuItem.id);
    if (existingItem) {
      setCart(cart.map(item =>
        item.menu_item_id === menuItem.id
          ? { ...item, quantity: item.quantity + 1 }
          : item
      ));
    } else {
      setCart([...cart, {
        menu_item_id: menuItem.id,
        quantity: 1,
        name: menuItem.name,
        price: menuItem.price
      }]);
    }
  };

  const updateQuantity = (menuItemId, quantity) => {
    if (quantity <= 0) {
      removeFromCart(menuItemId);
    } else {
      setCart(cart.map(item =>
        item.menu_item_id === menuItemId
          ? { ...item, quantity }
          : item
      ));
    }
  };

  const removeFromCart = (menuItemId) => {
    setCart(cart.filter(item => item.menu_item_id !== menuItemId));
  };

  const getTotal = () => {
    return cart.reduce((sum, item) => sum + (parseFloat(item.price) * item.quantity), 0);
  };

  const placeOrder = async () => {
    if (cart.length === 0) {
      alert('Your cart is empty');
      return;
    }

    try {
      const orderData = {
        restaurant_id: parseInt(restaurantId),
        table_number: tableNumber ? parseInt(tableNumber) : null,
        items: cart.map(item => ({
          menu_item_id: item.menu_item_id,
          quantity: item.quantity
        }))
      };

      await API.post('/orders/', orderData);
      setOrderPlaced(true);
      setCart([]);
      
      setTimeout(() => {
        setOrderPlaced(false);
      }, 3000);
    } catch (err) {
      console.error('Error placing order:', err);
      alert('Failed to place order. Please try again.');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Loading menu...</p>
      </div>
    );
  }

  if (!restaurant) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p>Restaurant not found</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto p-4 md:p-8">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-4xl font-bold">{restaurant.name}</h1>
            {tableNumber && (
              <p className="text-gray-600 mt-2">Table {tableNumber}</p>
            )}
          </div>
          {user && (
            <button
              onClick={() => navigate('/dashboard')}
              className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
            >
              My Dashboard
            </button>
          )}
        </div>

        {orderPlaced && (
          <div className="bg-green-100 border border-green-400 text-green-700 px-4 py-3 rounded mb-4">
            Order placed successfully!
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Menu Section */}
          <div className="lg:col-span-2">
            {menuData.length === 0 ? (
              <p className="text-center text-gray-600">No menu available</p>
            ) : (
              menuData.map((menuGroup) => (
                <div key={menuGroup.menu.id} className="mb-12">
                  <h2 className="text-2xl font-semibold mb-6 border-b pb-2">
                    {menuGroup.menu.name}
                  </h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {menuGroup.items.map((item) => (
                      <div key={item.id} className="bg-white shadow-md rounded-lg p-6 hover:shadow-lg transition">
                        <h3 className="text-xl font-bold">{item.name}</h3>
                        {item.description && (
                          <p className="text-gray-600 mt-2">{item.description}</p>
                        )}
                        <div className="flex justify-between items-center mt-4">
                          <p className="text-lg font-semibold text-green-600">${item.price}</p>
                          <button
                            onClick={() => addToCart(item)}
                            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
                          >
                            Add to Cart
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Cart Section */}
          <div className="lg:col-span-1">
            <div className="bg-white shadow-lg rounded-lg p-6 sticky top-4">
              <h2 className="text-2xl font-bold mb-4">Your Cart</h2>
              {cart.length === 0 ? (
                <p className="text-gray-600">Your cart is empty</p>
              ) : (
                <>
                  <div className="space-y-3 mb-4">
                    {cart.map((item) => (
                      <div key={item.menu_item_id} className="border-b pb-3">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <p className="font-semibold">{item.name}</p>
                            <p className="text-sm text-gray-600">${item.price} each</p>
                          </div>
                          <button
                            onClick={() => removeFromCart(item.menu_item_id)}
                            className="text-red-600 hover:text-red-800 ml-2"
                          >
                            ×
                          </button>
                        </div>
                        <div className="flex items-center gap-2 mt-2">
                          <button
                            onClick={() => updateQuantity(item.menu_item_id, item.quantity - 1)}
                            className="bg-gray-200 px-2 py-1 rounded"
                          >
                            −
                          </button>
                          <span className="px-3">{item.quantity}</span>
                          <button
                            onClick={() => updateQuantity(item.menu_item_id, item.quantity + 1)}
                            className="bg-gray-200 px-2 py-1 rounded"
                          >
                            +
                          </button>
                          <span className="ml-auto font-semibold">
                            ${(parseFloat(item.price) * item.quantity).toFixed(2)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="border-t pt-4">
                    <div className="flex justify-between items-center mb-4">
                      <span className="text-xl font-bold">Total:</span>
                      <span className="text-xl font-bold text-green-600">
                        ${getTotal().toFixed(2)}
                      </span>
                    </div>
                    <button
                      onClick={placeOrder}
                      className="w-full bg-green-600 text-white py-3 rounded hover:bg-green-700 font-semibold"
                    >
                      Place Order
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Menu;

