import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret-please-change-32-bytes")
os.environ.setdefault("ALLOW_DEV_FALLBACK", "0")

mock_supabase_mod = MagicMock()
mock_supabase_mod.create_client.return_value = MagicMock()
sys.modules["supabase"] = mock_supabase_mod

sys.modules.setdefault("fitz", MagicMock())
sys.modules.setdefault("numpy", MagicMock())

mock_pil_mod = MagicMock()
mock_image_mod = MagicMock()
mock_pil_mod.Image = mock_image_mod
sys.modules.setdefault("PIL", mock_pil_mod)
sys.modules.setdefault("PIL.Image", mock_image_mod)
