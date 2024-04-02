from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen

font = TTFont('../../data/base_font/MonlamTBslim.ttf')
glyph_set = font.getGlyphSet()
glyph_count = 0

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
    unicode_value = None
    if glyph_name.startswith("uni"):
        try:
            unicode_value = int(glyph_name[3:], 16)
        except ValueError:
            pass

    print(f"Glyph name: {glyph_name}")
    print(f"Unicode value: {unicode_value}")
    print(f"Advance width: {advance_width}")
    print(f"Left Side Bearing (LSB): {left_side_bearing}")
    print(f"Right Side Bearing (RSB): {right_side_bearing}")
    print(f"xMin: {xMin}")
    print(f"xMax: {xMax}")
    print(f"yMin: {yMin}")
    print(f"yMax: {yMax}")
    print("\n")
    glyph_count += 1

print(f"number of glyphs in the font: {glyph_count}")
