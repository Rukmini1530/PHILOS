import React from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import ErrorBoundary from "./components/common/ErrorBoundary";
import ProtectedRoute from "./components/common/ProtectedRoute";
import Layout from "./components/layout/Layout";
import AboutPage from "./pages/AboutPage";
import AdminPanel from "./pages/AdminPanel";
import ContactPage from "./pages/ContactPage";
import DocsPage from "./pages/DocsPage";
import Home from "./pages/Home";
import LandingPage from "./pages/LandingPage";
import LoginPage from "./pages/LoginPage";
import NotFound from "./pages/NotFound";
import SignupPage from "./pages/SignupPage";
import Viewer from "./pages/Viewer";

function App() {
  return (
    <ErrorBoundary>
      <Routes>
        {/* Public pages - outside authenticated shell */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />

        {/* Authenticated application routes */}
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Home />} />
          <Route path="viewer/:datasetId" element={<Viewer />} />
          <Route path="/404" element={<NotFound />} />
          <Route path="*" element={<Navigate to="/404" replace />} />
        </Route>

        {/* Admin route - only visible/accessible to admins */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute requireAdmin={true}>
              <AdminPanel />
            </ProtectedRoute>
          }
        />
      </Routes>
    </ErrorBoundary>
  );
}

export default App;