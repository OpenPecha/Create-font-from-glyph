from fontTools.ttLib.tables._g_l_y_f import Glyph as TTGlyph
from fontTools.pens.basePen import BasePen
from xml.etree import ElementTree as ET
from svg.path import parse_path
import os
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables._c_m_a_p import cmap_format_4
from convert_px_to_fontunit import create_font_units
from fontTools.ttLib.tables.otTables import Lookup, Ligature, LigatureSubst
from fontTools.ttLib.tables import otTables


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


def parse_svg_to_glyph(svg_file_path):
    filename = os.path.splitext(os.path.basename(svg_file_path))[0]
    codepoints = extract_codepoints(filename)
    glyph_name = generate_glyph_name(codepoints)
    desired_headline = -1900

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

        transformPen = TransformPen(ttPen, (1.0, 0, 0, 1.0, 0, vertical_translation + 2700))

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

    return glyph, codepoints, glyph_name


def add_glyphs_to_font(font_path, glyphs_data, new_font_path, svg_directory):
    font = TTFont(font_path)
    
    for table_name in ['cmap', 'head', 'hhea', 'maxp', 'post', 'OS/2', 'name', 'glyf', 'hmtx']:
        if table_name not in font:
            font[table_name] = newTable(table_name)

    font['name'].setName('DergeVariant1.0', 4, 3, 1, 0x409)  
    font['name'].setName('1.0', 5, 3, 1, 0x409) 
    font['name'].setName('DergeVariant1.0', 1, 3, 1, 0x409)
    font['name'].setName('MonlamAI', 9, 3, 1, 0x409)
    font['name'].setName('MonlamAI', 0, 3, 1, 0x409) 

    font['cmap'].tableVersion = 0
    font['cmap'].tables = []
    cmap_subtable = cmap_format_4(4)
    cmap_subtable.platformID = 3
    cmap_subtable.platEncID = 1
    cmap_subtable.language = 0
    cmap_subtable.cmap = {}
    all_glyph_units = create_font_units(svg_directory)

    glyph_count = {}

    for (glyph, codepoints, glyph_name), (glyph_width, lsb, rsb) in zip(glyphs_data, all_glyph_units):
        original_glyph_name = glyph_name
        if glyph_name not in glyph_count:
            glyph_count[glyph_name] = 0
        else:
            glyph_count[glyph_name] += 1
            glyph_name = f"{glyph_name}.calt{glyph_count[glyph_name]}"

        if 'glyf' in font:
            font['glyf'][glyph_name] = glyph

        advance_width = glyph_width + lsb + rsb

        if 'hmtx' in font:
            font['hmtx'][glyph_name] = (advance_width, lsb)

        if len(original_glyph_name.split('0F')) <= 2: 
            for cp in codepoints:
                cmap_subtable.cmap[cp] = original_glyph_name

    font['cmap'].tables.append(cmap_subtable)
    font['cmap'].tables.sort(key=lambda x: (x.platformID, x.platEncID, x.language, x.format))
    
    font.save(new_font_path)
    print(f"font saved at: {new_font_path}")

def main():
    svg_directory = "../../data/font_data/derge_font/variant_glyphs/svg" 
    blank_font_path = "../../data/base_font/AdobeBlank.ttf"  
    new_font_path = "../../data/font_data/derge_font/variant_glyphs/ttf/derge_complete.ttf"  
    glyphs_data = []
    for filename in os.listdir(svg_directory):
        if filename.endswith(".svg"):
            svg_file = os.path.join(svg_directory, filename)
            glyph, codepoints, glyph_name = parse_svg_to_glyph(svg_file)
            glyphs_data.append((glyph, codepoints, glyph_name))
    
    print(f"glyphs added: {len(glyphs_data)}")
    add_glyphs_to_font(blank_font_path, glyphs_data, new_font_path, svg_directory)

if __name__ == "__main__":
    main()