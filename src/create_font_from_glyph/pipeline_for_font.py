from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib.tables._g_l_y_f import Glyph as TTGlyph
from xml.etree import ElementTree as ET
from svg.path import parse_path
import os


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

    return glyph, glyph_name


def set_font_metadata(font, font_name, family_name):
    name_table = font['name']
    for name_record in name_table.names:
        if name_record.nameID == 1:
            name_record.string = family_name.encode('utf-16-be')
        elif name_record.nameID == 4:
            name_record.string = font_name.encode('utf-16-be')

# for tsa, tsha, dza


def adjust_baseline_for_glyph(glyph_name, baseline):
    special_baseline_glyphs = {'uni0F59', 'uni0F5A', 'uni0F5B'}
    if any(glyph in glyph_name for glyph in special_baseline_glyphs):
        return -1900
    return baseline


def process_glyphs(svg_dir_path, font, vowel_glyphs):

    for filename in os.listdir(svg_dir_path):
        if filename.endswith('.svg'):
            svg_file_path = os.path.join(svg_dir_path, filename)

            codepoints = extract_codepoints(os.path.splitext(filename)[0])
            glyph_name = generate_glyph_name(codepoints)

            # headlined for vowel glyphs
            if glyph_name in vowel_glyphs:
                desired_headline = -1790
            elif glyph_name == 'uni0F72':
                desired_headline = -1750
            else:
                desired_headline = -2000

            desired_headline = adjust_baseline_for_glyph(glyph_name, desired_headline)

            glyph, glyph_name = parse_svg_to_glyph(svg_file_path, desired_headline)

            if glyph_name in font['glyf']:
                font['glyf'][glyph_name] = glyph

                try:
                    parts = filename.split('_')
                    width_pixel = int(parts[1])
                    lsb_pixel = int(parts[2])
                    rsb_pixel = int(parts[3].replace('.svg', ''))
                except (IndexError, ValueError):
                    print(f"file with wrong filename format: {filename}")
                    continue

                # convert pixel values to font units
                width = int((width_pixel / 160) * 1000)
                lsb = int((lsb_pixel / 160) * 1000)
                rsb = int((rsb_pixel / 160) * 1000)
                advance_width = width + lsb + rsb + 50

                shift_amounts = {
                    'uni0F7C': -300,  # ོ
                    'uni0F7A': -330,  # ེ
                    'uni0F72': -350  # ི
                }
                # for vowel glyphs
                if glyph_name in shift_amounts:
                    lsb += shift_amounts[glyph_name]
                    rsb = 0
                    advance_width = 0

                # for nga
                if glyph_name == 'uni0F20':
                    lsb = lsb
                    rsb = 0
                    advance_width = width

                # update font metrics with lsb, rsb and advance width
                font['hmtx'][glyph_name] = (advance_width, lsb)
                font['glyf'][glyph_name].rsb = rsb


def main():
    svg_dir_path = 'data/font_data/derge_font/v5_complete_glyphs/reduced_de_noise_svg'
    old_font_path = 'data/base_font/sambhotaUnicodeBaseShip.ttf'
    new_font_path = 'fonts/derge_font/DergeComplete.4.0.ttf'
    font = TTFont(old_font_path)

    vowel_glyphs = {'uni0F7C', 'uni0F7A'}

    process_glyphs(svg_dir_path, font, vowel_glyphs)

    font_name = "DergeComplete"
    family_name = "Derge-Regular.4.0"
    set_font_metadata(font, font_name, family_name)

    font.save(new_font_path)

    print("font created successfully")


if __name__ == "__main__":
    main()
