import { Router } from "express";
import { authenticate, optionalAuthenticate } from "../middleware/auth.middleware.js";
import { createTelegramSchedules } from "../controllers/telegram.controller.js";
import {
  createFromPrescription,
  deleteSchedule,
  listSchedules,
  updateSchedule,
  extendSchedule,
} from "../controllers/schedule.controller.js";

const router = Router();

// Schedule creation
router.post("/schedules", optionalAuthenticate, createTelegramSchedules);
router.post("/schedule", authenticate, createFromPrescription);

// Schedule retrieval, editing, extending, and deletion
router.get("/schedules", optionalAuthenticate, listSchedules);
router.put("/schedules/:id", optionalAuthenticate, updateSchedule);
router.patch("/schedules/:id/extend", optionalAuthenticate, extendSchedule);
router.delete("/schedules/:id", optionalAuthenticate, deleteSchedule);

export default router;

