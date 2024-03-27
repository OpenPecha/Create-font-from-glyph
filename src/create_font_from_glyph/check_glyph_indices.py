from fontTools.ttLib import TTFont

font_path = 'C:/Users/tenka/monlam/create-font-from-glyph/test-create-font-from-glyph/create_font_from_glyph/sambhotaUnicodeBaseShip.ttf'
font = TTFont(font_path)
cmap = font['cmap']
glyph_indices = {}

for table in cmap.tables:
    if table.isUnicode():
    
        for codepoint, glyph_id in table.cmap.items():
            glyph_indices[codepoint] = glyph_id

for codepoint, glyph_id in glyph_indices.items():
    print(f"Unicode codepoint: U+{codepoint:04X}, Glyph index: {glyph_id}")

font.close()
