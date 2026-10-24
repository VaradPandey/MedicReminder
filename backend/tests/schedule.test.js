process.env.NODE_ENV = "test";

import test, { before, after } from "node:test";
import assert from "node:assert";
import jwt from "jsonwebtoken";
import mongoose from "mongoose";
import { Schedule } from "../src/models/schedule.model.js";

const { app } = await import("../src/app.js");
const JWT_SECRET = process.env.ACCESS_TOKEN_SECRET || "dev-secret";

const testUserId = new mongoose.Types.ObjectId();
const testToken = jwt.sign({ _id: testUserId.toString(), email: "schedule_test@example.com" }, JWT_SECRET);

before(async () => {
  await mongoose.connect(process.env.MONGO_URI_ATLAS || "mongodb://localhost:27017/medicreminder");
});

after(async () => {
  await Schedule.deleteMany({ user: testUserId });
  await mongoose.disconnect();
});

test("TASK-002: createFromPrescription creates schedules with medicine, time, duration without ValidationError", async () => {
  const server = app.listen(0);
  const port = server.address().port;

  try {
    const payload = {
      chatId: "987654321",
      items: [
        {
          medicine: "Amoxicillin 500mg",
          times: ["08:00", "20:00"],
          durationDays: 5,
        },
      ],
    };

    const res = await fetch(`http://127.0.0.1:${port}/api/schedule`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${testToken}`,
      },
      body: JSON.stringify(payload),
    });

    assert.strictEqual(res.status, 200);
    const body = await res.json();
    assert.strictEqual(body.success, true);
    assert.strictEqual(body.count, 2);

    const doc1 = body.data[0];
    assert.strictEqual(doc1.medicine, "Amoxicillin 500mg");
    assert.strictEqual(doc1.time, "08:00");
    assert.strictEqual(doc1.duration, 5);
    assert.strictEqual(doc1.cronTime, "0 8 * * *");
    assert.strictEqual(doc1.remainingRuns, 5);

    const doc2 = body.data[1];
    assert.strictEqual(doc2.medicine, "Amoxicillin 500mg");
    assert.strictEqual(doc2.time, "20:00");
    assert.strictEqual(doc2.duration, 5);
    assert.strictEqual(doc2.cronTime, "0 20 * * *");

    // Verify persisted in DB
    const persisted = await Schedule.find({ user: testUserId });
    assert.strictEqual(persisted.length, 2);
  } finally {
    server.close();
  }
});

test("TASK-002: createFromPrescription handles non-array items gracefully", async () => {
  const server = app.listen(0);
  const port = server.address().port;

  try {
    const res = await fetch(`http://127.0.0.1:${port}/api/schedule`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${testToken}`,
      },
      body: JSON.stringify({ chatId: "123", items: "invalid" }),
    });

    assert.strictEqual(res.status, 400);
    const body = await res.json();
    assert.strictEqual(body.success, false);
  } finally {
    server.close();
  }
});
