// src/pages/Admin/Admin_ManageCrops.jsx
import { useEffect, useState } from "react";
import { useAuth } from "../../middle/AuthContext";

const API = import.meta.env.VITE_API_BASE || "http://localhost:5000";

export default function Admin_ManageCrops() {
  const user = useAuth();
  const [crops, setCrops] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [form, setForm] = useState({ crop_name: "", rate_per_unit: "" });
  const [creating, setCreating] = useState(false);
  const [editingCrop, setEditingCrop] = useState(null);
  const [updating, setUpdating] = useState(false);
  const [deletingCrop, setDeletingCrop] = useState(null);

  const loadCrops = async () => {
    setErr("");
    setLoading(true);
    try {
      const res = await fetch(`${API}/admin/crops`, {
        credentials: "include",
      });
      if (!res.ok) throw new Error((await res.json()).error || "Failed to load crops");
      const data = await res.json();
      setCrops(data.crop_details || []);
    } catch (e) {
      setErr(e.message || "Failed to load crops");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCrops();
  }, []);

  const onChange = (e) => setForm((p) => ({ ...p, [e.target.name]: e.target.value }));

  const onAddCrop = async (e) => {
    e.preventDefault();
    setErr("");
    if (!form.crop_name.trim() || !form.rate_per_unit) {
      setErr("Crop name and rate per unit are required");
      return;
    }
    setCreating(true);
    try {
      const res = await fetch(`${API}/admin/crops`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          crop_name: form.crop_name.trim(),
          rate_per_unit: parseFloat(form.rate_per_unit)
        }),
      });
      if (!res.ok) throw new Error((await res.json()).error || "Failed to add crop");
      setForm({ crop_name: "", rate_per_unit: "" });
      await loadCrops();
    } catch (e) {
      setErr(e.message || "Failed to add crop");
    } finally {
      setCreating(false);
    }
  };

  const onEditCrop = (crop) => {
    setEditingCrop(crop);
    setForm({ crop_name: crop.crop_name, rate_per_unit: crop.rate_per_unit.toString() });
  };

  const onUpdateCrop = async (e) => {
    e.preventDefault();
    setErr("");
    if (!form.crop_name.trim() || !form.rate_per_unit) {
      setErr("Crop name and rate per unit are required");
      return;
    }
    setUpdating(true);
    try {
      const res = await fetch(`${API}/admin/crops/${editingCrop.crop_name}`, {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          crop_name: form.crop_name.trim(),
          rate_per_unit: parseFloat(form.rate_per_unit)
        }),
      });
      if (!res.ok) throw new Error((await res.json()).error || "Failed to update crop");
      setEditingCrop(null);
      setForm({ crop_name: "", rate_per_unit: "" });
      await loadCrops();
    } catch (e) {
      setErr(e.message || "Failed to update crop");
    } finally {
      setUpdating(false);
    }
  };

  const onDeleteCrop = async (cropName) => {
    if (!confirm(`Delete "${cropName}"? This action cannot be undone.`)) return;
    setErr("");
    setDeletingCrop(cropName);
    try {
      const res = await fetch(`${API}/admin/crops/${cropName}`, {
        method: "DELETE",
        credentials: "include",
      });
      if (!res.ok) throw new Error((await res.json()).error || "Failed to delete crop");
      await loadCrops();
    } catch (e) {
      setErr(e.message || "Failed to delete crop");
    } finally {
      setDeletingCrop(null);
    }
  };

  const cancelEdit = () => {
    setEditingCrop(null);
    setForm({ crop_name: "", rate_per_unit: "" });
  };

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Manage Crops & Rates</h1>
          <p className="text-sm text-gray-500">Company: {user?.company_id}</p>
        </div>
      </header>

      {/* Add/Edit Form */}
      <div className="bg-white border rounded-lg p-4">
        <h2 className="text-lg font-medium mb-3">
          {editingCrop ? "Edit Crop" : "Add New Crop"}
        </h2>
        <form onSubmit={editingCrop ? onUpdateCrop : onAddCrop} className="grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <label className="block text-sm text-gray-700">Crop Name</label>
            <input
              name="crop_name"
              value={form.crop_name}
              onChange={onChange}
              className="mt-1 w-full border rounded px-3 py-2 focus:outline-none focus:ring focus:border-blue-400"
              placeholder="e.g. Wheat, Rice, Corn"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-gray-700">Rate per Unit</label>
            <input
              name="rate_per_unit"
              type="number"
              step="0.01"
              min="0"
              value={form.rate_per_unit}
              onChange={onChange}
              className="mt-1 w-full border rounded px-3 py-2 focus:outline-none focus:ring focus:border-blue-400"
              placeholder="e.g. 150.50"
              required
            />
          </div>
          <div className="flex items-end gap-2">
            <button
              type="submit"
              disabled={creating || updating}
              className="flex-1 bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {creating ? "Adding..." : updating ? "Updating..." : editingCrop ? "Update Crop" : "Add Crop"}
            </button>
            {editingCrop && (
              <button
                type="button"
                onClick={cancelEdit}
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"
              >
                Cancel
              </button>
            )}
          </div>
        </form>
        {err && <p className="mt-2 text-sm text-red-600">{err}</p>}
      </div>

      {/* Crops List */}
      <div className="bg-white border rounded-lg">
        <div className="p-4 border-b">
          <h2 className="text-lg font-medium">Crops & Rates</h2>
        </div>
        <div className="divide-y">
          {loading ? (
            <div className="p-4 text-gray-500">Loading...</div>
          ) : crops.length === 0 ? (
            <div className="p-4 text-gray-500">No crops found. Add your first crop above.</div>
          ) : (
            crops.map((crop) => (
              <div key={crop.crop_name} className="p-4 flex flex-col sm:flex-row sm:items-center gap-3 sm:gap-4 justify-between">
                <div className="min-w-0 flex-1">
                  <p className="font-medium text-lg">{crop.crop_name}</p>
                  <p className="text-sm text-gray-600">
                    Rate: ₹{crop.rate_per_unit} per unit
                  </p>
                  <div className="mt-1 text-xs text-gray-400 space-y-1">
                    <p>Created: {new Date(crop.created_at).toLocaleDateString()} by <span className="font-medium text-gray-600">{crop.created_by}</span></p>
                    {crop.updated_at && crop.updated_at !== crop.created_at && (
                      <p>Updated: {new Date(crop.updated_at).toLocaleDateString()} by <span className="font-medium text-gray-600">{crop.updated_by}</span></p>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => onEditCrop(crop)}
                    className="px-3 py-1.5 text-sm rounded border border-blue-200 text-blue-700 hover:bg-blue-50"
                  >
                    Edit
                  </button>
                  <button
                    onClick={() => onDeleteCrop(crop.crop_name)}
                    disabled={deletingCrop === crop.crop_name}
                    className="px-3 py-1.5 text-sm rounded border border-red-200 text-red-700 hover:bg-red-50 disabled:opacity-50"
                  >
                    {deletingCrop === crop.crop_name ? "Deleting..." : "Delete"}
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