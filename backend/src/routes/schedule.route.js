import { Router } from "express";
import { authenticate } from "../middleware/auth.middleware.js";
import { createTelegramSchedules } from "../controllers/telegram.controller.js";
import {
  createFromPrescription,
  deleteSchedule,
  listSchedules,
} from "../controllers/schedule.controller.js";

const router = Router();

// Telegram-only schedule creation
router.post("/schedules", createTelegramSchedules);

// Prescription-based schedule creation & management
router.post("/schedule", authenticate, createFromPrescription);
router.get("/schedules", authenticate, listSchedules);
router.delete("/schedules/:id", authenticate, deleteSchedule);

export default router;
