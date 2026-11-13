"""
Automated Unit Tests for Qnote Core Modules
"""
import unittest
import tempfile
import os
import shutil
from pathlib import Path
from qnote.storage import NoteStorage
from qnote.themes import THEMES, get_theme
from qnote.ink import InkEngine, InkStroke

class TestQnoteStorage(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_qnote.db"
        self.storage = NoteStorage(db_path=self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_and_fetch_note(self):
        note = self.storage.get_or_create_current_note(default_theme_id=2)
        self.assertIsNotNone(note)
        self.assertEqual(note["theme_id"], 2)
        self.assertEqual(note["text_content"], "")
        
        # Save updates
        self.storage.save_note(
            note["id"],
            text_content="今日速记：极简设计思维",
            strokes=[{"color": "#18181c", "pts": [[10, 10, 2.0], [20, 25, 2.5]]}],
            theme_id=3
        )
        
        updated = self.storage.get_note_by_id(note["id"])
        self.assertEqual(updated["text_content"], "今日速记：极简设计思维")
        self.assertEqual(updated["theme_id"], 3)
        self.assertIn("18181c", updated["strokes_data"])

    def test_new_sheet_and_pagination(self):
        id1 = self.storage.create_new_note(theme_id=0)
        self.storage.save_note(id1, "Page 1", [], 0)
        
        id2 = self.storage.create_new_note(theme_id=1)
        self.storage.save_note(id2, "Page 2", [], 1)
        
        self.assertEqual(self.storage.get_total_count(), 2)
        
        prev_id = self.storage.get_adjacent_note_id(id2, "prev")
        self.assertEqual(prev_id, id1)
        
        next_id = self.storage.get_adjacent_note_id(id1, "next")
        self.assertEqual(next_id, id2)

class TestQnoteThemes(unittest.TestCase):
    def test_ten_themes_exist(self):
        self.assertEqual(len(THEMES), 10)
        for i, theme in enumerate(THEMES):
            self.assertEqual(theme.id, i)
            self.assertTrue(len(theme.name) > 0)
            self.assertTrue(len(theme.desc) > 0)
            self.assertTrue(theme.bg_color.isValid())
            self.assertTrue(theme.ink_color.isValid())
            self.assertTrue(theme.text_color.isValid())

class TestQnoteInk(unittest.TestCase):
    def test_smooth_bezier_and_jitter_filter(self):
        engine = InkEngine()
        engine.start_stroke(10.0, 10.0, "#18181c")
        
        # Micro tremor point (distance < 2.0) should be discarded by jitter filter
        rect_jitter = engine.continue_stroke(10.5, 10.5)
        self.assertIsNone(rect_jitter)
        
        # Valid moving points
        rect1 = engine.continue_stroke(30.0, 40.0)
        self.assertIsNotNone(rect1)
        
        rect2 = engine.continue_stroke(60.0, 70.0)
        self.assertIsNotNone(rect2)
        
        engine.end_stroke()
        self.assertEqual(len(engine.strokes), 1)
        
        # Export and restore
        exported = engine.export_data()
        self.assertTrue(len(exported) == 1)
        self.assertEqual(exported[0]["color"], "#18181c")
        
        new_engine = InkEngine()
        new_engine.load_data(exported)
        self.assertEqual(len(new_engine.strokes), 1)
        self.assertEqual(len(new_engine.strokes[0].points), len(engine.strokes[0].points))
        
        # Undo / Redo
        self.assertTrue(new_engine.undo())
        self.assertEqual(len(new_engine.strokes), 0)
        self.assertTrue(new_engine.redo())
        self.assertEqual(len(new_engine.strokes), 1)

if __name__ == "__main__":
    unittest.main()
