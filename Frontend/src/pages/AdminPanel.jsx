import {
  Activity,
  BarChart3,
  Database,
  HardDrive,
  LogOut,
  Trash2,
  Users,
  Shield,
  UserCheck,
  UserX,
  Eye,
  Globe,
  Moon,
  Sparkles,
  AlertTriangle,
} from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Button from "../components/ui/Button";
import api from "../services/api";
import AdminStatsCards from "../components/admin/AdminStatsCards";
import AdminUsersTable from "../components/admin/AdminUsersTable";
import AdminDatasetsTable from "../components/admin/AdminDatasetsTable";
import AdminActivityFeed from "../components/admin/AdminActivityFeed";
import { useApp } from "../context/AppContext";
import { cn } from "../utils/helpers";

const AdminPanel = () => {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [users, setUsers] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [activities, setActivities] = useState([]);
  const [activeTab, setActiveTab] = useState("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    loadAdminData();
  }, [activeTab]);

  const loadAdminData = async () => {
    setLoading(true);
    setError(null);

    try {
      if (activeTab === "overview") {
        const statsRes = await api.apiClient.get("/api/admin/stats");
        const activityRes = await api.apiClient.get("/api/admin/activity");
        setStats(statsRes.data);
        setActivities(activityRes.data.recent_activities);
      } else if (activeTab === "users") {
        const usersRes = await api.apiClient.get("/api/admin/users?limit=100");
        setUsers(usersRes.data.users);
      } else if (activeTab === "datasets") {
        const datasetsRes = await api.apiClient.get(
          "/api/admin/datasets?limit=100"
        );
        setDatasets(datasetsRes.data.datasets);
      } else if (activeTab === "activity") {
        const activityRes = await api.apiClient.get("/api/admin/activity");
        setActivities(activityRes.data.recent_activities);
      }
    } catch (err) {
      console.error("Failed to load admin data:", err);
      setError(err.response?.data?.detail || "Failed to load data");
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteUser = async (userId) => {
    if (
      !confirm(
        "Are you sure you want to delete this user and all their datasets? This cannot be undone."
      )
    ) {
      return;
    }

    try {
      await api.apiClient.delete(`/api/admin/users/${userId}`);
      setUsers(users.filter((u) => u.id !== userId));
    } catch (err) {
      console.error("Failed to delete user:", err);
    }
  };

  const handleDeleteDataset = async (datasetId) => {
    if (!confirm("Are you sure you want to delete this dataset?")) {
      return;
    }

    try {
      await api.apiClient.delete(`/api/admin/datasets/${datasetId}`);
      setDatasets(datasets.filter((d) => d.id !== datasetId));
    } catch (err) {
      console.error("Failed to delete dataset:", err);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem("astropixel_token");
    localStorage.removeItem("astropixel_user");
    window.location.href = "/login";
  };

  return (
    <div className="min-h-screen bg-gray-950">
      {/* Top Navigation */}
      <nav className="bg-gray-900 border-b border-gray-800 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <h1 className="text-2xl font-bold text-white">Admin Panel</h1>
          <button
            onClick={() => {
              localStorage.removeItem("astropixel_token");
              localStorage.removeItem("astropixel_user");
              window.location.href = "/login";
            }}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-800 rounded-lg transition-colors"
            title="Logout"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </nav>

      {/* Tabs */}
      <div className="bg-gray-900 border-b border-gray-800 sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-6">
          <div className="flex gap-8">
            {[
              { id: "overview", label: "Overview", icon: BarChart3 },
              { id: "users", label: "Users", icon: Users },
              { id: "datasets", label: "Datasets", icon: Database },
              { id: "activity", label: "Activity", icon: Activity },
            ].map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`px-4 py-4 border-b-2 transition-colors flex items-center gap-2 ${
                  activeTab === id
                    ? "border-blue-500 text-white"
                    : "border-transparent text-gray-400 hover:text-gray-300"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden sm:inline">{label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-6 py-8">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4 text-red-400">
            {error}
          </div>
        ) : (
          <>
            {/* Overview Tab */}
            {activeTab === "overview" && (
              <AdminStatsCards stats={stats} loading={false} error={null} />
            )}

            {/* Users Tab */}
            {activeTab === "users" && (
              <AdminUsersTable
                users={users}
                onDeleteUser={handleDeleteUser}
                loading={loading}
                error={error}
              />
            )}

            {/* Datasets Tab */}
            {activeTab === "datasets" && (
              <AdminDatasetsTable
                datasets={datasets}
                onDeleteDataset={handleDeleteDataset}
                loading={loading}
                error={error}
              />
            )}

            {/* Activity Tab */}
            {activeTab === "activity" && (
              <AdminActivityFeed
                activities={activities}
                loading={loading}
                error={error}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default AdminPanel;