from fontTools.ttLib import TTFont

def print_unicode_values_and_total_glyphs(font_path):
    font = TTFont(font_path)
    cmap = font.getBestCmap()

    glyph_to_unicode = {glyph: code for code, glyph in cmap.items()}

    total_glyphs = 0
    for glyph_name in font['glyf'].keys():
        if glyph_name in glyph_to_unicode:
            unicode_value = glyph_to_unicode[glyph_name]
            print(f"Glyph name: {glyph_name}, Unicode value: {unicode_value}")
        total_glyphs += 1

    print(f"Total number of glyphs in the font: {total_glyphs}")

print_unicode_values_and_total_glyphs('../../data/base_font/MonlamTBslim.ttf')
