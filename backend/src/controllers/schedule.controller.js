import { Schedule } from "../models/schedule.model.js";
import { bot, cancelTelegramJob, startTelegramJob } from "../services/telegram.service.js";

// Example: { chatId, items:[{ medicine, times:[HH:mm,HH:mm], durationDays, dosage },{},{}] }
const createFromPrescription = async (req, res) => {
  try {
    const userId = req.user?._id;
    if (!userId) {
      return res.status(401).json({ success: false, message: "Unauthorized" });
    }
    const { chatId } = req.body;

    const created = [];

    if (Array.isArray(req.body.items)) {
      for (const it of req.body.items) {
        const medName = it.medicine || "Medicine";
        const dosage = it.dosage || "";
        const medTimes = Array.isArray(it.times) ? it.times : [];
        const runs = Number(it.durationDays) || 1;
        for (const t of medTimes) {
          const [hourStr, minuteStr] = String(t).split(":");
          const hour = Number(hourStr);
          const minute = Number(minuteStr);
          const cronTime = `${minute} ${hour} * * *`;
          const message = `${medName} time reminder`;

          const startDate = new Date();
          const endDate = new Date(startDate.getTime() + runs * 24 * 60 * 60 * 1000);
          endDate.setHours(hour, minute, 0, 0);

          const doc = await Schedule.create({
            user: userId,
            chatId,
            medicine: medName,
            dosage,
            time: String(t),
            duration: runs,
            message,
            cronTime,
            remainingRuns: runs,
            active: true,
            startDate,
            endDate,
          });

          // send immediate confirmation via Telegram if available
          try {
            if (bot && chatId) {
              await bot.sendMessage(chatId, `Reminder created: ${message}`);
            }
          } catch (e) {
            console.error("telegram send on create failed:", e?.message || e);
          }
          created.push(doc);
        }
      }
      return res.json({ success: true, count: created.length, data: created });
    }
    return res.status(400).json({ success: false, message: "items must be an array" });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
};

const deleteSchedule = async (req, res) => {
  try {
    const id = req.params.id;
    const filter = { _id: id };
    if (req.user?._id) {
      filter.$or = [{ user: req.user._id }, { user: null }];
    }
    const doc = await Schedule.findOneAndDelete(filter);
    if (doc) {
      cancelTelegramJob(id);
    }
    res.json({
      success: true,
      message: doc ? "Schedule removed" : "Schedule not found",
    });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
};

const listSchedules = async (req, res) => {
  try {
    const userId = req.user?._id;
    const chatId = req.query.chatId;

    let filter = {};
    if (userId && chatId) {
      filter = { $or: [{ user: userId }, { chatId: String(chatId) }] };
    } else if (userId) {
      filter = { user: userId };
    } else if (chatId) {
      filter = { chatId: String(chatId) };
    } else {
      // If unauthenticated and no chatId provided
      return res.json([]);
    }

    const data = await Schedule.find(filter).sort({ createdAt: -1 });
    res.json(data);
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
};

const updateSchedule = async (req, res) => {
  try {
    const id = req.params.id;
    const filter = { _id: id };
    if (req.user?._id) {
      filter.$or = [{ user: req.user._id }, { user: null }];
    }
    const schedule = await Schedule.findOne(filter);
    if (!schedule) {
      return res.status(404).json({ success: false, message: "Schedule not found" });
    }

    const { medicine, dosage, time, duration, active, remainingRuns } = req.body;

    if (medicine) schedule.medicine = medicine;
    if (dosage !== undefined) schedule.dosage = dosage;
    if (duration !== undefined) {
      const durNum = Number(duration);
      if (!isNaN(durNum) && durNum > 0) {
        schedule.duration = durNum;
        if (remainingRuns === undefined) {
          schedule.remainingRuns = durNum;
        }
      }
    }
    if (remainingRuns !== undefined) {
      schedule.remainingRuns = Number(remainingRuns);
    }
    if (active !== undefined) {
      schedule.active = Boolean(active);
    }

    if (time) {
      const [hourStr, minuteStr] = String(time).split(":");
      const hh = Number(hourStr);
      const mm = Number(minuteStr);
      if (!isNaN(hh) && !isNaN(mm)) {
        schedule.time = time;
        schedule.cronTime = `${mm} ${hh} * * *`;
      }
    }
    schedule.message = `${schedule.medicine} time reminder`;

    // Recalculate endDate
    const start = schedule.startDate || schedule.createdAt || new Date();
    const durDays = schedule.duration || 1;
    const end = new Date(new Date(start).getTime() + durDays * 24 * 60 * 60 * 1000);
    if (schedule.time) {
      const [hh, mm] = schedule.time.split(":").map(Number);
      if (!isNaN(hh) && !isNaN(mm)) {
        end.setHours(hh, mm, 0, 0);
      }
    }
    schedule.endDate = end;

    await schedule.save();

    // Refresh Telegram cron job
    cancelTelegramJob(id);
    if (schedule.active && schedule.remainingRuns > 0) {
      await startTelegramJob(schedule);
    }

    res.json({ success: true, data: schedule, message: "Schedule updated successfully" });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
};

const extendSchedule = async (req, res) => {
  try {
    const id = req.params.id;
    const filter = { _id: id };
    if (req.user?._id) {
      filter.$or = [{ user: req.user._id }, { user: null }];
    }
    const schedule = await Schedule.findOne(filter);
    if (!schedule) {
      return res.status(404).json({ success: false, message: "Schedule not found" });
    }

    const additionalDays = Number(req.body.days) || 7;
    schedule.duration = (schedule.duration || 0) + additionalDays;
    schedule.remainingRuns = (schedule.remainingRuns || 0) + additionalDays;
    schedule.active = true;

    // Extend endDate
    const now = new Date();
    const baseDate = schedule.endDate && new Date(schedule.endDate) > now
      ? new Date(schedule.endDate)
      : now;
    const newEnd = new Date(baseDate.getTime() + additionalDays * 24 * 60 * 60 * 1000);
    if (schedule.time) {
      const [hh, mm] = schedule.time.split(":").map(Number);
      if (!isNaN(hh) && !isNaN(mm)) {
        newEnd.setHours(hh, mm, 0, 0);
      }
    }
    schedule.endDate = newEnd;

    await schedule.save();

    // Restart Telegram cron job
    cancelTelegramJob(id);
    await startTelegramJob(schedule);

    // Optional Telegram notification
    try {
      if (bot && schedule.chatId) {
        await bot.sendMessage(
          schedule.chatId,
          `✅ Reminder extended: ${schedule.medicine} schedule has been extended by ${additionalDays} days (till ${newEnd.toLocaleDateString()}).`
        );
      }
    } catch (e) {
      console.warn("[telegram] extend notice send failed:", e?.message);
    }

    res.json({
      success: true,
      data: schedule,
      message: `Schedule extended by ${additionalDays} days`,
    });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
};

export { createFromPrescription, deleteSchedule, listSchedules, updateSchedule, extendSchedule };

