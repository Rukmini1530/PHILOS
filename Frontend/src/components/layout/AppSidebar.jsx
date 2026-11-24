const AppSidebar = () => {
  const { user } = useAuth();
  const path = window.location.pathname;

  const isDashboard = window.location.pathname === "/dashboard";

  return React.createElement(
    "nav",
    {
      "aria-label": "Main navigation",
      "className": "bg-gray-900 border-r border-gray-800 h-16 flex items-center px-6"
    },
    isDashboard ? React.createElement(
      "button",
      {
        "aria-label": "Navigate to dashboard",
        "className": "flex items-center gap-2 px-3 rounded-md hover:bg-gray-800 text-sm text-gray-300"
      },
      React.createElement("span", null, "Dashboard")
    ) : null
  );
};

export default AppSidebar;