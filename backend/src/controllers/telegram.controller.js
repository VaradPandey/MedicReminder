import { Schedule } from "../models/schedule.model.js";
import { startTelegramJob } from "../services/telegram.service.js";

export const createTelegramSchedules = async (req, res) => {
  try {
    console.log("[DEBUG] /api/schedules payload:", req.body);

    const userId = req.user?._id || null;

    const { chatId, schedules = [] } = req.body;
    if (!chatId) return res.status(400).json({ success: false, message: "chatId is required" });
    if (!Array.isArray(schedules) || schedules.length === 0)
      return res.status(400).json({ success: false, message: "schedules[] is required" });

    const created = [];
    for (const s of schedules) {
      const medicine = s.medicine || "Medicine";
      const [hh, mm] = String(s.time || "").split(":").map(n => parseInt(n, 10));
      if (Number.isNaN(hh) || Number.isNaN(mm)) {
        return res.status(400).json({ success: false, message: `Invalid time for ${medicine}` });
      }
      const duration = parseInt(s.duration, 10) || 1;

      const cronTime = `${mm} ${hh} * * *`;
      const message = `${medicine} time reminder`;

      const startDate = new Date();
      const endDate = new Date(startDate.getTime() + duration * 24 * 60 * 60 * 1000);
      endDate.setHours(hh, mm, 0, 0);

      const doc = await Schedule.create({
        user: userId,
        chatId,
        medicine,
        dosage: s.dosage || "",
        message,
        cronTime,
        time: s.time,          // <-- add this
        duration,              // <-- add this
        remainingRuns: duration,
        active: true,
        startDate,
        endDate,
      });

      await startTelegramJob(doc);
      created.push(doc);
    }
    return res.json({ success: true, count: created.length, data: created });
  } catch (err) {
    console.error("[createTelegramSchedules ERROR]", err);
    return res.status(500).json({ success: false, error: err.message });
  }
};
