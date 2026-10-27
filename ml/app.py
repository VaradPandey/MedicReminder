"""
Flask entrypoint alias for MedicReminder Prescription OCR service.
"""
import os
from test_server_pythonic import app

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
