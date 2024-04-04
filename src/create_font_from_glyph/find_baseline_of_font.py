from fontTools.ttLib import TTFont

def get_baseline_alignment(font_path):
    font = TTFont(font_path)

    if 'OS/2' not in font:
        raise ValueError("Font does not contain 'OS/2' table")

    os2_table = font['OS/2']
    ascender = os2_table.sTypoAscender
    descender = os2_table.sTypoDescender
    baseline_alignment = ascender - descender

    return baseline_alignment
font_path = '../../data/base_font/MonlamTBslim.ttf'
baseline_alignment = get_baseline_alignment(font_path)
print(f"Baseline Alignment: {baseline_alignment}")
