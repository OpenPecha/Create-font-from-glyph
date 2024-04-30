from fontTools.ttLib.tables import _g_l_y_f
from fontTools.ttLib.tables._g_l_y_f import Glyph as TTGlyph
from fontTools.pens.basePen import BasePen
from xml.etree import ElementTree as ET
from svg.path import parse_path
import os
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.feaLib.builder import addOpenTypeFeatures
from fontTools.ttLib.tables._n_a_m_e import NameRecord
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables._g_l_y_f import Glyph


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


def parse_svg_to_glyph(svg_file_path, desired_headline):
    filename = os.path.splitext(os.path.basename(svg_file_path))[0]
    codepoints = extract_codepoints(filename)
    glyph_name = generate_glyph_name(codepoints)

    tree = ET.parse(svg_file_path)
    root = tree.getroot()

    glyph = TTGlyph()
    glyph.unicodes = codepoints or []

    pen = SVGPen(None)
    ttPen = TTGlyphPen()

    min_x, min_y, max_x, max_y = float('inf'), float('inf'), float('-inf'), float('-inf')

    for element in root.iter('{http://www.w3.org/2000/svg}path'):
        path_data = element.attrib.get('d', '')
        pen.pathFromSVGPathData(path_data)
        bbox = pen.get_bbox()
        pen.reset()

        if bbox:
            min_x = min(min_x, bbox[0])
            min_y = min(min_y, bbox[1])
            max_x = max(max_x, bbox[2])
            max_y = max(max_y, bbox[3])

    vertical_translation = desired_headline - max_y

    for element in root.iter('{http://www.w3.org/2000/svg}path'):
        path_data = element.attrib.get('d', '')
        pen.pathFromSVGPathData(path_data)

        transformPen = TransformPen(ttPen, (1.0, 0, 0, 1.0, 0, vertical_translation + 2000))

        for command in pen.get_path():
            if command[0] == 'moveTo':
                transformPen.moveTo(command[1])
            elif command[0] == 'lineTo':
                transformPen.lineTo(command[1])
            elif command[0] == 'curveTo':
                transformPen.curveTo(*command[1])
            elif command[0] == 'closePath':
                transformPen.closePath()

        pen.reset()

    glyph = ttPen.glyph()

    # print(f"File Name: {filename}")
    # print(f"Glyph Name: {glyph_name}")
    # print(f"Unicodes: {codepoints}")

    return glyph, glyph_name, codepoints



def create_font_from_glyphs(glyph_data, output_path):
    font = TTFont()

    # Initialize necessary tables
    font['head'] = newTable('head')
    font['head'].unitsPerEm = 1000

    font['hhea'] = newTable('hhea')
    font['hhea'].ascent = 900
    font['hhea'].descent = -100

    font['maxp'] = newTable('maxp')
    font['maxp'].numGlyphs = len(glyph_data) + 1  

    # Prepare the glyf 
    font['glyf'] = newTable('glyf')

    # Add glyphs to the glyf table
    for glyph, glyph_name, _ in glyph_data:
        font['glyf'][glyph_name] = glyph

    # Initialize cmap table
    cmap = newTable('cmap')
    cmap.tableVersion = 0
    cmap.tables = []
    subtable = CmapSubtable.newSubtable(4)
    subtable.platformID = 3
    subtable.platEncID = 1
    subtable.language = 0
    subtable.cmap = {unicode: glyph_name for _, glyph_name, unicodes in glyph_data for unicode in unicodes}
    cmap.tables.append(subtable)
    font['cmap'] = cmap

    # Name table
    font_name = "Example Font"
    name = newTable('name')
    name.names = []  
    nameRecord = NameRecord()
    nameRecord.nameID = 1
    nameRecord.platformID = 3
    nameRecord.platEncID = 1
    nameRecord.langID = 0x409
    nameRecord.string = font_name.encode('utf-16-be')
    name.names.append(nameRecord)
    font['name'] = name

    # Post table
    font['post'] = newTable('post')
    font['post'].italicAngle = 0
    font['post'].underlinePosition = -100
    font['post'].underlineThickness = 50
    font['post'].isFixedPitch = 0

    # Save the font
    font.save(output_path)


def main():
    svg_dir_path = "../../data/derge_font/svg"
    desired_headline = 2000 

    glyph_data = []
    for filename in os.listdir(svg_dir_path):
        if filename.endswith('.svg'):
            svg_file_path = os.path.join(svg_dir_path, filename)
            glyph, glyph_name, codepoints = parse_svg_to_glyph(svg_file_path, desired_headline)
            glyph_data.append((glyph, glyph_name, codepoints))

    create_font_from_glyphs(glyph_data, "../../data/derge_font/ttf/derge.ttf")

if __name__ == "__main__":
    main()
