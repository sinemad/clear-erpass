import { BrowserRouter, NavLink, Navigate, Route, Routes } from "react-router-dom";
import SettingsPage from "./components/Settings/SettingsPage";
import ServicesPage from "./components/Services/ServicesPage";
import ServiceDetailPage from "./components/Services/ServiceDetailPage";
import AccessTrackerDetailPage from "./components/AccessTracker/AccessTrackerDetailPage";
import LogsPage from "./components/Logs/LogsPage";
import { useTheme } from "./hooks/useTheme";
import styles from "./App.module.css";

export default function App() {
  const [theme, toggleTheme] = useTheme();

  return (
    <BrowserRouter>
      <div className={styles.layout}>
        <nav className={styles.nav}>
          <span className={styles.brand}>ClearPass Visualizer</span>
          <NavLink to="/services" className={({ isActive }) => isActive ? styles.activeLink : styles.link}>
            Services
          </NavLink>
          <NavLink to="/logs" className={({ isActive }) => isActive ? styles.activeLink : styles.link}>
            Logs
          </NavLink>
          <NavLink to="/settings" className={({ isActive }) => isActive ? styles.activeLink : styles.link}>
            Settings
          </NavLink>
          <button className={styles.themeToggle} onClick={toggleTheme} aria-label="Toggle theme">
            {theme === "light" ? "Dark" : "Light"}
          </button>
        </nav>

        <main className={styles.main}>
          <Routes>
            <Route path="/" element={<Navigate to="/services" replace />} />
            <Route path="/services" element={<ServicesPage />} />
            <Route path="/services/:id" element={<ServiceDetailPage />} />
            <Route path="/access-tracker/:id" element={<AccessTrackerDetailPage />} />
            <Route path="/logs" element={<LogsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
