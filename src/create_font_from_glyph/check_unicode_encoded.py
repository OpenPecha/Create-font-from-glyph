from fontTools.ttLib import TTFont

def is_tibetan_unicode_font(font_path):
    try:
        font = TTFont(font_path)
        for table in font['cmap'].tables:
            if table.platformID == 3 and table.platEncID in [1, 10]:
                for char_code in range(0x0F00, 0x0FFF):
                    if table.cmap.get(char_code) is not None:
                        return True
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

font_path = 'sambhotaUnicodeBaseShip.ttf'
unicode_check = is_tibetan_unicode_font(font_path)

if unicode_check is None:
    print("error occurred while checking the font.")
elif unicode_check:
    print(f"supportig tibetan Unicode range.")
else:
    print(f"not supportig tibetan Unicode range.")

