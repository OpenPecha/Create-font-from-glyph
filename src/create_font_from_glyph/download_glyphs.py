from fontTools.ttLib import TTFont

def extract_glyphs(font_file_path, output_file_path):
    try:
        font = TTFont(font_file_path)

        glyph_names = []
        for table in font['cmap'].tables:
            for glyph_id, glyph_name in table.cmap.items():
                glyph_names.append(glyph_name)

        glyph_names.sort()

        with open(output_file_path, 'w') as output_file:
            for glyph_name in glyph_names:
                output_file.write(f'{glyph_name}\n')

        print(f'Glyphs extracted and saved to "{output_file_path}" successfully.')

    except Exception as e:
        print(f'Error: {e}')

font_file_path = '../../data/derge_font/ttfDerge(monlam).ttf'  
output_file_path = 'Tibetan Essential List.txt'  

extract_glyphs(font_file_path, output_file_path)
