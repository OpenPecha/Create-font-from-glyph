from fontTools.ttLib import TTFont

def check_tables(font_path):
    font = TTFont(font_path)
    
    if 'glyf' in font:
        print("The font has a 'glyf' table.")
    else:
        print("The font does not have a 'glyf' table.")
        
    if 'loca' in font:
        print("The font has a 'loca' table.")
    else:
        print("The font does not have a 'loca' table.")

def main():
    font_path = '../../data/base_font/'
    check_tables(font_path)

if __name__ == "__main__":
    main()
