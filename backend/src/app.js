import express from "express";
import cors from "cors";
import cookieParser from "cookie-parser";
import userRouter from "./routes/user.route.js";
import scheduleRouter from "./routes/schedule.route.js";
import prescriptionRouter from "./routes/prescription.route.js";
import predictRouter from "./routes/predict.route.js";
import debugRouter from "./routes/debug.route.js";

const app = express();

const defaultOrigins = [
  "https://medic-reminder-two.vercel.app",
  "http://localhost:5173",
  "http://127.0.0.1:5173",
  "http://localhost:3000",
  "http://127.0.0.1:3000",
];

const configuredOrigins = process.env.CORS_ORIGIN
  ? process.env.CORS_ORIGIN.split(",").map((o) => o.trim()).filter(Boolean)
  : [];

const allowedOrigins = Array.from(new Set([...defaultOrigins, ...configuredOrigins]));

app.use(
  cors({
    origin: (origin, callback) => {
      // Allow requests with no origin (curl, health checkers, server-to-server)
      if (!origin) return callback(null, true);
      if (
        allowedOrigins.includes(origin) ||
        (origin.endsWith(".vercel.app") && origin.includes("medic-reminder"))
      ) {
        return callback(null, true);
      }
      return callback(new Error(`Origin ${origin} not allowed by CORS`));
    },
    credentials: true,
  })
);

// Lightweight health check endpoints
app.get(["/health", "/api/health"], (req, res) => {
  res.status(200).json({ status: "ok", service: "MedicReminder Backend" });
});

app.use(
  express.json({
    limit: "16kb",
  })
);
app.use(
  express.urlencoded({
    limit: "16kb",
    extended: true,
  })
);
app.use(express.static("public"));
app.use(cookieParser());

// mount routes
app.use("/api/users", userRouter);
app.use("/api", scheduleRouter);
app.use("/api", prescriptionRouter);
app.use("/api", predictRouter);

if (process.env.NODE_ENV !== "production") {
  app.use("/api/debug", debugRouter);
}

app.get("/", (req, res) => {
  res.send("HOMEPAGE");
});

export { app };