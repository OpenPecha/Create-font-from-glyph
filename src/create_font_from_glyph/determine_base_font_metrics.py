from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen

def print_glyph_and_unicode_values(font_path):
    font = TTFont(font_path)
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()

    glyph_to_unicode = {glyph: code for code, glyph in cmap.items()}

    for glyph_name in font.getGlyphNames():
        glyph = glyph_set[glyph_name]
        advance_width, left_side_bearing = font['hmtx'][glyph_name]
        pen = BoundsPen(glyph_set)

        glyph.draw(pen)
        bounds = pen.bounds
        if bounds: 
            xMin, yMin, xMax, yMax = bounds
        else:
            xMin = yMin = xMax = yMax = 0
        right_side_bearing = advance_width - (xMax - xMin)
        unicode_value = glyph_to_unicode.get(glyph_name)

        print(f"Glyph name: {glyph_name}")
        # print(f"Unicode value: {unicode_value}")
        print(f"Advance width: {advance_width}")
        print(f"Left Side Bearing (LSB): {left_side_bearing}")
        # print(f"Right Side Bearing (RSB): {right_side_bearing}")
        # print(f"xMin: {xMin}")
        # print(f"xMax: {xMax}")
        # print(f"yMin: {yMin}")
        # print(f"yMax: {yMax}")
  

print_glyph_and_unicode_values('../../data/derge_font/ttf/Derge(monlam).ttf')
