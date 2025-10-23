// src/pages/Admin_Home.jsx
import { useNavigate } from "react-router-dom";

export default function Admin_Home() {
  const nav = useNavigate();

  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-8">
        <h2 className="text-2xl font-semibold text-gray-800">Admin Dashboard</h2>
        <p className="text-gray-600 mt-1">Manage your company's officers and crops</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Officers management card */}
        <button
          onClick={() => nav("/admin/officers")}
          className="text-left bg-white border rounded-lg p-5 shadow-sm hover:shadow transition cursor-pointer"
        >
          <h3 className="text-lg font-semibold">Manage Officers</h3>
          <p className="mt-2 text-sm text-gray-600">
            Create new officers and view all officers in your company.
          </p>
          <div className="mt-4 inline-flex items-center text-blue-600">
            <span className="mr-1">Go to Officers</span>
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </button>

        {/* Crops & Rates management card */}
        <button
          onClick={() => nav("/admin/crops")}
          className="text-left bg-white border rounded-lg p-5 shadow-sm hover:shadow transition cursor-pointer"
        >
          <h3 className="text-lg font-semibold">Crops & Rates</h3>
          <p className="mt-2 text-sm text-gray-600">
            Manage crop list and pricing for your company.
          </p>
          <div className="mt-4 inline-flex items-center text-blue-600">
            <span className="mr-1">Manage Crops</span>
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
            </svg>
          </div>
        </button>

        {/* Placeholder card for future sections */}
        <div className="bg-white border rounded-lg p-5 shadow-sm">
          <h3 className="text-lg font-semibold">Company Stats</h3>
          <p className="mt-2 text-sm text-gray-600">Overview of submissions and activity.</p>
        </div>
      </div>
    </div>
  );
}






// // src/pages/Admin_Home.jsx
// import { useNavigate } from "react-router-dom";

// const API = "http://localhost:5000";

// export default function Admin_Home() {
//   const nav = useNavigate();

//   const logout = async () => {
//     try {
//       await fetch(`${API}/api/auth/logout`, {
//         method: "POST",
//         credentials: "include",
//       });
//     } catch {}
//     nav("/login", { replace: true });
//   };

//   return (
//     <div className="min-h-screen p-6">
//       <div className="max-w-3xl mx-auto flex items-center justify-between">
//         <h2 className="text-2xl font-semibold">Admin Home</h2>
//         <button
//           onClick={logout}
//           className="bg-gray-800 hover:bg-gray-900 text-white px-4 py-2 rounded"
//         >
//           Logout
//         </button>
//       </div>
//       <p className="mt-8 text-gray-700">Welcome, Company Admin.</p>
//     </div>
//   );
// }