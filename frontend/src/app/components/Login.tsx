import { useState, lazy, Suspense } from "react";
import { useNavigate } from "react-router";
import { Capacitor } from "@capacitor/core";
import { useAuth } from "../context/AuthContext";
import { Eye, EyeOff, AlertCircle, ArrowLeft } from "lucide-react";

const isNative = Capacitor.isNativePlatform();

// Only import Google web SDK on non-native platforms
const WebGoogleLogin = isNative
  ? null
  : lazy(() =>
      import("@react-oauth/google").then((mod) => ({
        default: mod.GoogleLogin,
      }))
    );

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
  const { login, loginWithGoogle, loginWithApple, register } = useAuth();

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
      navigate("/onboarding");
    } else {
      setError(result.error || "Error al crear la cuenta");
    }
  };

  const handleGoogleSuccess = async (response: { credential?: string }) => {
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

  const handleNativeGoogleSignIn = async () => {
    setError("");
    setIsLoading(true);
    try {
      const { GoogleSignIn } = await import("@capawesome/capacitor-google-sign-in");
      const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || "";
      await GoogleSignIn.initialize({ clientId });
      const signInResult = await GoogleSignIn.signIn();
      const result = await loginWithGoogle(signInResult.idToken);
      if (result.ok) {
        navigate(result.isNewUser ? "/onboarding" : "/");
      } else {
        setError(result.error || "Error al iniciar con Google");
      }
    } catch (err: any) {
      if (err?.code !== "SIGN_IN_CANCELED") {
        setError("Error al conectar con Google");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleAppleSignIn = async () => {
    setError("");
    setIsLoading(true);
    try {
      const { AppleSignIn } = await import("@capawesome/capacitor-apple-sign-in");
      const signInResult = await AppleSignIn.signIn();
      const result = await loginWithApple(
        signInResult.idToken,
        signInResult.givenName || undefined,
        signInResult.familyName || undefined,
      );
      if (result.ok) {
        navigate(result.isNewUser ? "/onboarding" : "/");
      } else {
        setError(result.error || "Error al iniciar con Apple");
      }
    } catch (err: any) {
      if (err?.code !== "SIGN_IN_CANCELED") {
        setError("Error al conectar con Apple");
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="py-6 px-6" style={{ paddingTop: 'calc(env(safe-area-inset-top, 0px) + 24px)' }}>
        <div className="max-w-md mx-auto flex items-center gap-3">
          <div className="w-9 h-9 bg-blue-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-lg">V</span>
          </div>
          <span className="text-xl font-bold text-gray-900">Fina</span>
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
                ? "Ingresa a tu cuenta de Fina"
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
              {isNative ? (
                <button
                  type="button"
                  onClick={handleNativeGoogleSignIn}
                  disabled={isLoading}
                  className="w-full flex items-center justify-center gap-3 px-4 py-2.5 border border-gray-300 rounded-lg bg-white hover:bg-gray-50 transition-colors disabled:opacity-50"
                >
                  <svg className="w-5 h-5" viewBox="0 0 24 24">
                    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
                    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                  </svg>
                  <span className="text-sm font-medium text-gray-700">
                    {mode === "login" ? "Iniciar sesion con Google" : "Registrarse con Google"}
                  </span>
                </button>
              ) : WebGoogleLogin ? (
                <Suspense fallback={<div className="h-10" />}>
                  <WebGoogleLogin
                    onSuccess={handleGoogleSuccess}
                    onError={() => setError("Error al conectar con Google")}
                    size="large"
                    width="380"
                    text={mode === "login" ? "signin_with" : "signup_with"}
                    shape="rectangular"
                  />
                </Suspense>
              ) : null}
            </div>

            {/* Apple (only on native iOS) */}
            {isNative && (
              <div className="flex justify-center mb-5">
                <button
                  type="button"
                  onClick={handleAppleSignIn}
                  disabled={isLoading}
                  className="w-full flex items-center justify-center gap-3 px-4 py-2.5 rounded-lg bg-black hover:bg-gray-900 transition-colors disabled:opacity-50"
                >
                  <svg className="w-5 h-5" viewBox="0 0 24 24" fill="white">
                    <path d="M17.05 20.28c-.98.95-2.05.88-3.08.4-1.09-.5-2.08-.48-3.24 0-1.44.62-2.2.44-3.06-.4C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.8 1.18-.24 2.31-.93 3.57-.84 1.51.12 2.65.72 3.4 1.8-3.12 1.87-2.38 5.98.48 7.13-.57 1.5-1.31 2.99-2.54 4.09zM12.03 7.25c-.15-2.23 1.66-4.07 3.74-4.25.29 2.58-2.34 4.5-3.74 4.25z"/>
                  </svg>
                  <span className="text-sm font-medium text-white">
                    {mode === "login" ? "Iniciar sesion con Apple" : "Registrarse con Apple"}
                  </span>
                </button>
              </div>
            )}

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
            &copy; 2026 Fina. Todos los derechos reservados.
          </p>
        </div>
      </main>
    </div>
  );
}
