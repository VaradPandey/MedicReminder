process.env.NODE_ENV = "test";

import test, { before, after } from "node:test";
import assert from "node:assert";
import jwt from "jsonwebtoken";
import mongoose from "mongoose";

const { app } = await import("../src/app.js");
const JWT_SECRET = process.env.ACCESS_TOKEN_SECRET || "dev-secret";

before(async () => {
  await mongoose.connect(process.env.MONGO_URI_ATLAS || "mongodb://localhost:27017/medicreminder");
});

after(async () => {
  await mongoose.disconnect();
});

test("TASK-001: Unauthenticated requests to /api/debug/schedules are rejected with 401", async () => {
  const server = app.listen(0);
  const port = server.address().port;

  try {
    const res = await fetch(`http://127.0.0.1:${port}/api/debug/schedules`);
    assert.strictEqual(res.status, 401);
    const body = await res.json();
    assert.strictEqual(body.message, "Token Not Found");
  } finally {
    server.close();
  }
});

test("TASK-001: Unauthenticated requests to /api/debug/send are rejected with 401", async () => {
  const server = app.listen(0);
  const port = server.address().port;

  try {
    const res = await fetch(`http://127.0.0.1:${port}/api/debug/send`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chatId: "123", message: "test" }),
    });
    assert.strictEqual(res.status, 401);
    const body = await res.json();
    assert.strictEqual(body.message, "Token Not Found");
  } finally {
    server.close();
  }
});

test("TASK-001: Invalid token to /api/debug/schedules returns 401 Unauthorized", async () => {
  const server = app.listen(0);
  const port = server.address().port;

  try {
    const res = await fetch(`http://127.0.0.1:${port}/api/debug/schedules`, {
      headers: { Authorization: "Bearer invalid.jwt.token" },
    });
    assert.strictEqual(res.status, 401);
    const body = await res.json();
    assert.strictEqual(body.message, "Invalid Token");
  } finally {
    server.close();
  }
});

test("TASK-001: Authenticated request with valid JWT passes authentication middleware", async () => {
  const server = app.listen(0);
  const port = server.address().port;
  const token = jwt.sign({ _id: "testuser123", email: "test@example.com" }, JWT_SECRET);

  try {
    const res = await fetch(`http://127.0.0.1:${port}/api/debug/schedules`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    assert.strictEqual(res.status, 200);
    const body = await res.json();
    assert.strictEqual(body.success, true);
    assert.ok(Array.isArray(body.data));
  } finally {
    server.close();
  }
});
