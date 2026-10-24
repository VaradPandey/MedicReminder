import { Router } from "express";
import multer from "multer";
import { authenticate } from "../middleware/auth.middleware.js";
import {
  createPrescription,
  listPrescriptions,
  deletePrescription,
  updatePrescription,
  extractPrescription,
} from "../controllers/prescription.controller.js";

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 10 * 1024 * 1024 },
});

const router = Router();

router.post("/prescriptions", authenticate, createPrescription);
router.get("/prescriptions", authenticate, listPrescriptions);
router.delete("/prescriptions/:id", authenticate, deletePrescription);
router.put("/prescriptions/:id", authenticate, updatePrescription);
router.post("/prescriptions/extract", authenticate, upload.single("image"), extractPrescription);

export default router;
