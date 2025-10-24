// src/App.jsx
import { BrowserRouter as Router, Routes, Route, Navigate } from "react-router-dom";
import { useEffect, useState } from "react";
import Login from "./pages/Login";
import AdminHome from "./pages/Admin/Admin_Home";
import AdminOfficers from "./pages/Admin/Admin_Officers";
import AdminManageCrops from "./pages/Admin/Admin_ManageCrops";
import OfficerHome from "./pages/Officer/Officer_Home";
import AdminLayout from "./layouts/AdminLayout";
import OfficerLayout from "./layouts/OfficerLayout";
import { AuthContext } from "./middle/AuthContext";

function ProtectedRoute({ children }) {
  const [loading, setLoading] = useState(true);
  const [user, setUser] = useState(null);

  useEffect(() => {
    let isMounted = true;
    fetch(`${import.meta.env.VITE_API_BASE || 'http://localhost:5000'}/api/auth/me`, {
      method: "GET",
      credentials: "include",
    })
      .then(async (res) => {
        if (!isMounted) return;
        if (!res.ok) {
          setUser(null);
          return;
        }
        const data = await res.json().catch(() => null);
        setUser(data || null);
      })
      .catch(() => {
        if (!isMounted) return;
        setUser(null);
      })
      .finally(() => {
        if (!isMounted) return;
        setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  if (loading) return <div className="p-6">Checking session...</div>;
  if (!user) return <Navigate to="/login" replace />;

  return (
    <AuthContext.Provider value={user}>
      {children}
    </AuthContext.Provider>
  );
}

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/admin"
          element={
            <ProtectedRoute>
              <AdminLayout>
                <AdminHome />
              </AdminLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/officers"
          element={
            <ProtectedRoute>
              <AdminLayout>
                <AdminOfficers />
              </AdminLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/crops"
          element={
            <ProtectedRoute>
              <AdminLayout>
                <AdminManageCrops />
              </AdminLayout>
            </ProtectedRoute>
          }
        />
        <Route
          path="/officer"
          element={
            <ProtectedRoute>
              <OfficerLayout>
                <OfficerHome />
              </OfficerLayout>
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/admin" replace />} />
      </Routes>
    </Router>
  );
}