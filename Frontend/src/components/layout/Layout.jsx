import React from "react";
import { Outlet, Routes, Route } from "react-router-dom";
import { cn } from "../../utils/helpers";
import AppHeader from "../layout/AppHeader";
import AppSidebar from "../layout/AppSidebar";
import AppFooter from "../layout/AppFooter";
import { SpaceBackground } from "../../components/space";

const APP_PUBLIC_PATHS = ["/", "/login", "/signup"];

// Simple path check
function isPublicPath() {
  const path = window.location.pathname;
  for (let i = 0; i < APP_PUBLIC_PATHS.length; i++) {
    if (window.location.pathname === APP_PUBLIC_PATHS[i]) {
      return true;
    }
  }
  return false;
}

// Simplified public routes - just return null, routing handled by App.jsx
function PublicRoutes() {
  return null;
}

// Protected routes - simplified structure
function ProtectedRoutes() {
  return /*#__PURE__*/ (
    <div className="min-h-screen bg-gray-900 text-white flex flex-col h-screen">
      {/* Space Background for authenticated routes */}
      <SpaceBackground
        intensity="subtle"
        showStars={true}
        showGradients={true}
        backgroundImage="/space-bg.jpg"
      />
      <AppHeader />
      <main className="flex-1 flex min-h-0 bg-gray-900 overflow-hidden">
        <Outlet />
      </main>
    </div>
  );
}

const Layout = () => {
  // For public paths, render null (routing handled by App.jsx)
  if (isPublicPath()) {
    return <PublicRoutes />;
  }

  return <ProtectedRoutes />;
};

export default Layout;