from fontTools.ttLib.tables._g_l_y_f import Glyph as TTGlyph
from fontTools.pens.basePen import BasePen
from xml.etree import ElementTree as ET
from svg.path import parse_path
import os
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.feaLib.builder import addOpenTypeFeatures
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables._c_m_a_p import cmap_format_4
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.cu2quPen import Cu2QuPen
from fontTools.ttLib.tables._n_a_m_e import makeName
from fontTools.ttLib.tables._n_a_m_e import table__n_a_m_e


def extract_codepoints(filename):
    tibetan_char = filename.split('_')[0]
    codepoints = [ord(char) for char in tibetan_char]
    return codepoints


def generate_glyph_name(codepoints):
    glyph_name = 'uni' + ''.join(f"{codepoint:04X}" for codepoint in codepoints)
    return glyph_name


class SVGPen(BasePen):
    def __init__(self, glyphSet=None):
        super().__init__(glyphSet)
        self.currentPoint = (0, 0)
        self.path = []

    def _moveTo(self, pt):
        if self.path and self.path[-1][0] != 'closePath':
            self.closePath()
        self.currentPoint = pt
        self.path.append(('moveTo', pt))

    def _lineTo(self, pt):
        self.currentPoint = pt
        self.path.append(('lineTo', pt))

    def _curveToOne(self, pt1, pt2, pt3):
        self.currentPoint = pt3
        self.path.append(('curveTo', (pt1, pt2, pt3)))

    def get_path(self):
        if self.path and self.path[-1][0] != 'closePath':
            self.closePath()
        return self.path

    def reset(self):
        self.currentPoint = (0, 0)
        self.path = []

    def closePath(self):
        self.path.append(('closePath',))

    def pathFromSVGPathData(self, path_data):
        path = parse_path(path_data)
        for segment in path:
            if segment.__class__.__name__ == 'Line':
                self._lineTo((segment.end.real, segment.end.imag))
            elif segment.__class__.__name__ == 'CubicBezier':
                self._curveToOne((segment.control1.real, segment.control1.imag),
                                 (segment.control2.real, segment.control2.imag),
                                 (segment.end.real, segment.end.imag))
            elif segment.__class__.__name__ == 'Move':
                self._moveTo((segment.end.real, segment.end.imag))
        if self.path and self.path[-1][0] != 'closePath':
            self.closePath()

    def get_bbox(self):
        if not self.path:
            return None
        x_coords = []
        y_coords = []
        for pt in self.path:
            if pt[0] in ['moveTo', 'lineTo']:
                x_coords.append(pt[1][0])
                y_coords.append(pt[1][1])
            elif pt[0] == 'curveTo':
                for point in pt[1]:
                    x_coords.append(point[0])
                    y_coords.append(point[1])
        return min(x_coords), min(y_coords), max(x_coords), max(y_coords)

    def get_glyph(self):
        glyph = TTGlyph()
        pen = TTGlyphPen(glyph)
        cu2quPen = Cu2QuPen(pen, 0.0025)

        for command in self.get_path():
            if command[0] == 'moveTo':
                cu2quPen.moveTo(command[1])
            elif command[0] == 'lineTo':
                cu2quPen.lineTo(command[1])
            elif command[0] == 'curveTo':
                cu2quPen.curveTo(*command[1])
            elif command[0] == 'closePath':
                cu2quPen.closePath()

        return glyph


def parse_svg_to_glyph(svg_file_path):
    os.path.splitext(os.path.basename(svg_file_path))[0]
    tree = ET.parse(svg_file_path)
    root = tree.getroot()

    pen = SVGPen(None)

    for element in root.iter('{http://www.w3.org/2000/svg}path'):
        path_data = element.attrib.get('d', '')
        pen.pathFromSVGPathData(path_data)

    glyph = pen.get_glyph()

    return glyph


def create_notdef_glyph():
    glyph = TTGlyph()
    glyph.glyphName = ".notdef"
    glyph.width = 600
    return glyph

def setupNameTable(fb):
    name_table = table__n_a_m_e()
    name_table.names = []

    names = [
        (1, "Font Family", "DergeScratch"),
        (2, "Font Subfamily", "Regular"),
        (4, "Full Font Name", "DergeScratch Regular"),
        (6, "PostScript Name", "DergeScratch-Regular")
    ]
    for nameID, name, string in names:
        name_record = makeName(string, nameID, 3, 1, 0x0409)
        name_table.names.append(name_record)

    fb.font['name'] = name_table

def setupPostTable(fb):
    fb.setupPost()

def setupHeadTable(fb):
    fb.setupHead()

def setupMaxpTable(fb):
    fb.setupMaxp()


def create_font(glyphs_data, new_font_path):
    fb = FontBuilder(unitsPerEm=1000, isTTF=True)
    glyph_names = [".notdef"] + [data[2] for data in glyphs_data]
    fb.setupGlyphOrder(glyph_names)
    char_map = {0xE000: ".notdef"}
    for _, codepoints, glyph_name in glyphs_data:
        for codepoint in codepoints:
            char_map[codepoint] = glyph_name
    fb.setupCharacterMap(char_map)

    glyf_table = {'.notdef': create_notdef_glyph()}
    for glyph, _, glyph_name in glyphs_data:
        glyf_table[glyph_name] = glyph
    fb.setupGlyf(glyf_table)

    hmtx = {".notdef": (600, 0)}
    for _, _, glyph_name in glyphs_data:
        hmtx[glyph_name] = (600, 0)
    fb.setupHorizontalMetrics(hmtx)
    fb.setupHorizontalHeader(ascent=800, descent=200)
    fb.setupOS2()
    setupNameTable(fb)
    setupPostTable(fb)
    setupMaxpTable(fb)

    print(f"Font saved at {new_font_path}")
    fb.save(new_font_path)



def main():
    directory = "../../data/derge_font/svg"
    new_font_path = "../../data/derge_font/ttf/derge.ttf"
    glyphs_data = []

    for filename in os.listdir(directory):
        if filename.endswith(".svg"):
            print(f"Processing {filename}...")
            svg_file = os.path.join(directory, filename)
            glyph = parse_svg_to_glyph(svg_file)
            codepoints = extract_codepoints(filename)
            glyph_name = generate_glyph_name(codepoints)
            glyphs_data.append((glyph, codepoints, glyph_name))

    print(f"glyphs added: {len(glyphs_data)}")
    create_font(glyphs_data, new_font_path)


if __name__ == "__main__":
    main()
