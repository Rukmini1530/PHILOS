import { Search, Filter, Trash2, Eye, Globe, Moon, Sparkles, AlertTriangle } from "lucide-react";
import { useState, useMemo } from "react";
import { cn } from "../../utils/helpers";

const EarthIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 01-9 9H9.75a9 9 0 010-18h.5a.75.75 0 01.419.137L15.113 4.138a.75.75 0 111.06 1.06l-5 10a.75.75 0 01-1.332.332L7.35 11.25a.75.75 0 01-.419-.137l-3-2.25a.75.75 0 01.286-1.286h1.5a3 3 0 016 0z" stroke="currentColor" />
  </svg>
);

const MarsIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3.055 11H5a2 2 0 012 2v1a2 2 0 002 2h2.586l.293.293a1 1 0 001.414 0l2.015-2.015a3 3 0 014.243 0L17 14.344a.75.75 0 10.707-1.707l-3-3a.75.75 0 010-1.06V8.707a.75.75 0 011.06-.707h.707a4.5 4.5 0 110 9H13a.75.75 0 000 1.5h.134a9.007 9.007 0 00.078 1.472.75.75 0 11-1.414.29L6.951 15.25a1.75 1.75 0 00-.458 1.195l.122.634a.75.75 0 11-1.48.23l-.353-.501a.75.75 0 01.206-.798h.5a3.001 3.001 0 001.17-2.312l1.283-2.547a.75.75 0 011.139-.674h.024a4.501 4.5 0 014.5-4.5h.01v.008c0 .782-.226 1.514-.612 2.154a4.483 4.483 0 01-1.179 2.138.75.75 0 11-1.414.289l-.1-.341a.75.75 0 01-.23-.572l-.11-.776a.75.75 0 00-.571-.23H6a.75.75 0 01-.75-.75v-1.5c0-.414.336-.75.75-.75h2.48a3.001 3.001 0 012.45-1.44 3.001 3.001 0 00-.24-1.071l-.166-.501a.75.75 0 01.52-.965h.5a.75.75 0 10-.817-1.486l-.421-.089a.75.75 0 11-.475-1.07l.34-1.198a.75.75 0 01.912-.662h.022a.75.75 0 01.31.22l.489.654.087.235a.75.75 0 11-.21.95l-.501.371a.75.75 0 01-.771.118H3a.75.75 0 01-.75-.75v-.75a.75.75 0 01.75-.75h.53l.194-.458a.75.75 0 01.25-.542h1.5a.75.75 0 110 1.5h-.5a.75.75 0 01-.75-.75v-.75A.75.75 0 012.75 2h1.107a.75.75 0 00-.164-1.484l.84-2.522a.75.75 0 00-.24-1.071L2.347 1.47a.75.75 0 11.24-1.07l1.68-2.5a.75.75 0 111.38.225l2.571.569a.75.75 0 11-.18 1.293l-.55.66a.75.75 0 11-.851-.676l-.161-.483a.75.75 0 01.52-.965h.5a.75.75 0 010 1.5h-.5a.75.75 0 01-.75-.75v-.5A.75.75 0 012.75 13h.5a.75.75 0 010 1.5h-.5a.75.75 0 01-.75-.75V12a.75.75 0 00-.75.75H1v.5a.75.75 0 01-.75.75H1a.75.75 0 110-1.5h.5a.75.75 0 11.75.75v1.5a.75.75 0 11-1.5 0z" stroke="currentColor" />
  </svg>
);

const SpaceIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M12 6a6 6 0 110 12 6 6 0 010-12z" stroke="currentColor" />
  </svg>
);

const DefaultCategoryIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.692 9-11.622 0-1.042-.13-2.052-.382-3.016z" stroke="currentColor" />
  </svg>
);

const CompletedIcon = () => (
  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
  </svg>
);

const ProcessingIcon = () => (
  <svg className="w-3 h-3 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
    <path className="opacity-75" fill="none" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 12a8 8 0 018-8V0" />
  </svg>
);

const FailedIcon = () => (
  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
  </svg>
);

const DemoIcon = () => (
  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h8.688M1.338 12h18.688M12 4.248v13.5" />
  </svg>
);

const DeleteIcon = () => (
  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" stroke="currentColor" />
  </svg>
);

const getCategoryIcon = (category) => {
  switch (category) {
    case "earth":
      return <EarthIcon />;
    case "mars":
      return <MarsIcon />;
    case "space":
      return <SpaceIcon />;
    default:
      return <DefaultCategoryIcon />;
  }
};

const getStatusBadge = (status) => {
  switch (status) {
    case "completed":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-green-500/20 text-green-400 rounded-full">
          <CompletedIcon />
          Completed
        </span>
      );
    case "processing":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-yellow-500/20 text-yellow-400 rounded-full">
          <ProcessingIcon />
          Processing
        </span>
      );
    case "failed":
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-red-500/20 text-red-400 rounded-full">
          <FailedIcon />
          Failed
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-gray-500/20 text-gray-400 rounded-full">
          {status}
        </span>
      );
  }
};

const getCategoryBadge = (category) => {
  const Icon = getCategoryIcon(category);
  return (
    <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-gray-700 text-gray-300 rounded-full">
      <Icon />
      <span className="capitalize">{category}</span>
    </span>
  );
};

const AdminDatasetsTable = ({ datasets, onDeleteDataset, loading, error }) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [filterCategory, setFilterCategory] = useState("all"); // all, earth, mars, space
  const [filterStatus, setFilterStatus] = useState("all"); // all, completed, processing, failed

  const filteredDatasets = useMemo(() => {
    return datasets.filter((dataset) => {
      const matchesSearch = dataset.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                           (dataset.owner_email && dataset.owner_email.toLowerCase().includes(searchTerm.toLowerCase()));
      const matchesCategory = filterCategory === "all" || dataset.category === filterCategory;
      const matchesStatus = filterStatus === "all" || dataset.processing_status === filterStatus;
      return matchesSearch && matchesCategory && matchesStatus;
    });
  }, [datasets, searchTerm, filterCategory, filterStatus]);

  const handleDelete = (datasetId, e) => {
    e.stopPropagation();
    if (!confirm("Are you sure you want to delete this dataset? This cannot be undone.")) {
      return;
    }
    onDeleteDataset(datasetId);
  };

  if (loading) {
    return (
      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <div className="p-4 border-b border-gray-800">
          <h2 className="text-lg font-semibold">Datasets</h2>
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
          <h2 className="text-lg font-semibold">Datasets</h2>
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
            placeholder="Search datasets..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-9 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Categories</option>
            <option value="earth">Earth</option>
            <option value="mars">Mars</option>
            <option value="space">Space</option>
          </select>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">All Status</option>
            <option value="completed">Completed</option>
            <option value="processing">Processing</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-gray-800 bg-gray-800/50">
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider">Dataset</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider hidden md:table-cell">Owner</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider hidden lg:table-cell">Size</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider hidden lg:table-cell">Category</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider hidden lg:table-cell">Status</th>
              <th className="px-6 py-3 text-left text-xs font-semibold text-gray-400 uppercase tracking-wider hidden lg:table-cell">Type</th>
              <th className="px-6 py-3 text-right text-xs font-semibold text-gray-400 uppercase tracking-wider">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-800">
            {filteredDatasets.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-6 py-12 text-center text-gray-400">
                  <p className="text-lg font-medium mb-1">No datasets found</p>
                  <p className="text-xs text-gray-500">Try adjusting your search or filter</p>
                </td>
              </tr>
            ) : (
              filteredDatasets.map((dataset) => (
                <tr key={dataset.id} className="hover:bg-gray-800/50 transition-colors">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-medium text-sm">
                        {dataset.name?.charAt(0)?.toUpperCase() || "D"}
                      </div>
                      <div>
                        <p className="font-medium text-white truncate max-w-xs">{dataset.name}</p>
                        <p className="text-xs text-gray-400 truncate max-w-xs">{dataset.owner_email || "Unknown"}</p>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 hidden md:table-cell">
                    <p className="text-sm text-gray-400 truncate max-w-xs">{dataset.owner_email || "Unknown"}</p>
                  </td>
                  <td className="px-6 py-4 hidden lg:table-cell text-sm text-gray-400">
                    {dataset.size_mp ? `${dataset.size_mp} MP` : `${dataset.width}×${dataset.height}`}
                  </td>
                  <td className="px-6 py-4 hidden lg:table-cell">
                    <div className="flex items-center gap-2">
                      {getCategoryIcon(dataset.category)}
                      <span className="text-xs text-gray-400 capitalize">{dataset.category}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 hidden lg:table-cell">
                    {getStatusBadge(dataset.processing_status)}
                  </td>
                  <td className="px-6 py-4 hidden lg:table-cell">
                    {dataset.is_demo ? (
                      <span className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium bg-blue-500/20 text-blue-400 rounded-full">
                        <DemoIcon />
                        DEMO
                      </span>
                    ) : (
                      <span className="text-gray-400">User Upload</span>
                    )}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        if (!confirm("Are you sure you want to delete this dataset? This cannot be undone.")) {
                          return;
                        }
                        onDeleteDataset(dataset.id);
                      }}
                      className="text-red-400 hover:text-red-300 flex items-center gap-1 text-sm font-medium transition-colors"
                      title="Delete dataset"
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
    </div>
  );
};

export default AdminDatasetsTable;