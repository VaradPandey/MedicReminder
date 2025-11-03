import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useSelector } from "react-redux";
import { Container, LogoutBtn } from "./index";

export default function Header() {
  const navigate = useNavigate();
  const authStatus = useSelector((state) => state.auth.status);
  const [isDark, setIsDark] = useState(false);

  // Initialize theme from localStorage or system preference
  useEffect(() => {
    const stored = localStorage.getItem("theme");
    const prefersDark =
      window.matchMedia &&
      window.matchMedia("(prefers-color-scheme: dark)").matches;
    const shouldBeDark = stored ? stored === "dark" : prefersDark;
    setIsDark(shouldBeDark);
    document.documentElement.classList.toggle("dark", shouldBeDark);
  }, []);

  const toggleTheme = () => {
    const next = !isDark;
    setIsDark(next);
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("theme", next ? "dark" : "light");
  };

  const navItems = [
    { name: "Home", path: "/" },
    // { name: "Prediction", path: "/prediction" },
    { name: "Login", path: "/login", auth: false },
    { name: "Register", path: "/register", auth: false },
    { name: "Upload", path: "/upload", auth: true },
    { name: "Prescriptions", path: "/prescriptions", auth: true },
    { name: "Create Schedule", path: "/schedule", auth: true },
  ];

  return (
    <header className="py-4 shadow bg-white text-gray-900 dark:bg-gray-800 dark:text-white">
      <Container>
        {/* Top Section: Project Name + Logout Button */}
        <div className="flex items-center justify-between">
          <h1
            className="text-2xl font-bold cursor-pointer mx-auto"
            onClick={() => navigate("/")}
          >
            CareSentry
          </h1>

          {/* Top-right: Theme toggle and (if authed) Logout */}
          {/* <div className="absolute right-6 top-4 flex items-center gap-3">
            <button
              onClick={toggleTheme}
              aria-label="Toggle dark mode"
              className="w-9 h-9 rounded-full border border-gray-300 dark:border-gray-600 flex items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              title={isDark ? 'Switch to light' : 'Switch to dark'}
            >
              {isDark ? (
                // Sun icon
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M6.76 4.84l-1.8-1.79-1.42 1.41 1.79 1.8 1.43-1.42zM1 13h3v-2H1v2zm10-9h2V1h-2v3zm7.66 2.46l1.79-1.8-1.41-1.41-1.8 1.79 1.42 1.42zM17 13h3v-2h-3v2zM12 6a6 6 0 100 12 6 6 0 000-12zm0 16h2v-3h-2v3zM4.22 18.36l1.42 1.42 1.8-1.79-1.42-1.42-1.8 1.79zM19.78 18.36l-1.8-1.79-1.42 1.42 1.79 1.79 1.43-1.42z" />
                </svg>
              ) : (
                // Moon icon
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2a9.99 9.99 0 00-9.95 9.06A9 9 0 1012 2zm0 18a8 8 0 01-7.75-6.01A9.99 9.99 0 0012 4c.34 0 .67.02 1 .05A8 8 0 0112 20z" />
                </svg>
              )}
            </button>
            {authStatus && <LogoutBtn />}
          </div> */}
        </div>

        {/* Navigation Bar */}
        <nav className="mt-3">
          <ul className="flex justify-center space-x-8">
            {navItems
              .filter((item) =>
                authStatus ? item.auth !== false : item.auth !== true
              )
              .map((item) => (
                <li key={item.name}>
                  <button
                    onClick={() => navigate(item.path)}
                    className="hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
                  >
                    {item.name}
                  </button>
                </li>
              ))}
          </ul>
        </nav>
      </Container>
    </header>
  );
}
