import { Database, UserPlus, Calendar, Clock, Tag } from "lucide-react";
import { useState, useMemo } from "react";
import { cn } from "../../utils/helpers";
import { formatDate } from "../../utils/helpers";

const DatasetCreatedIcon = () => (
  <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10a2 2 0 002 2h12a2 2 0 002-2V9a2 2 0 00-2-2H6a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2h-2.586l-1.586-1.586A2 2 0 0011.172 0H5.828A2 2 0 013 3.828V6a2 2 0 012-2h12a2 2 0 012 2v10a2 2 0 01-2 2h-2.5" stroke="currentColor" />
  </svg>
);

const UserSignupIcon = () => (
  <svg className="w-6 h-6 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3a6 6 0 01-6-6v-1z" stroke="currentColor" />
  </svg>
);

const DefaultIcon = () => (
  <svg className="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.692 9-11.622 0-1.042-.13-2.052-.382-3.016z" stroke="currentColor" />
  </svg>
);

const getActivityIcon = (type) => {
  switch (type) {
    case "dataset_created":
      return <DatasetCreatedIcon />;
    case "user_signup":
      return <UserSignupIcon />;
    default:
      return <DefaultIcon />;
  }
};

const getActivityDescription = (activity) => {
  switch (activity.type) {
    case "dataset_created":
      return `Dataset "${activity.name}" created by ${activity.owner}`;
    case "user_signup":
      return `New user "${activity.email}" signed up`;
    default:
      return "Unknown activity";
  }
};

const AdminActivityFeed = ({ activities, loading, error }) => {
  const [filterType, setFilterType] = useState("all"); // all, dataset_created, user_signup

  const filteredActivities = useMemo(() => {
    return activities.filter((activity) => {
      if (filterType === "all") return true;
      return activity.type === filterType;
    });
  }, [activities, filterType]);

  if (loading) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-gray-800">
          <h2 className="text-lg font-semibold">Recent Activity</h2>
        </div>
        <div className="p-4 space-y-3">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-20 bg-gray-800/50 animate-pulse rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-gray-800">
          <h2 className="text-lg font-semibold">Recent Activity</h2>
        </div>
        <div className="p-6 text-center">
          <p className="text-red-400">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-gray-800 flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        <h2 className="text-lg font-semibold">Recent Activity</h2>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Activity</option>
          <option value="dataset_created">Dataset Uploads</option>
          <option value="user_signup">User Signups</option>
        </select>
      </div>

      {/* Activity Feed */}
      <div className="divide-y divide-gray-800">
        {filteredActivities.length === 0 ? (
          <div className="p-8 text-center">
            <p className="text-gray-400 text-lg mb-1">No activity found</p>
            <p className="text-gray-500 text-sm">Try adjusting your filter or check back later</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-800">
            {filteredActivities.map((activity, idx) => (
              <div key={idx} className="px-6 py-4 hover:bg-gray-800/50 transition-colors">
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 w-12 h-12 rounded-xl flex items-center justify-center bg-gray-800/50">
                    {getActivityIcon(activity.type)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-white font-medium text-sm">{getActivityDescription(activity)}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {activity.type === "dataset_created" ? (
                        <span>Owner: {activity.owner} | Status: {activity.processing_status}</span>
                      ) : null}
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      {new Date(activity.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminActivityFeed;