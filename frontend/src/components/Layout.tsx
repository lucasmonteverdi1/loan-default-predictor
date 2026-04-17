import { NavLink, Outlet } from "react-router-dom";

const navCls = ({ isActive }: { isActive: boolean }) =>
  [
    "px-4 py-2 text-sm font-medium rounded-lg transition-colors",
    isActive
      ? "bg-indigo-600 text-white"
      : "text-gray-600 hover:bg-gray-100",
  ].join(" ");

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top nav */}
      <header className="sticky top-0 z-10 bg-white border-b border-gray-200 shadow-sm">
        <div className="mx-auto max-w-4xl px-4 py-3 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-bold text-gray-900 leading-tight">
              Credit Risk Scorer
            </h1>
            <p className="text-xs text-gray-400">XGBoost · SHAP · Gemini · Groq · LangGraph</p>
          </div>
          <nav className="flex gap-2">
            <NavLink to="/" end className={navCls}>
              Evaluate
            </NavLink>
            <NavLink to="/monitoring" className={navCls}>
              Monitoring
            </NavLink>
          </nav>
        </div>
      </header>

      {/* Page content */}
      <main className="mx-auto max-w-4xl px-4 py-8">
        <Outlet />
      </main>
    </div>
  );
}
