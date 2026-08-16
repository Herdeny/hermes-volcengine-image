"""Mock tests for the Volcengine Ark Seedream provider."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


HERMES_REPO = Path.home() / ".hermes" / "hermes-agent"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERMES_REPO))
sys.path.insert(0, str(PROJECT_ROOT / "plugins"))

from image_gen.volcengine import (  # noqa: E402
    API_URL,
    DEFAULT_MODEL,
    VolcengineImageGenProvider,
)


class VolcengineImageGenProviderTest(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = VolcengineImageGenProvider()

    @patch("image_gen.volcengine.get_secret", return_value="test-key")
    @patch("image_gen.volcengine.save_url_image")
    @patch("image_gen.volcengine.requests.post")
    def test_success_url_is_saved_locally(
        self,
        post: Mock,
        save_url_image: Mock,
        _get_secret: Mock,
    ) -> None:
        response = Mock(status_code=200, text="")
        response.json.return_value = {"data": [{"url": "https://example.test/image.png"}]}
        post.return_value = response

        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "generated.png"
            image_path.write_bytes(b"mock image")
            save_url_image.return_value = image_path

            result = self.provider.generate("一只戴眼镜的橘猫程序员", "square")

            self.assertTrue(Path(result["image"]).is_file())

        self.assertTrue(result["success"])
        self.assertEqual(result["image"], str(image_path))
        self.assertEqual(result["model"], DEFAULT_MODEL)
        self.assertEqual(result["aspect_ratio"], "square")
        post.assert_called_once_with(
            API_URL,
            headers={
                "Authorization": "Bearer test-key",
                "Content-Type": "application/json",
            },
            json={
                "model": DEFAULT_MODEL,
                "prompt": "一只戴眼镜的橘猫程序员",
                "size": "2048x2048",
                "watermark": False,
            },
            timeout=120,
        )
        save_url_image.assert_called_once_with(
            "https://example.test/image.png",
            prefix=f"volcengine_{DEFAULT_MODEL}",
        )

    @patch("image_gen.volcengine.get_secret", return_value="bad-key")
    @patch("image_gen.volcengine.requests.post")
    def test_401_returns_auth_error(self, post: Mock, _get_secret: Mock) -> None:
        post.return_value = Mock(status_code=401, text="Unauthorized")

        result = self.provider.generate("test", "landscape")

        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "无效的 ARK_API_KEY")
        self.assertEqual(result["error_type"], "auth_error")

    @patch("image_gen.volcengine.get_secret", return_value="test-key")
    @patch("image_gen.volcengine.requests.post")
    def test_network_exception_returns_network_error(
        self,
        post: Mock,
        _get_secret: Mock,
    ) -> None:
        import requests

        post.side_effect = requests.ConnectionError("connection failed")

        result = self.provider.generate("test", "portrait")

        self.assertFalse(result["success"])
        self.assertEqual(result["error_type"], "network_error")
        self.assertEqual(result["aspect_ratio"], "portrait")


if __name__ == "__main__":
    unittest.main()
