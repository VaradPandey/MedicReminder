import { Prescription } from "../models/prescription.model.js";

export const createPrescription = async (req, res) => {
  try {
    const userId = req.user?._id;
    if (!userId)
      return res.status(401).json({ status: 401, message: "Unauthorized" });

    const body = req.body || {};

    // Normalize medications: ensure array
    let medications = body.medications;
    if (!Array.isArray(medications)) {
      if (medications && typeof medications === "object")
        medications = [medications];
      else medications = [];
    }

    // Create new prescription — only medications and status now
    const doc = await Prescription.create({
      user: userId,
      medications: medications.map((m) => ({
        name: m.name || m.medicine || "",
        dosage: m.dosage || m.dose || "",
        frequency: m.frequency || m.freq || "",
        duration: m.duration || "",
        instructions: m.instructions || "",
      })),
      status: body.status || "Active",
    });

    res
      .status(201)
      .json({ status: 201, message: "Prescription saved", data: doc });
  } catch (err) {
    res.status(500).json({
      status: 500,
      message: "Failed to save prescription",
      error: err.message,
    });
  }
};

export const listPrescriptions = async (req, res) => {
  try {
    const userId = req.user?._id;
    if (!userId)
      return res.status(401).json({ status: 401, message: "Unauthorized" });

    const docs = await Prescription.find({ user: userId }).sort({
      createdAt: -1,
    });

    res.json({ status: 200, message: "OK", data: docs });
  } catch (err) {
    res.status(500).json({
      status: 500,
      message: "Failed to list prescriptions",
      error: err.message,
    });
  }
};

export const deletePrescription = async (req, res) => {
  try {
    const userId = req.user?._id;
    if (!userId)
      return res.status(401).json({ status: 401, message: "Unauthorized" });

    const { id } = req.params;
    if (!id)
      return res.status(400).json({ status: 400, message: "Missing prescription ID" });

    const doc = await Prescription.findOneAndDelete({ _id: id, user: userId });
    if (!doc)
      return res.status(404).json({ status: 404, message: "Prescription not found" });

    res.json({ status: 200, message: "Prescription deleted successfully" });
  } catch (err) {
    res.status(500).json({
      status: 500,
      message: "Failed to delete prescription",
      error: err.message,
    });
  }
};

export const updatePrescription = async (req, res) => {
  try {
    const userId = req.user?._id;
    if (!userId)
      return res.status(401).json({ status: 401, message: "Unauthorized" });

    const { id } = req.params;
    const { medications } = req.body;

    if (!Array.isArray(medications))
      return res
        .status(400)
        .json({ status: 400, message: "Invalid medications format" });

    const doc = await Prescription.findOneAndUpdate(
      { _id: id, user: userId },
      { medications },
      { new: true }
    );

    if (!doc)
      return res
        .status(404)
        .json({ status: 404, message: "Prescription not found" });

    const updated = doc.toObject();
    updated.id = updated._id;

    res.json({
      status: 200,
      message: "Prescription updated successfully",
      data: updated,
    });
  } catch (err) {
    res.status(500).json({
      status: 500,
      message: "Failed to update prescription",
      error: err.message,
    });
  }
};

export const extractPrescription = async (req, res) => {
  const startTime = Date.now();
  const reqId = req.headers["x-request-id"] || Math.random().toString(36).substring(2, 10);
  const getLogTimestamp = () => new Date().toISOString().replace("T", " ").substring(0, 19);

  try {
    const userId = req.user?._id;
    if (!userId) {
      console.warn(`${getLogTimestamp()} WARN [OCR][BACKEND] Unauthorized request request_id=${reqId}`);
      return res.status(401).json({ status: 401, message: "Unauthorized" });
    }

    console.log(`${getLogTimestamp()} INFO [OCR][BACKEND] Incoming prescription extraction request user_id=${userId} request_id=${reqId}`);

    if (!req.file) {
      console.warn(`${getLogTimestamp()} WARN [OCR][BACKEND] Request validation failed request_id=${reqId} reason='no image file attached'`);
      return res.status(400).json({ status: 400, message: "image file is required" });
    }

    console.log(
      `${getLogTimestamp()} INFO [OCR][BACKEND] Request validation passed request_id=${reqId} ` +
      `filename='${req.file.originalname}' mimetype='${req.file.mimetype}' size_bytes=${req.file.size}`
    );

    const ML_SERVICE_URL = process.env.ML_SERVICE_URL || "http://127.0.0.1:5000/extract";

    const formData = new FormData();
    const blob = new Blob([req.file.buffer], { type: req.file.mimetype || "image/jpeg" });
    formData.append("image", blob, req.file.originalname || "prescription.jpg");

    console.log(`${getLogTimestamp()} INFO [OCR][BACKEND] Forwarding request to ML service request_id=${reqId} url=${ML_SERVICE_URL}`);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 90_000);

    const mlResponse = await fetch(ML_SERVICE_URL, {
      method: "POST",
      body: formData,
      headers: {
        "X-Request-Id": reqId,
      },
      signal: controller.signal,
    });
    clearTimeout(timeout);

    const durationMs = Date.now() - startTime;
    console.log(`${getLogTimestamp()} INFO [OCR][BACKEND] ML service response received request_id=${reqId} status=${mlResponse.status} duration_ms=${durationMs}`);

    if (!mlResponse.ok) {
      let errorDetail = "";
      try {
        const errorJson = await mlResponse.json();
        errorDetail = errorJson.error || errorJson.message || JSON.stringify(errorJson);
      } catch {
        errorDetail = await mlResponse.text();
      }
      const sanitizedError = String(errorDetail).replace(/[\r\n]+/g, " ").substring(0, 200);
      console.error(`${getLogTimestamp()} ERROR [OCR][BACKEND] ML OCR service error request_id=${reqId} duration_ms=${durationMs} error='${sanitizedError}'`);
      return res.status(mlResponse.status || 502).json({
        status: mlResponse.status || 502,
        message: sanitizedError || "ML OCR service error",
        error: sanitizedError,
        requestId: reqId,
      });
    }

    const data = await mlResponse.json();
    console.log(`${getLogTimestamp()} INFO [OCR][BACKEND] Extraction completed successfully request_id=${reqId} duration_ms=${durationMs} status=200`);

    return res.status(200).json({
      status: 200,
      success: true,
      result: data.result || "",
      requestId: reqId,
    });
  } catch (err) {
    const durationMs = Date.now() - startTime;
    if (err.name === "AbortError") {
      console.error(`${getLogTimestamp()} ERROR [OCR][BACKEND] ML OCR service timed out request_id=${reqId} duration_ms=${durationMs}`);
      return res.status(504).json({
        status: 504,
        message: "ML OCR service timed out after 90s. The vision model is running slowly. Please retry in a few moments.",
        requestId: reqId,
      });
    }
    const sanitizedError = String(err.message || err).replace(/[\r\n]+/g, " ").substring(0, 200);
    console.error(`${getLogTimestamp()} ERROR [OCR][BACKEND] Extraction request failed request_id=${reqId} duration_ms=${durationMs} error='${sanitizedError}'`);
    return res.status(500).json({
      status: 500,
      message: "Failed to extract prescription",
      error: sanitizedError,
      requestId: reqId,
    });
  }
};

