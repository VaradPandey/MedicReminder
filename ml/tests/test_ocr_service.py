import io
import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock
from PIL import Image

# Ensure ml directory is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import test_server_pythonic as srv

class TestOcrService(unittest.TestCase):
    def setUp(self):
        self.app = srv.app
        self.client = self.app.test_client()

    def test_home_endpoint(self):
        """GET / returns 200 OK."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"Flask Pythonic Backend", res.data)

    def test_extract_missing_image(self):
        """POST /extract without image returns 400."""
        res = self.client.post('/extract', data={})
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("error", data)
        self.assertIn("image file is required", data["error"])

    def test_extract_unsupported_file_type(self):
        """POST /extract with non-image file returns 400."""
        data = {
            'image': (io.BytesIO(b"fake data"), 'test.exe')
        }
        res = self.client.post('/extract', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertIn("Unsupported file type", data["error"])

    @patch.dict(os.environ, {"GROQ_API_KEY": "", "MOCK_OCR": "false"})
    def test_extract_missing_groq_api_key(self):
        """POST /extract when GROQ_API_KEY is missing returns 500 with informative message."""
        buf = io.BytesIO()
        Image.new('RGB', (100, 100), color='white').save(buf, format='PNG')
        buf.seek(0)

        data = {'image': (buf, 'rx.png')}
        res = self.client.post('/extract', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 500)
        json_data = res.get_json()
        self.assertIn("GROQ_API_KEY is not configured", json_data["error"])

    @patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test_mock_key", "MOCK_OCR": "false"})
    @patch("test_server_pythonic.extract_text_from_image", return_value="")
    def test_extract_failed_ocr_no_text(self, mock_ocr):
        """When OCR fails to find readable text, returns 422 with clear message (no hallucination)."""
        buf = io.BytesIO()
        Image.new('RGB', (100, 100), color='white').save(buf, format='PNG')
        buf.seek(0)

        data = {'image': (buf, 'blank_rx.png')}
        res = self.client.post('/extract', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 422)
        json_data = res.get_json()
        self.assertIn("No readable text could be recognized", json_data["error"])

    @patch.dict(os.environ, {"MOCK_OCR": "true"})
    def test_extract_mock_ocr_mode(self):
        """When MOCK_OCR=true, returns 200 with structured mock prescription JSON."""
        buf = io.BytesIO()
        Image.new('RGB', (100, 100), color='white').save(buf, format='PNG')
        buf.seek(0)

        data = {'image': (buf, 'rx.png')}
        res = self.client.post('/extract', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertIn("result", json_data)
        parsed = json.loads(json_data["result"])
        self.assertEqual(parsed["patientName"], "Jane Doe")
        self.assertTrue(len(parsed["medications"]) > 0)

    @patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test_key", "MOCK_OCR": "false", "GROQ_MODEL": "openai/gpt-oss-20b"})
    @patch("test_server_pythonic.extract_text_from_image", return_value="Rx: Amoxicillin 500mg Twice daily for 7 days")
    @patch("test_server_pythonic.get_ai_client")
    def test_extract_mocked_groq_success(self, mock_get_client, mock_ocr):
        """When Groq returns valid completion, returns 200 with parsed prescription."""
        mock_choice = MagicMock()
        mock_choice.message.content = json.dumps({
            "patientName": "John Doe",
            "doctorName": "Dr. Smith",
            "dateIssued": "2026-10-24",
            "diagnosis": "Bacterial Infection",
            "medications": [
                {
                    "name": "Amoxicillin",
                    "dosage": "500mg",
                    "frequency": "Twice daily",
                    "duration": "7 days",
                    "instructions": "Take with water"
                }
            ]
        })
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]

        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create.return_value = mock_completion
        mock_get_client.return_value = mock_client_instance

        buf = io.BytesIO()
        Image.new('RGB', (100, 100), color='white').save(buf, format='PNG')
        buf.seek(0)

        data = {'image': (buf, 'rx.png')}
        res = self.client.post('/extract', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 200)
        json_data = res.get_json()
        self.assertIn("result", json_data)
        parsed = json.loads(json_data["result"])
        self.assertEqual(parsed["medications"][0]["name"], "Amoxicillin")

    @patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test_key", "MOCK_OCR": "false", "GROQ_MODEL": "openai/gpt-oss-20b"})
    @patch("test_server_pythonic.extract_text_from_image", return_value="Rx: Paracetamol 650mg")
    @patch("test_server_pythonic.get_ai_client")
    def test_extract_groq_provider_error(self, mock_get_client, mock_ocr):
        """When Groq provider raises an exception, returns 502 Bad Gateway without leaking secrets."""
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create.side_effect = Exception("Rate limit exceeded (TPM)")
        mock_get_client.return_value = mock_client_instance

        buf = io.BytesIO()
        Image.new('RGB', (100, 100), color='white').save(buf, format='PNG')
        buf.seek(0)

        data = {'image': (buf, 'rx.png')}
        res = self.client.post('/extract', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 502)
        json_data = res.get_json()
        self.assertIn("Groq AI provider error", json_data["error"])

    @patch.dict(os.environ, {"GROQ_API_KEY": "gsk_test_key", "MOCK_OCR": "false", "GROQ_MODEL": "openai/gpt-oss-20b"})
    @patch("test_server_pythonic.extract_text_from_image", return_value="Rx: Ibuprofen 400mg")
    @patch("test_server_pythonic.get_ai_client")
    def test_extract_groq_empty_response(self, mock_get_client, mock_ocr):
        """When Groq provider returns empty choices, returns 502 Bad Gateway."""
        mock_completion = MagicMock()
        mock_completion.choices = []
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create.return_value = mock_completion
        mock_get_client.return_value = mock_client_instance

        buf = io.BytesIO()
        Image.new('RGB', (100, 100), color='white').save(buf, format='PNG')
        buf.seek(0)

        data = {'image': (buf, 'rx.png')}
        res = self.client.post('/extract', data=data, content_type='multipart/form-data')
        self.assertEqual(res.status_code, 502)
        json_data = res.get_json()
        self.assertIn("empty or invalid completion response", json_data["error"])

if __name__ == '__main__':
    unittest.main()
