from fontTools.ttLib.tables._g_l_y_f import Glyph as TTGlyph
from fontTools.pens.basePen import BasePen
from xml.etree import ElementTree as ET
from svg.path import parse_path
import os
from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen


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

    print(f"File Name: {filename}")
    print(f"Glyph Name: {glyph_name}")
    print(f"Unicodes: {codepoints}")

    return glyph, glyph_name


def set_font_metadata(font, font_name, family_name):
    name_table = font['name']
    for name_record in name_table.names:
        if name_record.nameID == 1:
            name_record.string = family_name.encode('utf-16-be')
        elif name_record.nameID == 4:
            name_record.string = font_name.encode('utf-16-be')

def process_glyphs(svg_dir_path, font, reduction_excluded_glyphs):
    glyph_count = 0
    bearing_reduction_amount = 200
    
    for filename in os.listdir(svg_dir_path):
        if filename.endswith('.svg'):
            svg_file_path = os.path.join(svg_dir_path, filename)

            codepoints = extract_codepoints(os.path.splitext(filename)[0])
            glyph_name = generate_glyph_name(codepoints)
            
            if glyph_name in reduction_excluded_glyphs:
                desired_headline = -1700
                apply_reduction = False
            else:
                desired_headline = -2000
                apply_reduction = True

            glyph, glyph_name = parse_svg_to_glyph(svg_file_path, desired_headline)

            if glyph_name in font['glyf']:
                font['glyf'][glyph_name] = glyph
                original_advance_width, original_lsb = font['hmtx'][glyph_name]

                if apply_reduction:
                    new_lsb = max(0, original_lsb - bearing_reduction_amount)
                    new_advance_width = max(0, int(original_advance_width) - bearing_reduction_amount)
                else:
                    new_lsb = original_lsb
                    new_advance_width = original_advance_width

                font['hmtx'][glyph_name] = (new_advance_width, new_lsb)

                glyph_count += 1

    return glyph_count

def main():
    svg_dir_path = '../../data/font_data/derge_font/variant_glyphs/svg'
    old_font_path = '../../data/base_font/sambhotaUnicodeBaseShip.ttf'
    new_font_path = '../../data/font_data/derge_font/variant_glyphs/ttf/DergeComplete.ttf'
    font = TTFont(old_font_path)

    reduction_excluded_glyphs = {'uni0F72', 'uni0F7C', 'uni0F7A'}
    
    glyph_count = process_glyphs(svg_dir_path, font, reduction_excluded_glyphs)

    font_name = "DergeComplete"
    family_name = "Derge-Regular"
    set_font_metadata(font, font_name, family_name)

    font.save(new_font_path)

    print(f"Number of glyphs replaced: {glyph_count}")

if __name__ == "__main__":
    main()