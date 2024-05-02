import os
import re


def convert_pixel_to_glyph_unit(pixels, units_per_em=90, point_size=12, ppi=100):
    """Convert pixel units into font units."""
    return round(pixels * (units_per_em / (point_size) * (ppi / 72)))


def extract_numbers_from_filename(filename):
    """Extract units from filename, where filename is in the format ཀ_x_y_z."""
    numbers = re.findall(r'\d+', filename)
    return [int(num) for num in numbers]


def extract_glyph_name(filename):
    """Extract the glyph name from the filename."""
    return filename.split("_")[0]


def create_font_units(directory):
    results = []
    for filename in os.listdir(directory):
        if filename.endswith(".svg"):
            numbers = extract_numbers_from_filename(filename)
            glyph_units = [convert_pixel_to_glyph_unit(num) for num in numbers]
            glyph_width, lsb, rsb = glyph_units
            glyph_name = extract_glyph_name(filename)
            results.append((glyph_width, lsb, rsb,))
            advance_width = glyph_width + lsb + rsb
            # print(f"Glyph Name: {glyph_name}, Glyph Width: {glyph_width}, LSB: {lsb}, RSB: {rsb}")
            # print("Advance Width:", advance_width)
        
    return results


results = create_font_units("../../data/derge_font/Derge_test_ten_glyphs/svg")
