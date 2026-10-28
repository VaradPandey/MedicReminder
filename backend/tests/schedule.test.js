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

test("TASK-009: Schedule lifecycle - list, update, extend, and delete", async () => {
  const server = app.listen(0);
  const port = server.address().port;

  try {
    // 1. Create a schedule
    const scheduleDoc = await Schedule.create({
      user: testUserId,
      chatId: "987654321",
      medicine: "Metformin",
      dosage: "500mg",
      time: "09:00",
      duration: 7,
      remainingRuns: 7,
      cronTime: "0 9 * * *",
      message: "Metformin time reminder",
      active: true,
      startDate: new Date(),
    });

    // 2. List schedules
    const listRes = await fetch(`http://127.0.0.1:${port}/api/schedules`, {
      headers: {
        Authorization: `Bearer ${testToken}`,
      },
    });
    assert.strictEqual(listRes.status, 200);
    const listData = await listRes.json();
    assert.ok(Array.isArray(listData));
    const found = listData.find((s) => s._id === scheduleDoc._id.toString());
    assert.ok(found);
    assert.strictEqual(found.medicine, "Metformin");

    // 3. Update schedule (edit time and dosage)
    const updateRes = await fetch(`http://127.0.0.1:${port}/api/schedules/${scheduleDoc._id}`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${testToken}`,
      },
      body: JSON.stringify({
        medicine: "Metformin XR",
        dosage: "1000mg",
        time: "10:30",
        duration: 10,
      }),
    });
    assert.strictEqual(updateRes.status, 200);
    const updateBody = await updateRes.json();
    assert.strictEqual(updateBody.success, true);
    assert.strictEqual(updateBody.data.medicine, "Metformin XR");
    assert.strictEqual(updateBody.data.dosage, "1000mg");
    assert.strictEqual(updateBody.data.time, "10:30");
    assert.strictEqual(updateBody.data.cronTime, "30 10 * * *");

    // 4. Extend schedule by 5 days
    const extendRes = await fetch(`http://127.0.0.1:${port}/api/schedules/${scheduleDoc._id}/extend`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${testToken}`,
      },
      body: JSON.stringify({ days: 5 }),
    });
    assert.strictEqual(extendRes.status, 200);
    const extendBody = await extendRes.json();
    assert.strictEqual(extendBody.success, true);
    assert.strictEqual(extendBody.data.duration, 15);
    assert.strictEqual(extendBody.data.active, true);
    assert.ok(extendBody.data.endDate);

    // 5. Delete schedule
    const deleteRes = await fetch(`http://127.0.0.1:${port}/api/schedules/${scheduleDoc._id}`, {
      method: "DELETE",
      headers: {
        Authorization: `Bearer ${testToken}`,
      },
    });
    assert.strictEqual(deleteRes.status, 200);
    const deleteBody = await deleteRes.json();
    assert.strictEqual(deleteBody.success, true);

    // Verify removed from DB
    const checkDeleted = await Schedule.findById(scheduleDoc._id);
    assert.strictEqual(checkDeleted, null);
  } finally {
    server.close();
  }
});

