// src/pages/Admin_Officers.jsx
import { useEffect, useState } from "react";
import { useAuth } from "../../middle/AuthContext";

const API = "http://localhost:5000";

export default function Admin_Officers() {
  const user = useAuth(); // { _id, role, company_id, username, ... }
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [form, setForm] = useState({ username: "", password: "" });
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const load = async () => {
    setErr("");
    setLoading(true);
    try {
      const res = await fetch(`${API}/admin/officers`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error((await res.json()).error || "Failed to load officers");
      const data = await res.json();
      setItems(data.items || []);
    } catch (e) {
      setErr(e.message || "Failed to load officers");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const onChange = (e) => setForm((p) => ({ ...p, [e.target.name]: e.target.value }));

  const onCreate = async (e) => {
    e.preventDefault();
    setErr("");
    if (!form.username.trim() || !form.password.trim()) {
      setErr("Username and password are required");
      return;
    }
    setCreating(true);
    try {
      const res = await fetch(`${API}/admin/officers`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: form.username.trim(), password: form.password.trim() }),
      });
      if (!res.ok) throw new Error((await res.json()).error || "Failed to create officer");
      setForm({ username: "", password: "" });
      await load();
    } catch (e) {
      setErr(e.message || "Failed to create officer");
    } finally {
      setCreating(false);
    }
  };

  const onDelete = async (id) => {
    if (!id) return;
    if (!confirm("Delete this officer? This action cannot be undone.")) return;
    setErr("");
    setDeletingId(id);
    try {
      const res = await fetch(`${API}/admin/officers/${id}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (!res.ok) throw new Error((await res.json()).error || "Failed to delete officer");
      await load();
    } catch (e) {
      setErr(e.message || "Failed to delete officer");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Officers</h1>
          <p className="text-sm text-gray-500">Company: {user?.company_id}</p>
        </div>
      </header>

      <div className="bg-white border rounded-lg p-4">
        <h2 className="text-lg font-medium mb-3">Create New Officer</h2>
        <form onSubmit={onCreate} className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-sm text-gray-700">Username</label>
            <input
              name="username"
              value={form.username}
              onChange={onChange}
              className="mt-1 w-full border rounded px-3 py-2 focus:outline-none focus:ring focus:border-blue-400"
              placeholder="officer username"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-gray-700">Password</label>
            <input
              type="password"
              name="password"
              value={form.password}
              onChange={onChange}
              className="mt-1 w-full border rounded px-3 py-2 focus:outline-none focus:ring focus:border-blue-400"
              placeholder="temporary password"
              required
            />
          </div>
          <div className="flex items-end">
            <button
              type="submit"
              disabled={creating}
              className="w-full md:w-auto bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {creating ? "Creating..." : "Create Officer"}
            </button>
          </div>
        </form>
        {err && <p className="mt-2 text-sm text-red-600">{err}</p>}
      </div>

      <div className="bg-white border rounded-lg">
        <div className="p-4 border-b">
          <h2 className="text-lg font-medium">All Officers</h2>
        </div>
        <div className="divide-y">
          {loading ? (
            <div className="p-4 text-gray-500">Loading...</div>
          ) : items.length === 0 ? (
            <div className="p-4 text-gray-500">No officers found</div>
          ) : (
            items.map((o) => (
              <div key={o._id} className="p-4 flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 justify-between">
                <div className="min-w-0 flex-1">
                  <p className="font-medium break-words">{o.username}</p>
                  <p className="text-xs text-gray-500">Role: {o.role} · Company: {o.company_id}</p>
                  <p className="text-[10px] text-gray-400 break-all">ID: {o._id}</p>
                </div>
                <div className="flex items-center gap-2 sm:gap-3">
                  <button
                    onClick={() => onDelete(o._id)}
                    disabled={deletingId === o._id}
                    className="px-3 py-1.5 text-sm rounded border border-red-200 text-red-700 hover:bg-red-50 disabled:opacity-50"
                  >
                    {deletingId === o._id ? "Deleting..." : "Delete"}
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
