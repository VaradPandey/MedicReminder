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
const port = 3000;

connectDb()
  .then(
    app.listen(port, () => {
      console.log(`Listening at port ${port}`);
      telegramSetup();
    })
  )
  .catch((err) => {
    console.log(err);
  });
