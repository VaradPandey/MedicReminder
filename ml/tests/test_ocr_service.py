import io
import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock
from PIL import Image

# Ensure ml directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import test_server_pythonic as srv
from image_preprocessor import preprocess_prescription_image, validate_image_file, MAX_FILE_SIZE_BYTES
from ocr_engine import PrescriptionOCREngine, PrescriptionOCRError, GeminiVisionProvider, OpenRouterVisionProvider

def create_mock_completion(content=None, reasoning=None, finish_reason="stop", refusal=None, error=None):
    """Creates a mock ChatCompletion object mimicking OpenAI / OpenRouter response."""
    resp = MagicMock()
    resp.error = error
    if error and not content:
        resp.choices = None
        return resp

    msg = MagicMock()
    msg.content = content
    msg.reasoning = reasoning
    msg.reasoning_content = None
    msg.refusal = refusal

    choice = MagicMock()
    choice.finish_reason = finish_reason
    choice.message = msg

    resp.choices = [choice]
    return resp

class TestOcrService(unittest.TestCase):
    def setUp(self):
        self.app = srv.app
        self.client = self.app.test_client()

        # Temporary dummy test image for engine calls
        buf = io.BytesIO()
        Image.new('RGB', (100, 100), color='white').save(buf, format='PNG')
        self.test_img_bytes = buf.getvalue()

        self.temp_img = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        self.temp_img.write(self.test_img_bytes)
        self.temp_img.close()

    def tearDown(self):
        if os.path.exists(self.temp_img.name):
            try:
                os.remove(self.temp_img.name)
            except OSError:
                pass

    def test_home_endpoint(self):
        """GET / returns 200 OK with service metadata."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "online")
        self.assertIn("service", data)
        self.assertIn(data.get("engine"), ("gemini", "openrouter_vision", "openai"))

    def test_health_endpoint(self):
        """GET /health returns 200 OK."""
        res = self.client.get('/health')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn(data.get("engine"), ("gemini", "openrouter_vision", "openai"))

    def test_extract_missing_image(self):
        """POST /extract without image returns 400."""
        res = self.client.post('/extract', data={})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("error", data)
        self.assertIn("image file is required", data["error"].lower())

    def test_extract_empty_file(self):
        """POST /extract with 0-byte file returns 400."""
        data = {
            'image': (io.BytesIO(b""), 'empty.png')
        }
        res = self.client.post('/extract', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("empty", data["error"].lower())

    def test_extract_unsupported_file_type(self):
        """POST /extract with non-image file returns 400."""
        data = {
            'image': (io.BytesIO(b"dummy executable bytes"), 'test.exe')
        }
        res = self.client.post('/extract', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("Unsupported file type", data["error"])

    def test_extract_oversized_file(self):
        """POST /extract with image exceeding 15MB returns 400."""
        oversized_data = b"0" * (MAX_FILE_SIZE_BYTES + 1024)
        data = {
            'image': (io.BytesIO(oversized_data), 'huge.png')
        }
        res = self.client.post('/extract', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("exceeds", data["error"].lower())

    def test_image_preprocessor_resizing(self):
        """Oversized image is correctly downscaled maintaining aspect ratio."""
        huge_img = Image.new('RGB', (4000, 2000), color='white')
        processed, meta = preprocess_prescription_image(huge_img, max_dimension=1000)
        self.assertTrue(meta["resized"])
        self.assertEqual(processed.size[0], 1000)
        self.assertEqual(processed.size[1], 500)

    @patch.dict(os.environ, {"MOCK_OCR": "true"})
    def test_extract_mock_ocr_mode(self):
        """When MOCK_OCR=true, returns 200 with structured mock prescription JSON."""
        data = {'image': (io.BytesIO(self.test_img_bytes), 'rx.png')}
        res = self.client.post('/extract', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertIn("result", json_data)
        parsed = json.loads(json_data["result"])
        self.assertEqual(parsed["patientName"], "Jane Doe")
        self.assertTrue(len(parsed["medications"]) > 0)
        self.assertTrue(parsed["needs_review"])

    # --------------------------------------------------------------------------
    # 1. Valid JSON prescription response
    # --------------------------------------------------------------------------
    def test_engine_valid_json_response(self):
        """Engine parses direct valid JSON model response into structured schema."""
        valid_json = json.dumps({
            "patientName": "Mr. Aman",
            "doctorName": "Dr. Sachin Patil",
            "dateIssued": "22/05/2025",
            "diagnosis": "Fever",
            "medications": [
                {
                    "name": "Opox-CV",
                    "strength": "200mg",
                    "dosage": "1 tablet",
                    "frequency": "Twice daily",
                    "duration": "6 days",
                    "instructions": "After food",
                    "confidence": 0.95
                }
            ],
            "unreadable_fields": [],
            "needs_review": True
        })

        mock_resp = create_mock_completion(content=valid_json, finish_reason="stop")
        engine = PrescriptionOCREngine()
        engine.client = MagicMock()
        engine.client.chat.completions.create.return_value = mock_resp

        result = engine.process_prescription(self.temp_img.name)
        self.assertEqual(result["patientName"], "Mr. Aman")
        self.assertEqual(result["doctorName"], "Dr. Sachin Patil")
        self.assertEqual(len(result["medications"]), 1)
        self.assertEqual(result["medications"][0]["name"], "Opox-CV")
        self.assertTrue(result["needs_review"])

    # --------------------------------------------------------------------------
    # 2. JSON wrapped in Markdown fences
    # --------------------------------------------------------------------------
    def test_engine_json_wrapped_in_markdown_fences(self):
        """Engine extracts JSON wrapped in ```json ... ``` with conversational preambles."""
        fenced_content = (
            "Here is the transcribed prescription from the image:\n\n"
            "```json\n"
            "{\n"
            '  "patientName": "Vikram Malhotra",\n'
            '  "doctorName": "Dr. Rajesh Sharma",\n'
            '  "dateIssued": "24/10/2026",\n'
            '  "diagnosis": "Bronchitis",\n'
            '  "medications": [\n'
            '    {\n'
            '      "name": "Augmentin",\n'
            '      "strength": "625mg",\n'
            '      "dosage": "1 tablet",\n'
            '      "frequency": "Twice daily",\n'
            '      "duration": "5 days",\n'
            '      "instructions": "After food",\n'
            '      "confidence": 0.95\n'
            '    }\n'
            '  ],\n'
            '  "unreadable_fields": [],\n'
            '  "needs_review": true\n'
            "}\n"
            "```\n\n"
            "Please review carefully."
        )

        mock_resp = create_mock_completion(content=fenced_content, finish_reason="stop")
        engine = PrescriptionOCREngine()
        engine.client = MagicMock()
        engine.client.chat.completions.create.return_value = mock_resp

        result = engine.process_prescription(self.temp_img.name)
        self.assertEqual(result["patientName"], "Vikram Malhotra")
        self.assertEqual(len(result["medications"]), 1)
        self.assertEqual(result["medications"][0]["name"], "Augmentin")
        self.assertTrue(result["needs_review"])

    # --------------------------------------------------------------------------
    # 3. Empty response content
    # --------------------------------------------------------------------------
    def test_engine_empty_response_content(self):
        """Engine raises 502 when response content is empty and no reasoning JSON is found."""
        mock_resp = create_mock_completion(content="", reasoning="", finish_reason="stop")
        engine = PrescriptionOCREngine()
        engine.client = MagicMock()
        engine.client.chat.completions.create.return_value = mock_resp

        with self.assertRaises(PrescriptionOCRError) as ctx:
            engine.process_prescription(self.temp_img.name)
        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("empty text content", str(ctx.exception).lower())

    # --------------------------------------------------------------------------
    # 4. Missing choices or message content
    # --------------------------------------------------------------------------
    def test_engine_missing_choices_or_message(self):
        """Engine raises 502 when choices list is empty or message is missing."""
        # Empty choices
        mock_resp_empty = MagicMock()
        mock_resp_empty.choices = []
        mock_resp_empty.error = None

        engine = PrescriptionOCREngine()
        engine.client = MagicMock()
        engine.client.chat.completions.create.return_value = mock_resp_empty

        with self.assertRaises(PrescriptionOCRError) as ctx:
            engine.process_prescription(self.temp_img.name)
        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("empty choices list", str(ctx.exception).lower())

        # Missing message in choice
        mock_choice = MagicMock()
        mock_choice.message = None
        mock_choice.finish_reason = "stop"
        mock_resp_no_msg = MagicMock()
        mock_resp_no_msg.choices = [mock_choice]
        mock_resp_no_msg.error = None
        engine.client.chat.completions.create.return_value = mock_resp_no_msg

        with self.assertRaises(PrescriptionOCRError) as ctx:
            engine.process_prescription(self.temp_img.name)
        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("valid message", str(ctx.exception).lower())

    # --------------------------------------------------------------------------
    # 5. Reasoning-only or malformed response
    # --------------------------------------------------------------------------
    def test_engine_reasoning_only_without_json(self):
        """Engine raises 502 when response contains only plain text without structured JSON."""
        non_json_content = "I can see a prescription signed by Dr. Patil, but I cannot decipher the medications."
        mock_resp = create_mock_completion(content=non_json_content, finish_reason="stop")

        engine = PrescriptionOCREngine()
        engine.client = MagicMock()
        engine.client.chat.completions.create.return_value = mock_resp

        with self.assertRaises(PrescriptionOCRError) as ctx:
            engine.process_prescription(self.temp_img.name)
        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("failed to parse structured json", str(ctx.exception).lower())

    def test_engine_reasoning_fallback_with_embedded_json(self):
        """Engine recovers structured JSON when content is empty but reasoning contains valid JSON."""
        embedded_json = '{\n  "patientName": "Aman",\n  "doctorName": "Dr. Patil",\n  "medications": []\n}'
        mock_resp = create_mock_completion(
            content="",
            reasoning=f"Analyzing image...\n{embedded_json}\nFinished thinking.",
            finish_reason="stop"
        )

        engine = PrescriptionOCREngine()
        engine.client = MagicMock()
        engine.client.chat.completions.create.return_value = mock_resp

        result = engine.process_prescription(self.temp_img.name)
        self.assertEqual(result["patientName"], "Aman")
        self.assertEqual(result["doctorName"], "Dr. Patil")
        self.assertTrue(result["needs_review"])

    # --------------------------------------------------------------------------
    # 6. Truncated response (finish_reason='length')
    # --------------------------------------------------------------------------
    def test_engine_truncated_response(self):
        """Engine identifies truncated response with finish_reason='length' and returns clean 502."""
        truncated_content = '{\n  "patientName": "Mr. Aman",\n  "doctorName": "Dr. Sachin Patil",\n  "medications": ['
        mock_resp = create_mock_completion(content=truncated_content, finish_reason="length")

        engine = PrescriptionOCREngine()
        engine.client = MagicMock()
        engine.client.chat.completions.create.return_value = mock_resp

        with self.assertRaises(PrescriptionOCRError) as ctx:
            engine.process_prescription(self.temp_img.name)
        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("truncated", str(ctx.exception).lower())

    # --------------------------------------------------------------------------
    # 7. Provider HTTP 429 and 5xx errors
    # --------------------------------------------------------------------------
    def test_engine_provider_rate_limit_429(self):
        """Engine maps provider worker capacity or rate limit errors to 429."""
        mock_resp = create_mock_completion(
            error={'message': 'Upstream error from Nvidia: ResourceExhausted: Worker local total request limit reached (16/16)', 'code': 502}
        )
        engine = PrescriptionOCREngine()
        engine.provider = OpenRouterVisionProvider()
        engine.provider.api_key = "test_key"
        engine.client = MagicMock()
        engine.client.chat.completions.create.return_value = mock_resp

        with self.assertRaises(PrescriptionOCRError) as ctx:
            engine.process_prescription(self.temp_img.name)
        self.assertEqual(ctx.exception.status_code, 429)
        self.assertIn("busy", str(ctx.exception).lower())

    def test_engine_provider_5xx_error(self):
        """Engine maps provider internal errors to 502."""
        mock_resp = create_mock_completion(
            error={'message': 'Internal Server Error at upstream provider', 'code': 500}
        )
        engine = PrescriptionOCREngine()
        engine.provider = OpenRouterVisionProvider()
        engine.provider.api_key = "test_key"
        engine.client = MagicMock()
        engine.client.chat.completions.create.return_value = mock_resp

        with self.assertRaises(PrescriptionOCRError) as ctx:
            engine.process_prescription(self.temp_img.name)
        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("provider error", str(ctx.exception).lower())

    # --------------------------------------------------------------------------
    # 8. Retry policy and timeout behavior
    # --------------------------------------------------------------------------
    def test_engine_timeout_behavior(self):
        """Engine maps API timeout errors to 504 Gateway Timeout and never retries."""
        import openai
        engine = PrescriptionOCREngine()
        engine.provider = OpenRouterVisionProvider()
        engine.provider.api_key = "test_key"
        engine.client = MagicMock()
        engine.client.chat.completions.create.side_effect = openai.APITimeoutError(request=MagicMock())

        with self.assertRaises(PrescriptionOCRError) as ctx:
            engine.process_prescription(self.temp_img.name)
        self.assertEqual(ctx.exception.status_code, 504)
        self.assertIn("timed out after 75s", str(ctx.exception).lower())
        self.assertEqual(engine.client.chat.completions.create.call_count, 1)

    def test_engine_401_authentication_error_not_retried(self):
        """Engine aborts immediately on 401/unauthorized without retrying."""
        engine = PrescriptionOCREngine()
        engine.provider = OpenRouterVisionProvider()
        engine.provider.api_key = "test_key"
        engine.client = MagicMock()
        engine.client.chat.completions.create.side_effect = Exception("HTTP 401 Unauthorized: Invalid API key")

        with self.assertRaises(PrescriptionOCRError) as ctx:
            engine.process_prescription(self.temp_img.name)
        self.assertEqual(ctx.exception.status_code, 502)
        self.assertIn("authentication failed", str(ctx.exception).lower())
        self.assertEqual(engine.client.chat.completions.create.call_count, 1)

    @patch("time.sleep", return_value=None)
    def test_engine_transient_error_retried_and_succeeds(self, mock_sleep):
        """Engine retries once when receiving a transient capacity error and succeeds if attempt 2 passes."""
        valid_json = json.dumps({
            "patientName": "Retry Success Patient",
            "doctorName": "Dr. Test",
            "dateIssued": "24/10/2026",
            "diagnosis": "None",
            "medications": [{"name": "Aspirin", "strength": "100mg", "dosage": "1", "frequency": "Once daily", "duration": "5 days", "instructions": "", "confidence": 0.95}],
            "unreadable_fields": [],
            "needs_review": True
        })
        transient_error_resp = create_mock_completion(
            error={'message': 'ResourceExhausted: Worker local total request limit reached (16/16)', 'code': 502}
        )
        success_resp = create_mock_completion(content=valid_json, finish_reason="stop")

        engine = PrescriptionOCREngine()
        engine.provider = OpenRouterVisionProvider()
        engine.provider.api_key = "test_key"
        engine.client = MagicMock()
        engine.client.chat.completions.create.side_effect = [transient_error_resp, success_resp]

        result = engine.process_prescription(self.temp_img.name)
        self.assertEqual(engine.client.chat.completions.create.call_count, 2)
        self.assertEqual(result["patientName"], "Retry Success Patient")
        self.assertEqual(result["medications"][0]["name"], "Aspirin")
        mock_sleep.assert_called_once_with(2.0)

    def test_gemini_provider_rate_limit(self):
        """Gemini vision provider maps 429 rate limit to HTTP 429."""
        engine = PrescriptionOCREngine()
        engine.provider = GeminiVisionProvider()
        engine.provider.api_key = "test_key"
        engine.client = MagicMock()
        engine.client.chat.completions.create.side_effect = Exception("429 Resource has been exhausted (e.g. check quota)")

        with self.assertRaises(PrescriptionOCRError) as ctx:
            engine.process_prescription(self.temp_img.name)
        self.assertEqual(ctx.exception.status_code, 429)
        self.assertIn("quota exceeded", str(ctx.exception).lower())



    def test_temp_file_cleanup_on_error(self):
        """Temporary files are cleaned up from disk even when processing raises an exception."""
        recorded_paths = []

        def side_effect(path):
            recorded_paths.append(path)
            self.assertTrue(os.path.exists(path), "Temp file should exist during processing")
            raise RuntimeError("Unexpected pipeline crash")

        with patch.object(PrescriptionOCREngine, "process_prescription", side_effect=side_effect):
            data = {'image': (io.BytesIO(self.test_img_bytes), 'rx.png')}
            res = self.client.post('/extract', data=data, content_type='multipart/form-data')
            self.assertEqual(res.status_code, 500)
            self.assertEqual(len(recorded_paths), 1)
            # Verify file was cleaned up in finally block
            self.assertFalse(
                os.path.exists(recorded_paths[0]),
                "Temp file should be deleted after exception"
            )

if __name__ == '__main__':
    unittest.main()
