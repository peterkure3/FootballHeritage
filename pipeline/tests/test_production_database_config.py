import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlparse


def load_config(filename):
    spec = importlib.util.spec_from_file_location("isolated_production_config", Path(__file__).resolve().parents[1] / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.DATABASE_URI


class ProductionDatabaseConfigTests(unittest.TestCase):
    def test_hosted_urls_keep_tls_options_and_separate_database_credentials(self):
        pipeline = "postgresql://pipeline:example@pipeline.example/pipeline?sslmode=verify-full"
        heritage = "postgresql://readonly:example@heritage.example/heritage?sslmode=require"
        with patch.dict(os.environ, {"DATABASE_URL": pipeline, "HERITAGE_DATABASE_URL": heritage}):
            self.assertEqual(load_config("config.py"), pipeline)
            self.assertEqual(load_config("heritage_config.py"), heritage)

    def test_special_password_characters_do_not_change_the_database_host(self):
        password = "test@password:/?#%"
        with patch.dict(os.environ, {"DATABASE_URL": "", "HERITAGE_DATABASE_URL": "", "DB_USER": "test-user", "DB_PASSWORD": password, "DB_HOST": "database.example", "DB_PORT": "5432"}):
            for filename in ("config.py", "heritage_config.py"):
                with self.subTest(filename=filename):
                    uri = urlparse(load_config(filename))
                    self.assertEqual(uri.hostname, "database.example")
                    self.assertEqual(unquote(uri.password), password)


if __name__ == "__main__":
    unittest.main()
