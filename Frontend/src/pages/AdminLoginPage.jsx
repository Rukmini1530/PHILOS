import { AlertCircle, Lock } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import Button from "../components/ui/Button";
import Input from "../components/ui/Input";
import api from "../services/api";

const AdminLoginPage = () => {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (event) => {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      const response = await api.apiClient.post("/api/auth/login", {
        email,
        password,
      });

      if (response.data.user?.is_superuser !== true) {
        setError("This account does not have administrator access.");
        return;
      }

      localStorage.setItem("astropixel_token", response.data.access_token);
      localStorage.setItem("astropixel_user", JSON.stringify(response.data.user));
      navigate("/admin", { replace: true });
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to sign in.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md rounded-2xl border border-white/10 bg-gray-900 p-8 shadow-2xl">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-xl bg-indigo-500/20 text-indigo-300">
            <Lock className="h-7 w-7" />
          </div>
          <h1 className="text-2xl font-bold text-white">Admin Panel</h1>
          <p className="mt-2 text-gray-400">Sign in with an administrator account</p>
        </div>

        {error && (
          <div className="mb-5 flex gap-2 rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-red-200">
            <AlertCircle className="h-5 w-5 shrink-0" />
            <p>{error}</p>
          </div>
        )}

        <form onSubmit={handleLogin} className="space-y-5">
          <div>
            <label htmlFor="admin-email" className="mb-2 block text-sm text-gray-300">
              Email
            </label>
            <Input
              id="admin-email"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              disabled={loading}
            />
          </div>
          <div>
            <label htmlFor="admin-password" className="mb-2 block text-sm text-gray-300">
              Password
            </label>
            <Input
              id="admin-password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              disabled={loading}
            />
          </div>
          <Button type="submit" disabled={loading} className="w-full">
            {loading ? "Signing in…" : "Sign in"}
          </Button>
        </form>
      </div>
    </div>
  );
};

export default AdminLoginPage;
