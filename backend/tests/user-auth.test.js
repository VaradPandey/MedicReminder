process.env.NODE_ENV = "test";

import test, { before, after } from "node:test";
import assert from "node:assert";
import mongoose from "mongoose";
import { User } from "../src/models/user.model.js";

const { app } = await import("../src/app.js");

const testUsername = `user_test_${Date.now()}`;
const testEmail = `user_test_${Date.now()}@example.com`;
const testPassword = "SecretPassword123!";

before(async () => {
  await mongoose.connect(process.env.MONGO_URI_ATLAS || "mongodb://localhost:27017/medicreminder");
  await User.deleteMany({ email: { $regex: /user_test_/ } });
});

after(async () => {
  await User.deleteMany({ email: { $regex: /user_test_/ } });
  await mongoose.disconnect();
});

test("TASK-004: Registration validates required fields", async () => {
  const server = app.listen(0);
  const port = server.address().port;
  try {
    const res = await fetch(`http://127.0.0.1:${port}/api/users/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: "incomplete" }),
    });

    assert.strictEqual(res.status, 400);
    const body = await res.json();
    assert.strictEqual(body.status, 400);
    assert.match(body.message, /All fields are required/);
  } finally {
    server.close();
  }
});

test("TASK-004: Registration creates user and does NOT return password hash", async () => {
  const server = app.listen(0);
  const port = server.address().port;
  try {
    const res = await fetch(`http://127.0.0.1:${port}/api/users/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: testUsername,
        email: testEmail,
        phone: "+911234567890",
        password: testPassword,
      }),
    });

    assert.strictEqual(res.status, 201);
    const body = await res.json();
    assert.strictEqual(body.status, 201);
    assert.strictEqual(body.message, "User created successfully");
    assert.ok(body.user, "User object should be returned");
    assert.strictEqual(body.user.password, undefined, "Password hash must NOT be returned in response");
    assert.strictEqual(body.user.username, testUsername);
    assert.strictEqual(body.user.email, testEmail);

    // Verify persisted in DB with bcrypt hash
    const dbUser = await User.findOne({ username: testUsername });
    assert.ok(dbUser, "User should exist in MongoDB");
    assert.ok(dbUser.password.startsWith("$2b$"), "Password should be bcrypt hashed in DB");
  } finally {
    server.close();
  }
});

test("TASK-004: Duplicate email returns HTTP 400 error", async () => {
  const server = app.listen(0);
  const port = server.address().port;
  try {
    const res = await fetch(`http://127.0.0.1:${port}/api/users/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: `diff_${Date.now()}`,
        email: testEmail,
        phone: "+911234567890",
        password: testPassword,
      }),
    });

    assert.strictEqual(res.status, 400);
    const body = await res.json();
    assert.strictEqual(body.status, 400);
    assert.match(body.message, /already exists|already taken/i);
  } finally {
    server.close();
  }
});

test("TASK-004: Duplicate username returns HTTP 400 error", async () => {
  const server = app.listen(0);
  const port = server.address().port;
  try {
    const res = await fetch(`http://127.0.0.1:${port}/api/users/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: testUsername,
        email: `diff_${Date.now()}@example.com`,
        phone: "+911234567890",
        password: testPassword,
      }),
    });

    assert.strictEqual(res.status, 400);
    const body = await res.json();
    assert.strictEqual(body.status, 400);
    assert.match(body.message, /already exists|already taken/i);
  } finally {
    server.close();
  }
});

test("TASK-004: Login sanitizes user and returns HTTP 200 with token", async () => {
  const server = app.listen(0);
  const port = server.address().port;
  try {
    const res = await fetch(`http://127.0.0.1:${port}/api/users/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: testUsername,
        password: testPassword,
      }),
    });

    assert.strictEqual(res.status, 200);
    const body = await res.json();
    assert.strictEqual(body.status, 200);
    assert.ok(body.token, "JWT token should be returned");
    assert.strictEqual(body.user.password, undefined, "Password hash must NOT be returned");
  } finally {
    server.close();
  }
});

test("Issue 3: /api/users/auth/me returns HTTP 401 Unauthorized when unauthenticated", async () => {
  const server = app.listen(0);
  const port = server.address().port;
  try {
    const res = await fetch(`http://127.0.0.1:${port}/api/users/auth/me`);
    assert.strictEqual(res.status, 401, "Unauthenticated session check must return 401, not 400");
    const body = await res.json();
    assert.strictEqual(body.status, 401);
    assert.strictEqual(body.message, "Token Not Found");
  } finally {
    server.close();
  }
});

test("Issue 3: /api/users/auth/me returns HTTP 200 with user data when authenticated", async () => {
  const server = app.listen(0);
  const port = server.address().port;
  try {
    // First login to get token
    const loginRes = await fetch(`http://127.0.0.1:${port}/api/users/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: testUsername,
        password: testPassword,
      }),
    });
    const loginBody = await loginRes.json();
    const token = loginBody.token;

    // Check /api/users/auth/me with Bearer token
    const meRes = await fetch(`http://127.0.0.1:${port}/api/users/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    assert.strictEqual(meRes.status, 200);
    const meBody = await meRes.json();
    assert.strictEqual(meBody.status, 200);
    assert.strictEqual(meBody.data.username, testUsername);
    assert.strictEqual(meBody.data.password, undefined, "Password must not be returned");
  } finally {
    server.close();
  }
});
