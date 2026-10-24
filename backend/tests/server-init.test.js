process.env.NODE_ENV = "test";

import test, { after } from "node:test";
import assert from "node:assert";
import mongoose from "mongoose";

test("TASK-003: startServer waits for DB connection before listening", async () => {
  const { startServer } = await import("../src/index.js");
  
  // Calling startServer with port 0 binds an ephemeral port safely
  const server = await startServer(0);
  assert.ok(server, "Server instance should be returned");
  assert.ok(server.listening, "Server should be listening after successful connection");
  
  const address = server.address();
  assert.ok(address && address.port, "Server should have a valid bound port");
  
  await new Promise((resolve) => server.close(resolve));
  assert.strictEqual(server.listening, false, "Server should close cleanly");
  await mongoose.disconnect();
});
