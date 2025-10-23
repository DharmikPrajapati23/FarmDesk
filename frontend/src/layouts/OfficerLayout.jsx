// src/layouts/OfficerLayout.jsx
import Officer_Navbar from "../components/Officer_Navbar";

export default function OfficerLayout({ children }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <Officer_Navbar />
      <div className="p-6">
        {children}
      </div>
    </div>
  );
}