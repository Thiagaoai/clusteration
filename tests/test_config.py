import unittest

from app.core.config import SOURCE_BUILD_ID, Settings, effective_build_id


class BuildIdTests(unittest.TestCase):
    def test_effective_build_id_uses_source_when_env_is_unknown(self):
        settings = Settings(APP_BUILD_ID="unknown")

        self.assertEqual(effective_build_id(settings), SOURCE_BUILD_ID)

    def test_effective_build_id_uses_configured_value(self):
        settings = Settings(APP_BUILD_ID="deploy-123")

        self.assertEqual(effective_build_id(settings), "deploy-123")


if __name__ == "__main__":
    unittest.main()
