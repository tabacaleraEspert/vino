import { useState } from "react";
import { useNavigate } from "react-router";
import { GoogleLogin, type CredentialResponse } from "@react-oauth/google";
import { useAuth } from "../context/AuthContext";
import { Eye, EyeOff, AlertCircle, ArrowLeft } from "lucide-react";

type Mode = "login" | "register";

export function Login() {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [nombre, setNombre] = useState("");
  const [apellido, setApellido] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { login, loginWithGoogle, register } = useAuth();

  const switchMode = (m: Mode) => {
    setMode(m);
    setError("");
    setPassword("");
    setConfirmPassword("");
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email.trim() || !password) return;
    setError("");
    setIsLoading(true);
    const ok = await login(email.trim(), password);
    setIsLoading(false);
    if (ok) {
      navigate("/");
    } else {
      setError("Email o contraseña incorrectos");
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!nombre.trim() || !email.trim() || !password) return;
    if (password.length < 6) {
      setError("La contraseña debe tener al menos 6 caracteres");
      return;
    }
    if (password !== confirmPassword) {
      setError("Las contraseñas no coinciden");
      return;
    }
    setError("");
    setIsLoading(true);
    const result = await register(
      nombre.trim(),
      password,
      apellido.trim() || undefined,
      email.trim(),
    );
    setIsLoading(false);
    if (result.ok) {
      navigate("/");
    } else {
      setError(result.error || "Error al crear la cuenta");
    }
  };

  const handleGoogleSuccess = async (response: CredentialResponse) => {
    if (!response.credential) return;
    setError("");
    setIsLoading(true);
    const result = await loginWithGoogle(response.credential);
    setIsLoading(false);
    if (result.ok) {
      navigate(result.isNewUser ? "/onboarding" : "/");
    } else {
      setError(result.error || "Error al iniciar con Google");
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="py-6 px-6">
        <div className="max-w-md mx-auto flex items-center gap-3">
          <div className="w-9 h-9 bg-blue-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-lg">V</span>
          </div>
          <span className="text-xl font-bold text-gray-900">Vino</span>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 flex items-start justify-center px-6 pt-4 pb-12">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8">
            {/* Title */}
            <h1 className="text-2xl font-bold text-gray-900 mb-1">
              {mode === "login" ? "Iniciar sesion" : "Crear tu cuenta"}
            </h1>
            <p className="text-sm text-gray-500 mb-6">
              {mode === "login"
                ? "Ingresa a tu cuenta de Vino"
                : "Empeza a controlar tus finanzas"}
            </p>

            {/* Error */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-start gap-2 mb-6">
                <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            {/* Google */}
            <div className="flex justify-center mb-5">
              <GoogleLogin
                onSuccess={handleGoogleSuccess}
                onError={() => setError("Error al conectar con Google")}
                size="large"
                width="380"
                text={mode === "login" ? "signin_with" : "signup_with"}
                shape="rectangular"
              />
            </div>

            {/* Divider */}
            <div className="relative mb-5">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-200" />
              </div>
              <div className="relative flex justify-center text-xs">
                <span className="px-3 bg-white text-gray-400 uppercase tracking-wider">
                  o
                </span>
              </div>
            </div>

            {/* LOGIN FORM */}
            {mode === "login" && (
              <form onSubmit={handleLogin} className="space-y-4">
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1.5">
                    Email o usuario
                  </label>
                  <input
                    id="email"
                    type="text"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="username"
                    className="w-full px-3.5 py-2.5 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                    placeholder="tu@email.com"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                      Contraseña
                    </label>
                  </div>
                  <div className="relative">
                    <input
                      id="password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      autoComplete="current-password"
                      className="w-full px-3.5 py-2.5 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all pr-10"
                      placeholder="Tu contraseña"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-blue-600 text-white py-2.5 rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? (
                    <span className="flex items-center justify-center gap-2">
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Ingresando...
                    </span>
                  ) : (
                    "Iniciar sesion"
                  )}
                </button>
              </form>
            )}

            {/* REGISTER FORM */}
            {mode === "register" && (
              <form onSubmit={handleRegister} className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label htmlFor="nombre" className="block text-sm font-medium text-gray-700 mb-1.5">
                      Nombre
                    </label>
                    <input
                      id="nombre"
                      type="text"
                      value={nombre}
                      onChange={(e) => setNombre(e.target.value)}
                      required
                      autoComplete="given-name"
                      className="w-full px-3.5 py-2.5 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                      placeholder="Juan"
                    />
                  </div>
                  <div>
                    <label htmlFor="apellido" className="block text-sm font-medium text-gray-700 mb-1.5">
                      Apellido
                    </label>
                    <input
                      id="apellido"
                      type="text"
                      value={apellido}
                      onChange={(e) => setApellido(e.target.value)}
                      autoComplete="family-name"
                      className="w-full px-3.5 py-2.5 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                      placeholder="Perez"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="reg-email" className="block text-sm font-medium text-gray-700 mb-1.5">
                    Email
                  </label>
                  <input
                    id="reg-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                    className="w-full px-3.5 py-2.5 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                    placeholder="tu@email.com"
                  />
                </div>

                <div>
                  <label htmlFor="reg-password" className="block text-sm font-medium text-gray-700 mb-1.5">
                    Contraseña
                  </label>
                  <div className="relative">
                    <input
                      id="reg-password"
                      type={showPassword ? "text" : "password"}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      minLength={6}
                      autoComplete="new-password"
                      className="w-full px-3.5 py-2.5 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all pr-10"
                      placeholder="Minimo 6 caracteres"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                    >
                      {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label htmlFor="confirm-password" className="block text-sm font-medium text-gray-700 mb-1.5">
                    Confirmar contraseña
                  </label>
                  <input
                    id="confirm-password"
                    type={showPassword ? "text" : "password"}
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    autoComplete="new-password"
                    className="w-full px-3.5 py-2.5 border border-gray-300 rounded-lg text-sm outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all"
                    placeholder="Repeti tu contraseña"
                  />
                </div>

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full bg-blue-600 text-white py-2.5 rounded-lg text-sm font-semibold hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isLoading ? (
                    <span className="flex items-center justify-center gap-2">
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Creando cuenta...
                    </span>
                  ) : (
                    "Crear cuenta"
                  )}
                </button>

                <p className="text-xs text-gray-400 text-center">
                  Al crear tu cuenta aceptas los terminos de uso y la politica de privacidad.
                </p>
              </form>
            )}

            {/* Toggle login/register */}
            <div className="mt-6 pt-5 border-t border-gray-200 text-center text-sm">
              {mode === "login" ? (
                <p className="text-gray-600">
                  ¿No tenes cuenta?{" "}
                  <button
                    onClick={() => switchMode("register")}
                    className="text-blue-600 font-semibold hover:text-blue-700"
                  >
                    Registrate
                  </button>
                </p>
              ) : (
                <p className="text-gray-600">
                  ¿Ya tenes cuenta?{" "}
                  <button
                    onClick={() => switchMode("login")}
                    className="text-blue-600 font-semibold hover:text-blue-700"
                  >
                    Inicia sesion
                  </button>
                </p>
              )}
            </div>
          </div>

          {/* Footer */}
          <p className="text-center text-xs text-gray-400 mt-6">
            &copy; 2026 Vino. Todos los derechos reservados.
          </p>
        </div>
      </main>
    </div>
  );
}
