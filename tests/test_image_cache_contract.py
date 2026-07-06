import unittest
from bridge.app.media import image_cache

class ImageCacheContractTest(unittest.TestCase):
    def test_normalize_image_tags_with_simple_tag(self):
        text = "A\n[Image: https://example.test/a.jpg]\nB"
        result = image_cache.normalize_image_tags(text)
        self.assertEqual(result, "A\n[Image: https://example.test/a.jpg]\nB")

    def test_normalize_image_tags_with_alt_tag(self):
        text = "前文 [Image: https://example.test/a.jpg | Alt: 示例] 后文"
        result = image_cache.normalize_image_tags(text)
        self.assertEqual(result, "前文 [Image: https://example.test/a.jpg | Alt: 示例] 后文")
        self.assertNotIn("Local", result)
        self.assertNotIn("Remote", result)
        self.assertNotIn("browser-bridge-cache", result)

    def test_normalize_image_tags_list_input(self):
        items = [{"text": "前文 [Image: https://example.test/a.jpg] 后文"}]
        result = image_cache.normalize_image_tags(items)
        self.assertIsInstance(result, list)
        self.assertEqual(result[0]["text"], "前文 [Image: https://example.test/a.jpg] 后文")

    def test_normalize_media_items_strips_local_path_and_preserves_meta(self):
        media_items = [
            {
                "type": "image",
                "url": "https://example.test/a.jpg",
                "localPath": "/tmp/old.jpg",
                "placement": "inline",
                "alt": "Alt text",
                "title": "Title text",
                "source": "Source info",
                "role": "cover"
            }
        ]
        result = image_cache.normalize_media_items(media_items)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        item = result[0]
        self.assertNotIn("localPath", item)
        self.assertEqual(item["type"], "image")
        self.assertEqual(item["url"], "https://example.test/a.jpg")
        self.assertEqual(item["order"], 1)
        self.assertEqual(item["placement"], "inline")
        self.assertEqual(item["alt"], "Alt text")
        self.assertEqual(item["title"], "Title text")
        self.assertEqual(item["source"], "Source info")
        self.assertEqual(item["role"], "cover")

if __name__ == "__main__":
    unittest.main()
