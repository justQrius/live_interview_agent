"""
Tests for context management components.
"""

import unittest
from unittest.mock import MagicMock, patch
import base64
import os

from src.context.chunker import Chunker
from src.context.manager import ContextManager
from src.context.parsers import TextParser, get_parser_for_file, PDFParser, DocxParser

class TestChunker(unittest.TestCase):
    def test_chunk_text_simple(self):
        chunker = Chunker(chunk_size=10, chunk_overlap=0)
        text = "123456789012345"
        chunks = chunker.chunk_text(text)
        
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].text, "1234567890")
        self.assertEqual(chunks[1].text, "12345")

    def test_chunk_text_overlap(self):
        chunker = Chunker(chunk_size=10, chunk_overlap=5)
        text = "123456789012345"
        # Chunk 1: 0-10 -> "1234567890"
        # Start 2: 5
        # Chunk 2: 5-15 -> "6789012345"
        
        chunks = chunker.chunk_text(text)
        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0].text, "1234567890")
        self.assertEqual(chunks[1].text, "6789012345")
        
    def test_chunk_newline_handling(self):
        # Should break at newline if possible
        chunker = Chunker(chunk_size=20, chunk_overlap=0)
        text = "Hello world.\nThis is a test."
        # Length is ~27
        # Chunk size 20.
        # Without newline logic: "Hello world.\nThis is"
        # With newline logic: "Hello world.\n"
        
        chunks = chunker.chunk_text(text)
        self.assertEqual(chunks[0].text, "Hello world.\n")
        self.assertEqual(chunks[1].text, "This is a test.")

class TestParsers(unittest.TestCase):
    def test_text_parser(self):
        parser = TextParser()
        content = b"Hello world"
        text = parser.parse(content, "test.txt")
        self.assertEqual(text, "Hello world")

    def test_get_parser(self):
        self.assertIsInstance(get_parser_for_file("test.pdf"), PDFParser)
        self.assertIsInstance(get_parser_for_file("test.docx"), DocxParser)
        self.assertIsInstance(get_parser_for_file("test.txt"), TextParser)
        self.assertIsInstance(get_parser_for_file("test.unknown"), TextParser)

class TestContextManager(unittest.IsolatedAsyncioTestCase):
    async def test_process_file_txt(self):
        manager = ContextManager()
        
        content = "Hello context world"
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        chunks_count = await manager.process_file("test.txt", content_b64)
        
        self.assertGreater(chunks_count, 0)
        self.assertEqual(len(manager.chunks), 1)
        self.assertEqual(manager.chunks[0].text, "Hello context world")
        self.assertEqual(manager.processed_files["test.txt"]["chunk_count"], 1)

    async def test_clear_context(self):
        manager = ContextManager()
        content = "test"
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        await manager.process_file("test.txt", content_b64)
        
        self.assertEqual(len(manager.chunks), 1)
        manager.clear_context()
        self.assertEqual(len(manager.chunks), 0)
        self.assertEqual(len(manager.processed_files), 0)

if __name__ == '__main__':
    unittest.main()
