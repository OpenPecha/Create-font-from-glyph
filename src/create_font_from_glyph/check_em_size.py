import freetype

def get_em_square_size(font_path, font_size):
    face = freetype.Face(font_path)

    face.set_char_size(0, font_size * 64)
    em_pixels = face.size.ascender // 64
    
    return em_pixels


font_path = "../../data/base_font/AdobeBlank.ttf"  
font_size = 12  
em_size = get_em_square_size(font_path, font_size)
print(f"The em square size of the font is approximately {em_size} pixels.")
