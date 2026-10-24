import { app } from "./app.js";
import { connectDb } from "./db/mongodb.js";
import dotenv from "dotenv";
import { telegramSetup } from "./services/telegram.service.js";

dotenv.config({
  path: "./.env",
});
// Log environment info helpful for diagnosing CORS issues in deployed environments
console.log("NODE_ENV:", process.env.NODE_ENV);
console.log("CORS_ORIGIN:", process.env.CORS_ORIGIN);
// Use the host-provided PORT when available (required on many PaaS providers)
const port = process.env.PORT || 3000;

let server;

const startServer = async (listenPort = port) => {
  try {
    await connectDb();
    server = app.listen(listenPort, () => {
      console.log(`Listening at port ${listenPort}`);
      telegramSetup();
    });
    return server;
  } catch (err) {
    console.error("Failed to connect to database:", err);
    process.exit(1);
  }
};

if (process.env.NODE_ENV !== "test") {
  startServer();
}

export { startServer, server };
