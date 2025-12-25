import { useEffect, useState } from 'react';
import API from '../services/api';
import Navbar from '../components/Navbar';

const Home = () => {
  const [restaurants, setRestaurants] = useState([]);
  const [selectedRestaurant, setSelectedRestaurant] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRestaurants = async () => {
      try {
        // First, try to get list of restaurants
        const listRes = await API.get('/restaurants');
        if (listRes.data && listRes.data.length > 0) {
          // Get the first restaurant with menus
          const restaurantRes = await API.get(`/restaurants/${listRes.data[0].id}`);
          setSelectedRestaurant(restaurantRes.data);
          setRestaurants([restaurantRes.data]);
        } else {
          setRestaurants([]);
        }
        setLoading(false);
      } catch (err) {
        setLoading(false);
        console.error('Error fetching restaurants:', err);
      }
    };
    fetchRestaurants();
  }, []);

  if (loading) return <div className="p-8 text-center">Loading menu...</div>;

  if (!selectedRestaurant) return <div className="p-8 text-center">No restaurants available</div>;

  return (
    <>
      <Navbar />
      <div className="max-w-7xl mx-auto p-8">
        <h1 className="text-4xl font-bold mb-8 text-center">{selectedRestaurant.name} Menu</h1>
        {selectedRestaurant.menus?.length === 0 ? (
          <p className="text-center text-gray-600">No menus available yet.</p>
        ) : (
          selectedRestaurant.menus?.map((menu) => (
            <div key={menu.id} className="mb-12">
              <h2 className="text-2xl font-semibold mb-6 border-b pb-2">{menu.name}</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {menu.items?.map((item) => (
                  <div key={item.id} className="bg-white shadow-md rounded-lg p-6 hover:shadow-lg transition">
                    <h3 className="text-xl font-bold">{item.name}</h3>
                    {item.description && <p className="text-gray-600 mt-2">{item.description}</p>}
                    <p className="text-lg font-semibold text-green-600 mt-4">${item.price}</p>
                  </div>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </>
  );
};

export default Home;