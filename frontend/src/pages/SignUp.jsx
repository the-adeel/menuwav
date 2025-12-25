import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import API from '../services/api';

const SignUp = () => {
  const [userType, setUserType] = useState('customer'); // 'customer' or 'restaurant'
  const [formData, setFormData] = useState({
    username: '',
    password: '',
    email: '',
    phone: '',
    restaurant_name: '',
    address: '',
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      const signupData = {
        username: formData.username,
        password: formData.password,
        role: userType === 'restaurant' ? 'restaurant_admin' : 'customer',
        email: formData.email || null,
        phone: formData.phone || null,
      };

      if (userType === 'restaurant') {
        signupData.restaurant_name = formData.restaurant_name;
        signupData.address = formData.address || null;
      }

      await API.post('/auth/signup', signupData);
      
      if (userType === 'restaurant') {
        setSuccess('Sign up successful! Your restaurant is pending approval. You will be able to login once approved.');
        setTimeout(() => {
          navigate('/login');
        }, 3000);
      } else {
        setSuccess('Sign up successful! Redirecting to login...');
        setTimeout(() => {
          navigate('/login');
        }, 1500);
      }
    } catch (err) {
      console.error('Signup error:', err);
      const errorMessage = err.response?.data?.detail || err.response?.data?.message || err.message || 'Sign up failed. Please try again.';
      setError(errorMessage);
      
      // If it's a validation error, show more details
      if (err.response?.status === 422) {
        const validationErrors = err.response?.data?.detail;
        if (Array.isArray(validationErrors)) {
          setError(validationErrors.map(e => e.msg || e.message).join(', '));
        } else if (typeof validationErrors === 'string') {
          setError(validationErrors);
        }
      }
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-100">
      <div className="bg-white p-8 rounded shadow-md w-full max-w-md">
        <h2 className="text-2xl font-bold mb-6">Sign Up</h2>
        
        {/* Toggle */}
        <div className="mb-6 flex gap-4">
          <button
            type="button"
            onClick={() => setUserType('customer')}
            className={`flex-1 py-2 px-4 rounded ${
              userType === 'customer'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700'
            }`}
          >
            Sign up as Customer
          </button>
          <button
            type="button"
            onClick={() => setUserType('restaurant')}
            className={`flex-1 py-2 px-4 rounded ${
              userType === 'restaurant'
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700'
            }`}
          >
            Sign up as Restaurant
          </button>
        </div>

        {error && <p className="text-red-500 mb-4">{error}</p>}
        {success && <p className="text-green-500 mb-4">{success}</p>}

        <form onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Username"
            value={formData.username}
            onChange={(e) => setFormData({ ...formData, username: e.target.value })}
            className="w-full p-2 border mb-4 rounded"
            required
          />
          <input
            type="password"
            placeholder="Password"
            value={formData.password}
            onChange={(e) => setFormData({ ...formData, password: e.target.value })}
            className="w-full p-2 border mb-4 rounded"
            required
          />
          <input
            type="email"
            placeholder="Email (optional)"
            value={formData.email}
            onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            className="w-full p-2 border mb-4 rounded"
          />
          <input
            type="tel"
            placeholder="Phone (optional)"
            value={formData.phone}
            onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
            className="w-full p-2 border mb-4 rounded"
          />

          {userType === 'restaurant' && (
            <>
              <input
                type="text"
                placeholder="Restaurant Name *"
                value={formData.restaurant_name}
                onChange={(e) => setFormData({ ...formData, restaurant_name: e.target.value })}
                className="w-full p-2 border mb-4 rounded"
                required
              />
              <textarea
                placeholder="Address (optional)"
                value={formData.address}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                className="w-full p-2 border mb-4 rounded"
                rows="3"
              />
            </>
          )}

          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
          >
            Sign Up
          </button>
        </form>

        <p className="mt-4 text-sm text-gray-600 text-center">
          Already have an account? <Link to="/login" className="text-blue-600">Login</Link>
        </p>
      </div>
    </div>
  );
};

export default SignUp;

