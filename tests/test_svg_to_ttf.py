import unittest
import os
import shutil
from fontTools.ttLib import TTFont
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from create_font_from_glyph.svg_to_ttf import extract_codepoints, generate_glyph_name, parse_svg_to_glyph, process_glyphs, set_font_metadata

class TestFontTools(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.test_svg_dir = 'test_svgs'
        cls.test_svg_path = os.path.join(cls.test_svg_dir, 'test_glyph.svg')
        cls.test_font_path = 'sambhotaUnicodeBaseShip.ttf'  # Ensure this path is correct
        cls.new_font_path = 'test_font.ttf'
        cls.reduction_excluded_glyphs = {'uni0F72', 'uni0F7C', 'uni0F7A'}
        
        # Create a temporary directory for test SVG files
        if not os.path.exists(cls.test_svg_dir):
            os.makedirs(cls.test_svg_dir)
        
        # Create a simple SVG file
        with open(cls.test_svg_path, 'w') as f:
            f.write('<svg xmlns="http://www.w3.org/2000/svg">'
                    '<path d="M10 10 H 90 V 90 H 10 Z" /></svg>')

        # Ensure the test font file exists
        if not os.path.exists(cls.test_font_path):
            shutil.copy('sambhotaUnicodeBaseShip.ttf', cls.test_font_path)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.test_svg_dir)
        if os.path.exists(cls.test_font_path):
            os.remove(cls.test_font_path)
        if os.path.exists(cls.new_font_path):
            os.remove(cls.new_font_path)

    def test_extract_codepoints(self):
        filename = 'ཀ_01.svg'
        expected_codepoints = [0x0F40]
        codepoints = extract_codepoints(filename)
        self.assertEqual(codepoints, expected_codepoints)

    def test_generate_glyph_name(self):
        codepoints = [0x0F40]
        expected_glyph_name = 'uni0F40'
        glyph_name = generate_glyph_name(codepoints)
        self.assertEqual(glyph_name, expected_glyph_name)

    def test_parse_svg_to_glyph(self):
        desired_headline = -2000
        glyph, glyph_name = parse_svg_to_glyph(self.test_svg_path, desired_headline)
        print(f"Glyph Name: {glyph_name}")  # Debugging output
        self.assertIsNotNone(glyph)
        self.assertEqual(glyph_name, 'uni0F40')

    def test_process_glyphs(self):
        font = TTFont(self.test_font_path)
        glyph_count = process_glyphs(self.test_svg_dir, font, self.reduction_excluded_glyphs)
        print(f"Glyph Count: {glyph_count}")  # Debugging output
        self.assertGreater(glyph_count, 0)

    def test_set_font_metadata(self):
        font = TTFont(self.test_font_path)
        font_name = "TestFont"
        family_name = "TestFamily"
        set_font_metadata(font, font_name, family_name)
        name_table = font['name']
        
        # Debugging output
        name_entries = {entry.nameID: entry.toUnicode() for entry in name_table.names}
        print(f"Name Table Entries: {name_entries}")

        self.assertEqual(name_table.getName(4, 3, 1, 0).toUnicode(), font_name)
        self.assertEqual(name_table.getName(1, 3, 1, 0).toUnicode(), family_name)

if __name__ == '__main__':
    unittest.main()
