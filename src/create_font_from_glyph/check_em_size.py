import freetype

def get_em_square_size(font_path, font_size):
    # Initialize FreeType library
    face = freetype.Face(font_path)
    
    # Set the font size
    face.set_char_size(0, font_size * 64)
    
    # Get the em size in pixels
    em_pixels = face.size.ascender // 64
    
    return em_pixels

# Example usage
font_path = "../../data/base_font/sambhotaUnicodeBaseShip.ttf"  # Replace with the path to your font file
font_size = 12  # Replace with the desired font size
em_size = get_em_square_size(font_path, font_size)
print(f"The em square size of the font is approximately {em_size} pixels.")
