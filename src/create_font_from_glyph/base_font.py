from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables._g_l_y_f import Glyph
from fontTools.ttLib.tables._c_m_a_p import cmap_format_4, cmap_format_12

def create_minimal_font(font_path):
    font = TTFont()

    # Initialize necessary tables
    font['head'] = newTable('head')
    font['hhea'] = newTable('hhea')
    font['maxp'] = newTable('maxp')
    font['post'] = newTable('post')
    font['name'] = newTable('name')
    font['OS/2'] = newTable('OS/2')
    font['glyf'] = newTable('glyf')
    font['hmtx'] = newTable('hmtx')
    font['loca'] = newTable('loca')
    font['cmap'] = newTable('cmap')

    # Setup 'glyf' table
    glyph = Glyph()
    glyph.coordinates = []
    glyph.endPtsOfContours = []
    glyph.flags = []
    font['glyf']['.notdef'] = glyph  # Correct assignment
    font['hmtx']['.notdef'] = (500, 0)  # Correct hmtx setup

    # Setup 'cmap' table
    cmap_table = font['cmap']
    cmap_table.tableVersion = 0
    cmap_table.tables = []

    # cmap format 4
    cmap4 = cmap_format_4(4)
    cmap4.platformID = 3
    cmap4.platEncID = 1
    cmap4.language = 0
    cmap4.cmap = {32: 0}  # Mapping space character

    # cmap format 12
    cmap12 = cmap_format_12(12)
    cmap12.platformID = 3
    cmap12.platEncID = 10
    cmap12.language = 0
    cmap12.cmap = {32: 0}  # Mapping space character again for full range

    # Append subtables to the cmap table
    cmap_table.tables.append(cmap4)
    cmap_table.tables.append(cmap12)

    # Setup 'glyf', 'loca', and 'hmtx' for at least one glyph (space character)
    glyph = Glyph()  # Create a glyph instance
    glyph.coordinates = []
    glyph.endPtsOfContours = []
    glyph.flags = []
    font['glyf']['.notdef'] = glyph
    font['hmtx'][0] = (500, 0)
    # Setup 'glyf', 'loca', and 'hmtx' for at least one glyph (space character)
    glyph = font['glyf'].glyphs['.notdef'] = font['glyf'].Glyph()
    glyph.coordinates = []
    glyph.endPtsOfContours = []
    glyph.flags = []
    font['hmtx'][0] = (500, 0)  # Advance width and left side bearing for '.notdef'

    # Setup 'post' table
    font['post'].formatType = 2.0
    font['post'].italicAngle = 0
    font['post'].underlinePosition = -100
    font['post'].underlineThickness = 50
    font['post'].isFixedPitch = 0
    font['post'].minMemType42 = 0
    font['post'].maxMemType42 = 0
    font['post'].minMemType1 = 0
    font['post'].maxMemType1 = 0

    # Setup 'name' table
    name_record = font['name']
    name_record.setName("Example Font", 1, 3, 1, 1033)  # Family Name
    name_record.setName("Regular", 2, 3, 1, 1033)  # Subfamily Name
    name_record.setName("Example Font;1.0;2023", 5, 3, 1, 1033)  # Version string

    # Setup 'OS/2' table
    font['OS/2'].version = 4
    font['OS/2'].xAvgCharWidth = 500
    font['OS/2'].usWeightClass = 400
    font['OS/2'].usWidthClass = 5
    font['OS/2'].fsType = 0x0004  # Installable embedding
    font['OS/2'].ySubscriptXSize = 650
    font['OS/2'].ySubscriptYSize = 700
    font['OS/2'].ySubscriptXOffset = 0
    font['OS/2'].ySubscriptYOffset = 140
    font['OS/2'].ySuperscriptXSize = 650
    font['OS/2'].ySuperscriptYSize = 700
    font['OS/2'].ySuperscriptXOffset = 0
    font['OS/2'].ySuperscriptYOffset = 490
    font['OS/2'].yStrikeoutSize = 50
    font['OS/2'].yStrikeoutPosition = 350
    font['OS/2'].sFamilyClass = 0
    font['OS/2'].panose = (2, 11, 6, 9, 4, 2, 2, 2, 2, 4)
    font['OS/2'].ulUnicodeRange1 = 0xFFFFFFFF
    font['OS/2'].ulUnicodeRange2 = 0xFFFFFFFF
    font['OS/2'].ulUnicodeRange3 = 0xFFFFFFFF
    font['OS/2'].ulUnicodeRange4 = 0xFFFFFFFF
    font['OS/2'].achVendID = "NONE"
    font['OS/2'].fsSelection = 0x0040
    font['OS/2'].usFirstCharIndex = 32
    font['OS/2'].usLastCharIndex = 32
    font['OS/2'].sTypoAscender = 800
    font['OS/2'].sTypoDescender = -200
    font['OS/2'].sTypoLineGap = 200
    font['OS/2'].usWinAscent = 800
    font['OS/2'].usWinDescent = 200
    font['OS/2'].ulCodePageRange1 = 0xFFFFFFFF
    font['OS/2'].ulCodePageRange2 = 0xFFFFFFFF

    # Save the font
    font.save(font_path)
    print(f"Font saved at {font_path}")

create_minimal_font("minimal_font.ttf")
