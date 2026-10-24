process.env.NODE_ENV = "test";

import test from "node:test";
import assert from "node:assert";

const { app } = await import("../src/app.js");

test("Issue 2: POST /api/predict validates symptoms input", async () => {
  const server = app.listen(0);
  const port = server.address().port;

  try {
    const res = await fetch(`http://127.0.0.1:${port}/api/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symptoms: [] }),
    });

    assert.strictEqual(res.status, 400);
    const body = await res.json();
    assert.match(body.error, /symptoms must be a non-empty array/i);
  } finally {
    server.close();
  }
});
