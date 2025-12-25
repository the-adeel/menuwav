// src/pages/NotFound.jsx
import { Link } from 'react-router-dom';
import Navbar from '../components/Navbar';

const NotFound = () => (
  <>
    <Navbar />
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <h1 className="text-6xl font-bold text-gray-800">404</h1>
        <p className="text-2xl mt-4">Page Not Found</p>
        <Link to="/" className="mt-8 inline-block bg-blue-600 text-white px-6 py-3 rounded hover:bg-blue-700">
          Go Home
        </Link>
      </div>
    </div>
  </>
);

export default NotFound;