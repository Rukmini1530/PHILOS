import {
  Users,
  Database,
  HardDrive,
  Activity,
} from "lucide-react";
import { cn } from "../../utils/helpers";

const StatCard = ({ label, value, icon: IconProp, color, subtitle }) => {
  const colorStyles = {
    blue: "border-blue-500/30 bg-blue-500/10",
    green: "border-green-500/30 bg-green-500/10",
    orange: "border-orange-500/30 bg-orange-500/10",
    red: "border-red-500/30 bg-red-500/10",
  };

  const iconComponents = {
    Users,
    Database,
    HardDrive,
    Activity,
  };

  const IconComponent = iconComponents[IconProp] || Users;

  return (
    <div className={cn(
      "border rounded-xl p-6 transition-all hover:border-opacity-50",
      colorStyles[color]
    )}>
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-400 mb-1">{label}</p>
          <p className="text-3xl font-bold text-white truncate">{value}</p>
          {subtitle && <p className="text-xs text-gray-500 mt-1">{subtitle}</p>}
        </div>
        <div className="w-14 h-14 rounded-xl flex items-center justify-center flex-shrink-0 bg-gradient-to-br from-blue-500 to-purple-600/50">
          <Icon className="w-7 h-7 text-white" />
        </div>
      </div>
    </div>
  );
};

const AdminStatsCards = ({ stats, loading, error }) => {
  if (loading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="border border-gray-700/50 rounded-xl p-6 animate-pulse">
            <div className="h-4 bg-gray-700 rounded w-1/3 mb-2" />
            <div className="h-8 bg-gray-700 rounded w-1/2 mb-1" />
            <div className="h-4 bg-gray-700 rounded w-1/4" />
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-6 text-center">
        <p className="text-red-400">{error}</p>
      </div>
    );
  }

  if (!stats) {
    return null;
  }

  const statsData = [
    {
      label: "Total Users",
      value: stats.users?.total ?? 0,
      subtitle: `${stats.users?.created_today ?? 0} created today`,
      icon: Users,
      color: "blue",
    },
    {
      label: "Total Datasets",
      value: stats?.datasets?.total ?? 0,
      subtitle: `${stats.datasets?.user_uploads ?? 0} user uploads`,
      icon: Database,
      color: "green",
    },
    {
      label: "Storage Used",
      value: `${stats?.storage?.total_gb ?? 0} GB`,
      subtitle: `${stats?.storage?.avg_dataset_mp ?? 0} MP avg`,
      icon: HardDrive,
      color: "orange",
    },
    {
      label: "Processing",
      value: stats?.datasets?.processing ?? 0,
      subtitle: `${stats?.datasets?.completed ?? 0} completed`,
      icon: Activity,
      color: stats?.datasets?.failed > 0 ? "red" : "blue",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {statsData.map((stat, idx) => (
        <StatCard
          key={idx}
          label={stat.label}
          value={stat.value}
          icon={stat.icon}
          color={stat.color}
          subtitle={stat.subtitle}
        />
      ))}
    </div>
  );
};

export default AdminStatsCards;