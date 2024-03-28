from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.svgLib import SVGPath
from fontTools.ufoLib.glifLib import Glyph
from fontTools.ttLib import TTFont
import os



# to parse the svg
def parse_svg_to_glyph(svg_file_path, glyph_name=None, width=0, height=0, unicodes=None, glyph_set=None):
    glyph = Glyph(glyph_name, glyph_set)
    glyph.width = width
    glyph.height = height
    glyph.unicodes = unicodes or []

    pen = TTGlyphPen(glyph) 
    path = SVGPath(svg_file_path) 
    path.draw(pen)

    return glyph

# for assigning unicode
def extract_codepoints(filename):
    tibetan_char = filename.split('_')[0]
    codepoints = [f"U+{ord(char):04X}" for char in tibetan_char]
    return codepoints

# for assigning glyph name
def generate_glyph_name(codepoints):
    glyph_name = 'uni' + ''.join(codepoint.split('+')[1] for codepoint in codepoints)
    return glyph_name

def create_glyph(directory_path, width=0, height=0, unicodes=None, glyph_set=None):
    glyph_objects = []
    for filename in os.listdir(directory_path):
        if filename.endswith('.svg'):
            svg_file_path = os.path.join(directory_path, filename)
            codepoints = extract_codepoints(filename)
            glyph_name = generate_glyph_name(codepoints)
            glyph = parse_svg_to_glyph(svg_file_path, glyph_name, width, height, codepoints, glyph_set)
            glyph_objects.append(glyph)
    return glyph_objects

# # to create new font
# def replace_glyphs_in_font(font_path, svg_directory_path, new_font_path):
#     font = TTFont(font_path)
#     glyph_objects = create_glyph(svg_directory_path)

#     for glyph_object in glyph_objects:
#         font['glyf'][glyph_object.glyphName] = glyph_object
#         for unicode in glyph_object.unicodes:
#             font['cmap'].tables[0].cmap[unicode] = glyph_object.glyphName

#     font.save(new_font_path)

#     print(f"new font created at  {new_font_path}.")


def main():
    directory_path = "../../data/derge_font/svg"
    glyphs = create_glyph(directory_path)
    for glyph in glyphs:
        print(f"Glyph Name: {glyph.glyphName}, Unicode Codepoints: {glyph.unicodes}")
    

    # replace_glyphs_in_font('sambhotaUnicodeBaseShip.ttf', directory_path, 'derge_font.ttf')

if __name__ == "__main__":
    main()

