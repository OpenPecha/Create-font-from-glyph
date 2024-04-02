from fontTools.ttLib.tables._g_l_y_f import Glyph as TTGlyph
from fontTools.pens.basePen import BasePen
from xml.etree import ElementTree as ET
from svg.path import parse_path
import os
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen


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
        self.currentPoint = pt
        self.path.append(('moveTo', pt))

    def _lineTo(self, pt):
        self.currentPoint = pt
        self.path.append(('lineTo', pt))

    def _curveToOne(self, pt1, pt2, pt3):
        self.currentPoint = pt3
        self.path.append(('curveTo', (pt1, pt2, pt3)))

    def get_path(self):
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


def parse_svg_to_glyph(svg_file_path, glyph_name=None, unicode=None):
    filename = os.path.splitext(os.path.basename(svg_file_path))[0]
    codepoints = extract_codepoints(filename)
    glyph_name = generate_glyph_name(codepoints)
    unicode = codepoints

    tree = ET.parse(svg_file_path)
    root = tree.getroot()

    for element in root.iter('{http://www.w3.org/2000/svg}path'):
        path_data = element.attrib.get('d', '')
        glyph = TTGlyph()
        glyph.unicodes = unicode or []
        pen = SVGPen(None)
        pen.pathFromSVGPathData(path_data)
        ttPen = TTGlyphPen()

        for command in pen.get_path():
            if command[0] == 'moveTo':
                ttPen.moveTo(command[1])
            elif command[0] == 'lineTo':
                ttPen.lineTo(command[1])
            elif command[0] == 'curveTo':
                ttPen.curveTo(*command[1])
            elif command[0] == 'closePath':
                ttPen.closePath()

        glyph = ttPen.glyph()

    print(f"File Name: {filename}")
    print(f"Glyph Name: {glyph_name}")
    print(f"Unicodes: {unicode}")

    return glyph, glyph_name

def main():
    svg_dir_path = '../../data/derge_font/svg'
    old_font_path = '../../data/base_font/sambhotaUnicodeBaseShip.ttf'  
    new_font_path = '../../data/derge_font/ttf/derge.ttf' 
    font = TTFont(old_font_path)  

    glyph_count = 0  
    for filename in os.listdir(svg_dir_path):
        if filename.endswith('.svg'):
            svg_file_path = os.path.join(svg_dir_path, filename)
            glyph, glyph_name = parse_svg_to_glyph(svg_file_path)

            if glyph_name in font['glyf']:
                font['glyf'][glyph_name] = glyph
                glyph_count += 1 

    font.save(new_font_path)

    print(f"Number of glyphs replaced: {glyph_count}")  

if __name__ == "__main__":
    main()
