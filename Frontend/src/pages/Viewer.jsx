import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Eye,
  GitCompare,
  Maximize2,
  Settings,
  Tag,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Button from "../components/ui/Button";
import AnnotationTools from "../components/viewer/AnnotationTools";
import AnnotationsList from "../components/viewer/AnnotationsList";
import ComparisonView from "../components/viewer/ComparisonView";
import SettingsModal from "../components/viewer/SettingsModal";
import ViewerCanvas from "../components/viewer/ViewerCanvas";
import ViewerInfo from "../components/viewer/ViewerInfo";
import { useApp } from "../context/AppContext";
import { cn } from "../utils/helpers";

const Viewer = () => {
  const { datasetId } = useParams();
  const navigate = useNavigate();
  const viewerRef = useRef(null);
  const {
    datasets,
    selectedDataset,
    setSelectedDataset,
    viewMode,
    setViewMode,
    sidebarOpen,
    setSidebarOpen,
    loading,
  } = useApp();

  const [viewerReady, setViewerReady] = useState(false);
  const [viewportInfo, setViewportInfo] = useState({
    zoom: "1.0",
    position: { x: 0, y: 0 },
  });
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const [headerCollapsed, setHeaderCollapsed] = useState(false);

  // Comparison view state - shared between sidebar and main canvas
  const [comparisonMode, setComparisonMode] = useState("sideBySide");
  const [secondDataset, setSecondDataset] = useState(null);
  const [opacity, setOpacity] = useState(50);
  const [syncEnabled, setSyncEnabled] = useState(true);

  // Clear selectedDataset immediately when datasetId changes to prevent overlap
  useEffect(() => {
    // If the URL datasetId doesn't match the current selectedDataset, clear it
    if (selectedDataset && String(selectedDataset.id) !== String(datasetId)) {
      console.log("🔄 Dataset ID changed, clearing old dataset");
      setSelectedDataset(null);
      // Also clear second dataset in compare mode to prevent tiles from showing
      setSecondDataset(null);
    }
  }, [datasetId, selectedDataset, setSelectedDataset]);

  useEffect(() => {
    // Wait for datasets to load before checking
    if (loading) return;

    // Find and set the dataset - handle both string and number IDs
    const dataset = datasets.find((d) => {
      // Try both strict match and type-converted match
      return (
        d.id === datasetId ||
        d.id === Number(datasetId) ||
        String(d.id) === datasetId
      );
    });

    if (dataset) {
      setSelectedDataset(dataset);
    } else if (datasets.length > 0) {
      // Only redirect to 404 if datasets are loaded and dataset not found
      console.error(
        `Dataset not found: ${datasetId}. Available IDs:`,
        datasets.map((d) => d.id)
      );
      navigate("/404");
    }
  }, [datasetId, datasets, setSelectedDataset, navigate, loading]);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
    } else {
      document.exitFullscreen();
    }
  };

  useEffect(() => {
    const handleFullscreenChange = () => {
      // setIsFullscreen(!!document.fullscreenElement);
    };
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    return () =>
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
  }, []);

  // Listen for viewport updates from ViewerCanvas
  useEffect(() => {
    const handleViewportUpdate = (event) => {
      const { zoom, center } = event.detail;
      setViewportInfo({
        zoom: zoom,
        position: center,
      });
    };

    window.addEventListener("viewer-viewport-update", handleViewportUpdate);
    return () => {
      window.removeEventListener(
        "viewer-viewport-update",
        handleViewportUpdate
      );
    };
  }, []);

  // Auto-manage sidebar state based on view mode
  useEffect(() => {
    if (viewMode === "explore") {
      // Explore: No sidebars by default
      setSidebarOpen({ left: false, right: false });
    } else if (viewMode === "annotate") {
      // Annotate: Both sidebars open
      setSidebarOpen({ left: true, right: true });
    } else if (viewMode === "compare") {
      // Compare: Left sidebar for controls, right closed
      setSidebarOpen({ left: true, right: false });
    }
  }, [viewMode, setSidebarOpen]);

  // Initialize comparison datasets when entering compare mode
  useEffect(() => {
    if (viewMode === "compare" && secondDataset === null && selectedDataset) {
      const availableDatasets = datasets.filter(
        (d) => d.id !== selectedDataset.id
      );
      if (availableDatasets.length > 0) {
        console.log(
          "🎯 Initializing secondDataset with:",
          availableDatasets[0].name
        );
        setSecondDataset(availableDatasets[0]);
      }
    }
  }, [viewMode, selectedDataset, datasets, secondDataset]);

  // CRITICAL: Check if selectedDataset matches URL datasetId
  // This prevents rendering ViewerCanvas with wrong dataset (causes image overlap)
  const isCorrectDataset =
    selectedDataset &&
    (String(selectedDataset.id) === String(datasetId) ||
      selectedDataset.id === Number(datasetId));

  if (!selectedDataset || !isCorrectDataset) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-950">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading dataset...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col bg-gray-950 text-white">
      {/* Header */}
      <header
        className={cn(
          "bg-gray-900/95 backdrop-blur-sm border-b border-gray-800 px-4 py-2.5 flex-shrink-0 transition-all duration-200",
          headerCollapsed && "py-1.5 px-3"
        )}
      >
        <div className="flex items-center justify-between max-w-full mx-auto gap-3">
          {/* Left: Back, Dataset Name, Dimensions */}
          <div className="flex items-center gap-3 flex-1 min-w-0">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate("/dashboard")}
              className="gap-2 flex-shrink-0 text-gray-300 hover:text-white hover:bg-gray-800/50"
              title="Back to datasets"
            >
              <ArrowLeft className="w-4 h-4" />
              <span className="hidden sm:inline">Back</span>
            </Button>

            <div className="h-6 w-px bg-gray-700 flex-shrink-0" />

            <div className="min-w-0 flex-shrink">
              <h1 className="text-sm font-semibold truncate">{selectedDataset.name}</h1>
              <p className="text-[11px] text-gray-500 truncate">
                {selectedDataset.width?.toLocaleString()} ×{" "}
                {selectedDataset.height?.toLocaleString()} px
              </p>
            </div>
          </div>

          {/* Center: View Mode Tabs */}
          <div className="flex items-center gap-1 bg-gray-800/50 rounded-lg p-1 border border-gray-700/50 flex-shrink-0">
            <button
              onClick={() => setViewMode("explore")}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all text-xs font-medium",
                viewMode === "explore"
                  ? "bg-blue-600/20 text-blue-300 border border-blue-500/30"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-700/50"
              )}
              title="Explore mode"
            >
              <Eye className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Explore</span>
            </button>
            <button
              onClick={() => setViewMode("annotate")}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all text-xs font-medium",
                viewMode === "annotate"
                  ? "bg-blue-600/20 text-blue-300 border border-blue-500/30"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-700/50"
              )}
              title="Annotate mode"
            >
              <Tag className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Annotate</span>
            </button>
            <button
              onClick={() => setViewMode("compare")}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-md transition-all text-xs font-medium",
                viewMode === "compare"
                  ? "bg-purple-600/20 text-purple-300 border border-purple-500/30"
                  : "text-gray-400 hover:text-gray-200 hover:bg-gray-700/50"
              )}
              title="Compare mode"
            >
              <GitCompare className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Compare</span>
            </button>
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-1.5 flex-shrink-0">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setHeaderCollapsed(!headerCollapsed)}
              className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-800/50"
              title={headerCollapsed ? "Expand header" : "Collapse header"}
            >
              {headerCollapsed ? (
                <ChevronRight className="w-4 h-4" />
              ) : (
                <ChevronLeft className="w-4 h-4" />
              )}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleFullscreen}
              className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-800/50"
              title="Fullscreen"
            >
              <Maximize2 className="w-4 h-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowSettingsModal(true)}
              className="p-1.5 text-gray-400 hover:text-white hover:bg-gray-800/50"
              title="Viewer settings"
            >
              <Settings className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Left Sidebar */}
        <aside
          className={cn(
            "bg-gray-900/95 backdrop-blur-sm border-r border-gray-800 flex flex-col transition-all duration-300 ease-out",
            sidebarOpen.left ? "w-72" : "w-12",
            "overflow-hidden"
          )}
        >
          {sidebarOpen.left ? (
            <div className="flex flex-col h-full">
              {/* Sidebar Header */}
              <div className="p-3 border-b border-gray-800 flex items-center justify-between flex-shrink-0">
                <h2 className="font-semibold flex items-center gap-2 text-sm">
                  {viewMode === "annotate" && <Tag className="w-4 h-4 text-blue-400" />}
                  {viewMode === "compare" && <GitCompare className="w-4 h-4 text-purple-400" />}
                  {viewMode === "explore" && <Eye className="w-4 h-4 text-cyan-400" />}
                  <span className="truncate">
                    {viewMode === "annotate" && "Annotation Tools"}
                    {viewMode === "compare" && "Comparison"}
                    {viewMode === "explore" && "Dataset Info"}
                  </span>
                </h2>
                <button
                  onClick={() =>
                    setSidebarOpen((prev) => ({ ...prev, left: false }))
                  }
                  className="p-1.5 hover:bg-gray-800 rounded transition-colors text-gray-400 hover:text-white"
                  title="Collapse sidebar"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto custom-scrollbar">
                {viewMode === "annotate" && <AnnotationTools />}
                {viewMode === "explore" && (
                  <ViewerInfo dataset={selectedDataset} />
                )}
                {viewMode === "compare" && (
                  <ComparisonView
                    dataset={selectedDataset}
                    renderControlsOnly={true}
                    comparisonMode={comparisonMode}
                    setComparisonMode={setComparisonMode}
                    secondDataset={secondDataset}
                    setSecondDataset={setSecondDataset}
                    opacity={opacity}
                    setOpacity={setOpacity}
                    syncEnabled={syncEnabled}
                    setSyncEnabled={setSyncEnabled}
                  />
                )}
              </div>
            </div>
          ) : (
            <div className="flex flex-col h-full">
              <button
                onClick={() => setSidebarOpen((prev) => ({ ...prev, left: true }))}
                className="w-full flex items-center justify-center h-full p-2 hover:bg-gray-800 transition-colors"
                title="Expand sidebar"
              >
                <ChevronRight className="w-5 h-5 text-gray-500" />
              </button>
            </div>
          )}
        </aside>

        {/* Viewer Canvas */}
        <main className="flex-1 relative bg-gray-950 min-w-0">
          {viewMode === "compare" ? (
            <ComparisonView
              key={`compare-${selectedDataset.id}`}
              dataset={selectedDataset}
              renderControlsOnly={false}
              comparisonMode={comparisonMode}
              setComparisonMode={setComparisonMode}
              secondDataset={secondDataset}
              setSecondDataset={setSecondDataset}
              opacity={opacity}
              setOpacity={setOpacity}
              syncEnabled={syncEnabled}
              setSyncEnabled={setSyncEnabled}
            />
          ) : (
            <ViewerCanvas
              key={`viewer-${selectedDataset.id}`}
              dataset={selectedDataset}
              mode={viewMode}
              onReady={() => setViewerReady(true)}
              viewerRef={viewerRef}
            />
          )}
        </main>

        {/* Right Sidebar - Only in Annotate mode */}
        {viewMode === "annotate" && (
          <aside
            className={cn(
              "bg-gray-900/95 backdrop-blur-sm border-l border-gray-800 flex flex-col transition-all duration-300 ease-out",
              sidebarOpen.right ? "w-72" : "w-12",
              "overflow-hidden"
            )}
          >
            {sidebarOpen.right ? (
              <div className="flex flex-col h-full">
                <div className="p-3 border-b border-gray-800 flex items-center justify-between flex-shrink-0">
                  <h2 className="font-semibold flex items-center gap-2 text-sm">
                    <Tag className="w-4 h-4 text-blue-400" />
                    Annotations
                  </h2>
                  <button
                    onClick={() =>
                      setSidebarOpen((prev) => ({ ...prev, right: false }))
                    }
                    className="p-1.5 hover:bg-gray-800 rounded transition-colors text-gray-400 hover:text-white"
                    title="Collapse sidebar"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>

                <div className="flex-1 overflow-y-auto custom-scrollbar">
                  <AnnotationsList />
                </div>
              </div>
            ) : (
              <div className="flex flex-col h-full">
                <button
                  onClick={() =>
                    setSidebarOpen((prev) => ({ ...prev, right: true }))
                  }
                  className="w-full flex items-center justify-center h-full p-2 hover:bg-gray-800 transition-colors"
                  title="Expand sidebar"
                >
                  <ChevronLeft className="w-5 h-5 text-gray-500" />
                </button>
              </div>
            )}
          </aside>
        )}

        {/* Resize handles for sidebars */}
        {sidebarOpen.left && (
          <div
            className="absolute top-0 left-72 w-1 h-full cursor-col-resize bg-gray-700/50 hover:bg-blue-500/50 transition-colors z-10"
            onMouseDown={(e) => {
              e.preventDefault();
              const startX = e.clientX;
              const startWidth = 288; // 72 * 4 (rem to px)

              const handleMouseMove = (moveEvent) => {
                const newWidth = Math.max(240, Math.min(480, startWidth + (moveEvent.clientX - startX)));
                document.documentElement.style.setProperty('--left-sidebar-width', `${newWidth}px`);
              };

              const handleMouseUp = () => {
                document.removeEventListener('mousemove', handleMouseMove);
                document.removeEventListener('mouseup', handleMouseUp);
              };

              document.addEventListener('mousemove', handleMouseMove);
              document.addEventListener('mouseup', handleMouseUp);
            }}
            title="Drag to resize sidebar"
          />
        )}
        {sidebarOpen.right && (
          <div
            className="absolute top-0 right-72 w-1 h-full cursor-col-resize bg-gray-700/50 hover:bg-purple-500/50 transition-colors z-10"
            onMouseDown={(e) => {
              e.preventDefault();
              const startX = e.clientX;
              const startWidth = 288;

              const handleMouseMove = (moveEvent) => {
                const newWidth = Math.max(240, Math.min(480, startWidth - (moveEvent.clientX - startX)));
                document.documentElement.style.setProperty('--right-sidebar-width', `${newWidth}px`);
              };

              const handleMouseUp = () => {
                document.removeEventListener('mousemove', handleMouseMove);
                document.removeEventListener('mouseup', handleMouseUp);
              };

              document.addEventListener('mousemove', handleMouseMove);
              document.addEventListener('mouseup', handleMouseUp);
            }}
            title="Drag to resize sidebar"
          />
        )}

        {/* Status Bar */}
        <footer className="bg-gray-900/95 backdrop-blur-sm border-t border-gray-800 px-4 py-2 flex items-center justify-between text-[11px] text-gray-500 flex-shrink-0">
          <div className="flex items-center gap-3">
            <span className="text-green-400 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
              Ready
            </span>
            <span className="w-px h-3 bg-gray-700" />
            <span>Zoom: {viewerReady ? `${viewportInfo.zoom}x` : "—"}</span>
            <span className="w-px h-3 bg-gray-700" />
            <span>
              Pos:{" "}
              {viewerReady
                ? `${viewportInfo.position.x.toFixed(3)}, ${viewportInfo.position.y.toFixed(3)}`
                : "—"}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs font-medium text-gray-400">{selectedDataset.category?.toUpperCase()}</span>
            <span className="w-px h-3 bg-gray-700" />
            <span className="font-mono">
              {selectedDataset.width?.toLocaleString()} ×{" "}
              {selectedDataset.height?.toLocaleString()} px
            </span>
          </div>
        </footer>

        {/* Modals */}
        <SettingsModal
          isOpen={showSettingsModal}
          onClose={() => setShowSettingsModal(false)}
        />
      </div>
    </div>
  );
};

export default Viewer;