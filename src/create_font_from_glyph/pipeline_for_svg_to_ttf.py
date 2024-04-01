from fontTools.ttLib.tables._g_l_y_f import Glyph as TTGlyph
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.svgLib import SVGPath
from fontTools.ufoLib.glifLib import Glyph
from fontTools.pens.basePen import BasePen
import os
from svg.path import parse_path
from xml.dom.minidom import parse
from fontTools.ttLib import TTFont

# determining the bounding box of svg


def calculate_bounding_box_of_svg(svg_file_path):
    doc = parse(svg_file_path)
    path_strings = [path.getAttribute('d') for path in doc.getElementsByTagName('path')]
    all_coords = []
    for path_string in path_strings:
        path_data = parse_path(path_string)
        for move in path_data:
            all_coords.append((move.start.real, move.start.imag))
            all_coords.append((move.end.real, move.end.imag))
    x_coords = [coord[0] for coord in all_coords]
    y_coords = [coord[1] for coord in all_coords]
    xMin, xMax = min(x_coords), max(x_coords)
    yMin, yMax = min(y_coords), max(y_coords)
    return xMin, xMax, yMin, yMax


# parsing the svg path to write glyph from the path

from fontTools.pens.basePen import BasePen

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
        control1 = (pt1[0], pt1[1])
        control2 = (pt2[0], pt2[1])
        end = (pt3[0], pt3[1])
        self.path.append(('curveTo', control1, control2, end))
        self.currentPoint = end

    def curveTo(self, *points):
        if len(points) == 3:
            self._curveToOne(*points)
        else:
            super().curveTo(*points)

    def get_path(self):
        return self.path


def parse_svg_to_glyph(svg_file_path, glyph_name=None, unicodes=None, glyph_set=None, advance_width=0, lsb=0, rsb=0, xMin=0, xMax=0, yMin=0, yMax=0):
    glyph = TTGlyph()
    glyph.glyphName = glyph_name
    glyph.unicodes = unicodes or []
    glyph.width = advance_width
    glyph.lsb = lsb
    glyph.rsb = rsb

    pen = TTGlyphPen(glyph)
    path = SVGPath(svg_file_path)
    path.draw(pen)
    xMin, xMax, yMin, yMax = calculate_bounding_box_of_svg(svg_file_path)
    glyph.drawPoints = lambda pen: pen.drawRect((xMin, yMin, xMax, yMax))

    return glyph


def extract_codepoints(filename):
    tibetan_char = filename.split('_')[0]
    codepoints = [ord(char) for char in tibetan_char]
    return codepoints


def generate_glyph_name(codepoints):
    glyph_name = 'uni' + ''.join(f"{codepoint:04X}" for codepoint in codepoints)
    return glyph_name


def create_glyph(directory_path, width=0, height=0, glyph_set=None):
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
            glyph = parse_svg_to_glyph(svg_file_path, glyph_name, codepoints, glyph_set,
                                       advance_width, lsb, rsb, xMin, xMax, yMin, yMax)
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


def replace_glyphs(font, glyphs):
    for glyph in glyphs:
        if glyph.glyphName in font.getGlyphOrder():
            font['glyf'][glyph.glyphName] = glyph


def modify_font_name(font, new_name):
    name_table = font['name']
    for name in name_table.names:
        print(f"old name ID {name.nameID}: {name.toUnicode()}")
    for name in name_table.names:
        if name.nameID == 1:
            del name_table.names[name_table.names.index(name)]
    name_table.setName(new_name, 4, 3, 1, 0x409)
    name_table.setName(new_name, 1, 3, 1, 0x409)
    postscript_name = new_name.replace(' ', '')
    name_table.setName(postscript_name, 6, 3, 1, 0x409)

    for name in name_table.names:
        print(f"new name ID {name.nameID}: {name.toUnicode()}")




def main():
    directory_path = "../../data/derge_font/svg"
    glyphs = create_glyph(directory_path)
    font_path = '../../data/base_font/sambhotaUnicodeBaseShip.ttf'
    font = TTFont(font_path)
    replace_glyphs(font, glyphs)
    modify_font_name(font, 'Derge')
    font.save('../../data/derge_font/ttf/Derge.ttf')


if __name__ == "__main__":
    main()
