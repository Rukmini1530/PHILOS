import { Search, Filter, Trash2, Shield, UserCheck, UserX, User } from "lucide-react";
import { useState, useMemo } from "react";
import { cn } from "../../utils/helpers";
import Button from "../ui/Button";
import Input from "../ui/Input";

const SuperuserIcon = () => (
  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.692 9-11.622 0-1.042-.13-2.052-.382-3.016z" stroke="currentColor" />
  </svg>
);

const ActiveIcon = () => (
  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
);

const InactiveIcon = () => (
  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
  </svg>
);

const DeleteIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" stroke="currentColor" />
  </svg>
);

const AdminUsersTable = ({ users, onDeleteUser, loading, error }) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [filterStatus, setFilterStatus] = useState("all"); // all, active, inactive, superuser

  const filteredUsers = useMemo(() => {
    return users.filter((user) => {
      const matchesSearch = user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           user.username.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = filterStatus === "all" ||
        (filterStatus === "superuser" && user.is_superuser) ||
        (filterStatus === "active" && user.is_active && !user.is_superuser) ||
        (filterStatus === "inactive" && !user.is_active);
      return matchesSearch && matchesStatus;
    });
  }, [users, searchTerm, filterStatus]);

  const handleDelete = (userId, e) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this user and all their datasets? This cannot be undone.")) {
      return;
    }
    onDeleteUser(userId);
  };

  if (loading) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-gray-800">
          <h2 className="text-lg font-semibold">Users</h2>
        </div>
        <div className="p-4 space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-16 bg-gray-800/50 animate-pulse rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-gray-800">
          <h2 className="text-lg font-semibold">Users</h2>
        </div>
        <div className="p-6 text-center">
          <p className="text-red-400">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      {/* Header with Search and Filter */}
      <div className="p-4 border-b border-gray-800 flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <div className="relative w-full sm:w-64">
          <input
            type="text"
            placeholder="Search users..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Users</option>
          <option value="superuser">Superusers</option>
          <option value="active">Active Users</option>
          <option value="inactive">Inactive Users</option>
        </select>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-800 bg-gray-800/50">
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">User</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider hidden md:table-cell">Role</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider hidden lg:table-cell">Datasets</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider hidden lg:table-cell">Storage</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider hidden md:table-cell">Status</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider hidden lg:table-cell">Last Active</th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {users.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-gray-400">
                  <p className="text-lg font-medium mb-1">No users found</p>
                  <p className="text-sm text-gray-500">Try adjusting your search or filter</p>
                </td>
              </tr>
            ) : (
              users.map((user) => (
                <tr key={user.id} className="hover:bg-gray-800/50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-medium text-sm">
                        {user.username?.charAt(0)?.toUpperCase() || user.email?.charAt(0)?.toUpperCase() || "U"}
                      </div>
                      <div>
                        <p className="font-medium text-white truncate max-w-xs">{user.email}</p>
                        <p className="text-xs text-gray-400 truncate max-w-xs">{user.username}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 hidden md:table-cell">
                    <div className="flex items-center gap-2">
                      {user.is_superuser && (
                        <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-purple-500/20 text-purple-400 rounded-full">
                          <SuperuserIcon />
                          Superuser
                        </span>
                      )}
                      {!user.is_superuser && user.is_active && (
                        <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-green-500/20 text-green-400 rounded-full">
                          <ActiveIcon />
                          Active
                        </span>
                      )}
                      {!user.is_active && (
                        <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-red-500/20 text-red-400 rounded-full">
                          <InactiveIcon />
                          Inactive
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 hidden lg:table-cell text-sm text-gray-400">
                    {user.datasets_count ?? 0}
                  </td>
                  <td className="px-6 py-4 hidden lg:table-cell text-sm text-gray-400">
                    {user.storage_mb ? `${user.storage_mb} MB` : "0 MB"}
                  </td>
                  <td className="px-6 py-4 hidden md:table-cell">
                    {user.is_superuser ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-purple-500/20 text-purple-400 rounded-full">
                        <SuperuserIcon />
                        Superuser
                      </span>
                    ) : user.is_active ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-green-500/20 text-green-400 rounded-full">
                        <ActiveIcon />
                        Active
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-red-500/20 text-red-400 rounded-full">
                        <InactiveIcon />
                        Inactive
                      </span>
                    )}
                  </td>
                  <td className="px-6 py-4 hidden lg:table-cell text-sm text-gray-400">
                    {user.last_active ? new Date(user.last_active).toLocaleDateString() : "Never"}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (!confirm("Are you sure you want to delete this user and all their datasets? This cannot be undone.")) {
                          return;
                        }
                        onDeleteUser(user.id);
                      }}
                      className="text-red-400 hover:text-red-300 flex items-center gap-1 text-sm font-medium transition-colors"
                      title="Delete user and all their datasets"
                    >
                      <DeleteIcon />
                      <span className="hidden sm:inline">Delete</span>
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination placeholder - client-side for now */}
      {users.length > 0 && (
        <div className="p-4 border-t border-gray-800 flex items-center justify-between">
          <p className="text-sm text-gray-400">
            Showing {users.length} users
          </p>
        </div>
      )}
    </div>
  );
};

export default AdminUsersTable;