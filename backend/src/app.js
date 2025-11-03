import express from "express";
import cors from "cors";
import cookieParser from "cookie-parser";
import userRouter from "./routes/user.route.js";
import scheduleRouter from "./routes/schedule.route.js";
import prescriptionRouter from "./routes/prescription.route.js";
import predictRouter from "./routes/predict.route.js";
import debugRouter from "./routes/debug.route.js";

const app = express();

//setup inbuilt middlewares and imported ones
// Configure CORS. Allow a comma-separated list of origins via CORS_ORIGIN.
// If CORS_ORIGIN is not set in production we reflect the request origin so
// the browser gets an explicit Access-Control-Allow-Origin header (needed
// when `withCredentials: true` is used from the frontend).
const allowedOrigins = process.env.CORS_ORIGIN
  ? process.env.CORS_ORIGIN.split(",").map((o) => o.trim()).filter(Boolean)
  : [];

app.use(
  cors({
    origin: (origin, callback) => {
      // allow requests with no origin (like mobile apps or curl)
      if (!origin) return callback(null, true);

      // if allowedOrigins is empty, reflect the request origin (allow all)
      if (allowedOrigins.length === 0) return callback(null, true);

      if (allowedOrigins.indexOf(origin) !== -1) {
        return callback(null, true);
      }

      // Not allowed by CORS
      return callback(new Error("Origin not allowed by CORS"));
    },
    credentials: true,
  })
);
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
app.use("/api/debug", debugRouter);

app.get("/", (req, res) => {
  res.send("HOMEPAGE");
});

export { app };
