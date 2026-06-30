import unittest
from unittest.mock import Mock, patch

from bridge.app.media import image_cache


class FakeStdin:
    def __init__(self):
        self.data = b""
        self.closed = False

    def write(self, data):
        self.data += data

    def close(self):
        self.closed = True


class FakeProcess:
    def __init__(self):
        self.stdin = FakeStdin()
        self.killed = False

    def communicate(self, input=None):
        raise AssertionError("_spawn_downloader must not wait with communicate")

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        return 0


class ImageCacheDownloaderTest(unittest.TestCase):
    def test_spawn_downloader_writes_tasks_without_waiting_for_download_completion(self):
        process = FakeProcess()
        thread_instance = Mock()
        tasks = [{"url": "https://example.test/a.jpg", "path": "/tmp/a.jpg"}]

        with patch.object(image_cache.subprocess, "Popen", return_value=process) as popen:
            with patch.object(image_cache.threading, "Thread", return_value=thread_instance) as thread:
                image_cache._spawn_downloader(tasks)

        popen.assert_called_once()
        self.assertIn(b"https://example.test/a.jpg", process.stdin.data)
        self.assertTrue(process.stdin.closed)
        self.assertFalse(process.killed)
        thread.assert_called_once_with(
            target=image_cache._wait_for_downloader,
            args=(process,),
            daemon=True,
        )
        thread_instance.start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
