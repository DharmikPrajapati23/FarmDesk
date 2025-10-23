// src/layouts/AdminLayout.jsx
import Admin_Navbar from "../components/Admin_Navbar";

export default function AdminLayout({ children }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <Admin_Navbar />
      <div className="p-6">
        {children}
      </div>
    </div>
  );
}