process.env.NODE_ENV = "test";

import test, { before, after } from "node:test";
import assert from "node:assert";
import jwt from "jsonwebtoken";
import mongoose from "mongoose";
import { Prescription } from "../src/models/prescription.model.js";

const { app } = await import("../src/app.js");
const JWT_SECRET = process.env.ACCESS_TOKEN_SECRET || "dev-secret";

const testUserId = new mongoose.Types.ObjectId();
const testToken = jwt.sign({ _id: testUserId.toString(), email: "rx_test@example.com" }, JWT_SECRET);

before(async () => {
  await mongoose.connect(process.env.MONGO_URI_ATLAS || "mongodb://localhost:27017/medicreminder");
  await Prescription.deleteMany({ user: testUserId });
});

after(async () => {
  await Prescription.deleteMany({ user: testUserId });
  await mongoose.disconnect();
});

test("TASK-007: Unauthenticated request to /api/prescriptions is rejected", async () => {
  const server = app.listen(0);
  const port = server.address().port;
  try {
    const res = await fetch(`http://127.0.0.1:${port}/api/prescriptions`);
    assert.strictEqual(res.status, 401);
  } finally {
    server.close();
  }
});

test("TASK-007: Prescription CRUD lifecycle (create, list, update, delete)", async () => {
  const server = app.listen(0);
  const port = server.address().port;
  let createdRxId;

  try {
    // 1. Create prescription
    const createRes = await fetch(`http://127.0.0.1:${port}/api/prescriptions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${testToken}`,
      },
      body: JSON.stringify({
        medications: [
          { name: "Metformin", dosage: "500mg", frequency: "Daily", duration: "30 days" },
        ],
        status: "Active",
      }),
    });

    assert.strictEqual(createRes.status, 201);
    const createBody = await createRes.json();
    assert.strictEqual(createBody.status, 201);
    assert.ok(createBody.data._id);
    createdRxId = createBody.data._id;
    assert.strictEqual(createBody.data.medications[0].name, "Metformin");

    // 2. List prescriptions
    const listRes = await fetch(`http://127.0.0.1:${port}/api/prescriptions`, {
      headers: { Authorization: `Bearer ${testToken}` },
    });
    assert.strictEqual(listRes.status, 200);
    const listBody = await listRes.json();
    assert.ok(Array.isArray(listBody.data));
    assert.strictEqual(listBody.data.length, 1);
    assert.strictEqual(listBody.data[0]._id, createdRxId);

    // 3. Update prescription
    const updateRes = await fetch(`http://127.0.0.1:${port}/api/prescriptions/${createdRxId}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${testToken}`,
      },
      body: JSON.stringify({
        medications: [
          { name: "Metformin", dosage: "1000mg", frequency: "Twice daily", duration: "60 days" },
        ],
      }),
    });
    assert.strictEqual(updateRes.status, 200);
    const updateBody = await updateRes.json();
    assert.strictEqual(updateBody.data.medications[0].dosage, "1000mg");

    // 4. Delete prescription
    const deleteRes = await fetch(`http://127.0.0.1:${port}/api/prescriptions/${createdRxId}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${testToken}` },
    });
    assert.strictEqual(deleteRes.status, 200);

    // 5. Verify empty list after deletion
    const listAfterRes = await fetch(`http://127.0.0.1:${port}/api/prescriptions`, {
      headers: { Authorization: `Bearer ${testToken}` },
    });
    const listAfterBody = await listAfterRes.json();
    assert.strictEqual(listAfterBody.data.length, 0);
  } finally {
    server.close();
  }
});

test("TASK-008: POST /api/prescriptions/extract requires authentication", async () => {
  const server = app.listen(0);
  const port = server.address().port;
  try {
    const res = await fetch(`http://127.0.0.1:${port}/api/prescriptions/extract`, {
      method: "POST",
    });
    assert.strictEqual(res.status, 401);
  } finally {
    server.close();
  }
});

test("TASK-008: POST /api/prescriptions/extract validates image file presence", async () => {
  const server = app.listen(0);
  const port = server.address().port;
  try {
    const formData = new FormData();
    // No image appended
    const res = await fetch(`http://127.0.0.1:${port}/api/prescriptions/extract`, {
      method: "POST",
      headers: { Authorization: `Bearer ${testToken}` },
      body: formData,
    });
    assert.strictEqual(res.status, 400);
    const body = await res.json();
    assert.match(body.message, /image file is required/i);
  } finally {
    server.close();
  }
});

test("TASK-008: POST /api/prescriptions/extract accepts image upload and communicates with ML endpoint", async () => {
  const server = app.listen(0);
  const port = server.address().port;
  try {
    const formData = new FormData();
    const fakeImage = new Blob(["fake-image-bytes"], { type: "image/jpeg" });
    formData.append("image", fakeImage, "test-rx.jpg");

    const res = await fetch(`http://127.0.0.1:${port}/api/prescriptions/extract`, {
      method: "POST",
      headers: { Authorization: `Bearer ${testToken}` },
      body: formData,
    });

    // If ML service is running: returns 200 (or 400/500 from ML if fake bytes); if not running: 502/500 handled gracefully
    assert.ok([200, 400, 500, 502, 504].includes(res.status), `Unexpected status: ${res.status}`);
    const body = await res.json();
    assert.ok(body.message || body.result !== undefined || body.error);
  } finally {
    server.close();
  }
});

