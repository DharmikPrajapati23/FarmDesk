// src/components/Officer_Navbar.jsx
import { useNavigate } from "react-router-dom";
import { useAuth } from "../middle/AuthContext";

const API = "http://localhost:5000";

export default function Officer_Navbar() {
  const navigate = useNavigate();
  const user = useAuth();

  const onLogout = async () => {
    try {
      await fetch(`${API}/api/auth/logout`, {
        method: "POST",
        credentials: "include",
      });
    } catch (e) {
      // optional: console.error(e);
    } finally {
      navigate("/login", { replace: true });
    }
  };

  return (
    <nav className="w-full bg-white border-b px-4 py-3 flex items-center justify-between shadow-sm">
      <div className="flex items-center gap-4">
        <div className="text-lg font-semibold text-gray-800">FarmDesk Officer</div>
        <div className="hidden sm:block text-sm text-gray-500">|</div>
        <div className="text-sm text-gray-600">
          {user?.company_id || "—"}
        </div>
      </div>
      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-700 font-medium">
          {user?.username || "Officer"}
        </span>
        <button
          onClick={onLogout}
          className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
        >
          Logout
        </button>
      </div>
    </nav>
  );
}



// // src/components/Officer_Navbar.jsx
// import { useNavigate } from "react-router-dom";
// import { useAuth } from "../middle/AuthContext";

// const API = "http://localhost:5000";

// export default function Officer_Navbar() {
//   const navigate = useNavigate();
//   const user = useAuth();

//   const onLogout = async () => {
//     try {
//       await fetch(`${API}/api/auth/logout`, {
//         method: "POST",
//         credentials: "include",
//       });
//     } catch {}
//     navigate("/login", { replace: true });
//   };

//   return (
//     <nav className="w-full bg-white border-b px-4 py-3 flex items-center justify-between shadow-sm">
//       <div className="flex items-center gap-4">
//         <div className="text-lg font-semibold text-gray-800">FarmDesk Officer</div>
//         <div className="hidden sm:block text-sm text-gray-500">|</div>
//         <div className="text-sm text-gray-600">
//           {user?.company_id}
//         </div>
//       </div>
//       <div className="flex items-center gap-4">
//         <span className="text-sm text-gray-700 font-medium">
//           {user?.username}
//         </span>
//         <button
//           onClick={onLogout}
//           className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
//         >
//           Logout
//         </button>
//       </div>
//     </nav>
//   );
// }