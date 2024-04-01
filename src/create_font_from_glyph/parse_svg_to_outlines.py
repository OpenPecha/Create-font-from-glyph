from fontTools.pens.ttGlyphPen import TTGlyphPen
import imp
from fontTools.ttLib.tables._g_l_y_f import Glyph
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph as TTGlyph
from fontTools.pens.basePen import BasePen
from xml.etree import ElementTree as ET
from svg.path import parse_path
from xml.dom.minidom import parse
import os
from pathlib import Path


def extract_codepoints(filename):
    tibetan_char = filename.split('_')[0]
    codepoints = [ord(char) for char in tibetan_char]
    return codepoints


def generate_glyph_name(codepoints):
    glyph_name = 'uni' + ''.join(f"{codepoint:04X}" for codepoint in codepoints)
    return glyph_name


class SVGPen(BasePen):
    def __init__(self, glyphSet):
        super().__init__(glyphSet)
        self.currentPoint = (0, 0)
        self.path = []

    def _moveTo(self, pt):
        self.currentPoint = pt
        self.path.append(('moveTo', pt))

    def _lineTo(self, pt):
        self.currentPoint = pt
        self.path.append(('lineTo', pt))

    def _curveToOne(self, pt1, pt2, pt3):
        self.currentPoint = pt3
        self.path.append(('curveTo', pt1, pt2, pt3))

    def get_path(self):
        return self.path


def calculate_bounding_box_of_svg(svg_file_path):
    doc = parse(svg_file_path)
    path_strings = [path.getAttribute('d') for path in doc.getElementsByTagName('path')]
    all_coords = []
    for path_string in path_strings:
        path_data = parse_path(path_string)
        for segment in path_data:
            all_coords.append(segment.start)
            all_coords.append(segment.end)
    xMin, xMax = min(coord.real for coord in all_coords), max(coord.real for coord in all_coords)
    yMin, yMax = min(coord.imag for coord in all_coords), max(coord.imag for coord in all_coords)
    return xMin, xMax, yMin, yMax


def parse_svg_to_glyph(svg_file_path, glyph_name=None, unicode=None, glyph_set=None, advance_width=0, lsb=0, rsb=0, xMin=0, xMax=0, yMin=0, yMax=0):
    tree = ET.parse(svg_file_path)
    root = tree.getroot()
    width_str = root.attrib.get('width', '0')
    height_str = root.attrib.get('height', '0')

    width_str = width_str.replace('pt', '').strip()
    height_str = height_str.replace('pt', '').strip()

    try:
        width = float(width_str)
        height = float(height_str)
    except ValueError:
        print(f"error in heigth or width '{svg_file_path}'.")
        return None

    glyph = TTGlyph()
    glyph.name = glyph_name
    glyph.unicodes = unicode or []
    glyph.width = advance_width
    glyph.lsb = lsb
    glyph.rsb = rsb

    pen = SVGPen(None)
    for child in root:
        if child.tag == '{http://www.w3.org/2000/svg}path':
            path_data = child.attrib.get('d', '')
            pen.path = []
            pen.reset()
            glyph.addComponent(glyphName=glyph_name, transformation=(1, 0, 0, 1, 0, 0))
            pen._glyphSet = glyph
            pen.path = []
            pen.reset()
            pen.moveTo((0, 0))
            pen.pathFromSVGPathData(path_data)
            glyph.draw(pen)

    return glyph


def create_glyphs(directory_path, width=0, height=0, glyph_set=None):
    glyph_objects = []
    for filename in os.listdir(directory_path):
        if filename.endswith('.svg'):
            svg_file_path = os.path.join(directory_path, filename)
            codepoints = extract_codepoints(filename)
            glyph_name = generate_glyph_name(codepoints)
            xMin, xMax, yMin, yMax = calculate_bounding_box_of_svg(svg_file_path)
            advance_width = xMax - xMin
            lsb = xMin
            rsb = advance_width - (width + lsb)
            glyph = parse_svg_to_glyph(svg_file_path, glyph_name, codepoints,
                                       advance_width, lsb, rsb, xMin, xMax, yMin, yMax)
            glyph.glyph_name = glyph_name
            glyph.advance_width = advance_width
            glyph.codepoints = codepoints or []
            glyph.lsb = lsb
            glyph.rsb = rsb

            glyph_objects.append(glyph)
            print("Glyph created with the following attributes:")
            print("Glyph Name:", glyph_name)
            print("Unicodes:", codepoints)
            print("Glyph Set:", glyph_set)
            print("Advance Width:", advance_width)
            print("Left Side Bearing:", lsb)
            print("Right Side Bearing:", rsb)
            print("xMin:", xMin)
            print("xMax:", xMax)
            print("yMin:", yMin)
            print("yMax:", yMax)

    return glyph_objects


def replace_glyphs_in_font(font_path, new_glyphs):
    font = TTFont(font_path)
    glyfTable = font["glyf"]

    for glyph in new_glyphs:
        pen = TTGlyphPen(glyfTable)
        glyph.draw(pen, glyfTable) 
        new_glyph = pen.glyph()


        font['glyf'][glyph.glyph_name] = new_glyph
        font['hmtx'][glyph.glyph_name] = (glyph.advance_width, glyph.lsb)

        for table in font['cmap'].tables:
            for codepoint in glyph.codepoints:
                table.cmap[codepoint] = glyph.glyph_name

    font.save('../../data/derge_font/ttf/Derge.ttf')



def main():
    directory_path = '../../data/derge_font/svg'
    new_glyphs = create_glyphs(directory_path)
    replace_glyphs_in_font('../../data/base_font/sambhotaUnicodeBaseShip.ttf', new_glyphs)


if __name__ == "__main__":
    main()
