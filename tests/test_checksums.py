import hashlib
from pathlib import Path
import tempfile
import unittest

from src.firewatch.coverage_validation import sha256_file as coverage_sha256_file
from src.firewatch.data_pipeline import sha256_file as pipeline_sha256_file


class ChecksumTests(unittest.TestCase):
    def test_file_hash_helpers_match_sha256_with_their_existing_chunk_arguments(self):
        content = b"FIREWATCH source checksum test"
        expected = hashlib.sha256(content).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.bin"
            path.write_bytes(content)

            self.assertEqual(pipeline_sha256_file(path), expected)
            self.assertEqual(pipeline_sha256_file(path, chunk_size=3), expected)
            self.assertEqual(coverage_sha256_file(path), expected)
            self.assertEqual(coverage_sha256_file(str(path), chunk_bytes=5), expected)


if __name__ == "__main__":
    unittest.main()
