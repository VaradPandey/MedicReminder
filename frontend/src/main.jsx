import React from "react";
import { createRoot } from "react-dom/client";
import {
  createBrowserRouter,
  RouterProvider,
  Navigate,
} from "react-router-dom";
import "./index.css";
import App from "./App.jsx";
import LoginPage from "./pages/Login.jsx";
import RegisterPage from "./pages/Register.jsx";
import Prescription from "./pages/Prescription.jsx";
import PrescriptionsPage from "./pages/Prescriptions.jsx";
import SchedulePage from "./pages/Schedule.jsx";
import SetReminderPage from "./pages/SetReminderPage.jsx";
import PredictionPage from "./pages/Prediction.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import RedirectIfAuth from "./components/RedirectAuth.jsx";
import { AuthProvider } from "./context/AuthContext.jsx";
import Landing from "./pages/Landing.jsx";

const router = createBrowserRouter([
  {
    path: "/",
    element: (
      <AuthProvider>
        <App />
      </AuthProvider>
    ),
    children: [
      {
        index: true,
        element: <Landing />,
      },
      {
        path: "login",
        element: (
          <RedirectIfAuth>
            <LoginPage />
          </RedirectIfAuth>
        ),
      },
      {
        path: "register",
        element: (
          <RedirectIfAuth>
            <RegisterPage />
          </RedirectIfAuth>
        ),
      },
      {
        path: "upload",
        element: (
          <ProtectedRoute>
            <Prescription />
          </ProtectedRoute>
        ),
      },
      {
        path: "landing",
        element: <Landing />,
      },
      {
        path: "prediction",
        element: <PredictionPage />,
      },
      {
        path: "schedule",
        element: (
          <ProtectedRoute>
            <SchedulePage />
          </ProtectedRoute>
        ),
      },
      {
        path: "set-reminder",
        element: (
          <ProtectedRoute>
            <SetReminderPage />
          </ProtectedRoute>
        ),
      },
      {
        path: "prescriptions",
        element: (
          <ProtectedRoute>
            <PrescriptionsPage />
          </ProtectedRoute>
        ),
      },
      { path: "*", element: <Navigate to="/upload" replace /> },
    ],
  },
]);

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
