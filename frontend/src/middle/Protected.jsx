// src/middle/Protected.jsx
import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";
import { AuthContext } from "./AuthContext";

const API = "http://localhost:5000";

function normalizeRole(role) {
  if (!role) return undefined;
  const r = String(role).toLowerCase();
  if (["admin", "company_admin", "superadmin"].includes(r)) return "Admin";
  if (["officer", "company_officer"].includes(r)) return "Officer";
  return "Officer";
}

export default function Protected({ children }) {
  const [state, setState] = useState({ loading: true, user: null });

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await fetch(`${API}/api/auth/me`, { credentials: "include" });
        if (!alive) return;
        if (!res.ok) {
          setState({ loading: false, user: null });
          return;
        }
        const data = await res.json();
        setState({
          loading: false,
          user: {
            _id: data._id,
            username: data.username,
            company_id: data.company_id,
            role: normalizeRole(data.role),
          },
        });
      } catch {
        if (!alive) return;
        setState({ loading: false, user: null });
      }
    })();
    return () => { alive = false; };
  }, []);

  if (state.loading) return <div className="p-6">Checking session…</div>;
  if (!state.user) return <Navigate to="/login" replace />;

  return (
    <AuthContext.Provider value={state.user}>
      {children}
    </AuthContext.Provider>
  );
}




// // src/middle/Protected.jsx
// import { useEffect, useState } from "react";
// import { Navigate } from "react-router-dom";
// import { AuthContext } from "./AuthContext";

// const API = "http://localhost:5000";

// export default function Protected({ children }) {
//   const [state, setState] = useState({ loading: true, user: null });

//   useEffect(() => {
//     let alive = true;
//     (async () => {
//       try {
//         const res = await fetch(`${API}/api/auth/me`, { credentials: "include" });
//         if (!alive) return;
//         if (!res.ok) {
//           setState({ loading: false, user: null });
//           return;
//         }
//         const data = await res.json();
//         setState({ loading: false, user: data });
//       } catch {
//         if (!alive) return;
//         setState({ loading: false, user: null });
//       }
//     })();
//     return () => { alive = false; };
//   }, []);

//   if (state.loading) return <div className="p-6">Checking session…</div>;
//   if (!state.user) return <Navigate to="/login" replace />;

//   return (
//     <AuthContext.Provider value={state.user}>
//       {children}
//     </AuthContext.Provider>
//   );
// }
