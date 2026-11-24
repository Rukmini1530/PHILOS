import React from "react";
import { Link } from "react-router-dom";
import { Telescope, User, LogOut } from "lucide-react";
import Button from "../ui/Button";

const AppHeader = () => {
  return (
    <header className="bg-gray-900 border-b border-gray-800 sticky top-0 z-10 px-6 py-3 flex items-center justify-between max-w-7xl mx-auto">
      <div className="flex items-center gap-3">
        <Link to="/" className="flex items-center gap-2">
          <Telescope className="w-5 h-5 text-primary" />
          <span className="text-xl font-bold text-primary">PHILOS</span>
        </Link>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 text-gray-300">
          <User className="w-4 h-4" />
          <span className="text-sm">User</span>
          <Button variant="ghost" size="sm" className="gap-2 text-gray-400 hover:text-white">
            <LogOut className="w-4 h-4" />
            Logout
          </Button>
        </div>
      </div>
    </header>
  );
};

export default AppHeader;