from fontTools.ttLib import TTFont

def check_tibetan_glyph_names(font_path):
    try:
        font = TTFont(font_path)
        glyph_set = font.getGlyphSet()
        tibetan_glyph_names = [glyph_name for glyph_name in glyph_set.keys() if glyph_name.startswith("uni0F")]
        return tibetan_glyph_names
    except Exception as e:
        print(f"Error: {e}")
        return None

font_path = "SambhotaDege.ttf"
tibetan_glyph_names = check_tibetan_glyph_names(font_path)

if tibetan_glyph_names is not None:
    print("Tibetan Glyph Names:")
    for glyph_name in tibetan_glyph_names:
        print(glyph_name)
