import os
import re

def convert_pixel_to_glyph_unit(pixels, units_per_em=100, point_size=12, ppi=100):
    """Converts pixels to glyph units and rounds the result to the nearest integer."""
    return round(pixels * (units_per_em / (point_size) * (ppi / 72)))

def extract_numbers_from_filename(filename):
    """Extracts numbers from a filename."""
    numbers = re.findall(r'\d+', filename)
    return [int(num) for num in numbers]

def create_font_units(directory):
    """Creates font units for all SVG files in a directory."""
    results = []
    for filename in os.listdir(directory):
        if filename.endswith(".svg"):   
            numbers = extract_numbers_from_filename(filename)
            glyph_units = [convert_pixel_to_glyph_unit(num) for num in numbers]
            glyph_width, lsb, rsb = glyph_units  
            results.append((glyph_width, lsb, rsb,))
    return results

results = create_font_units("../../data/derge_font/svg")
for glyph_width, lsb, rsb in results:
    print(f"Glyph width: {glyph_width}, LSB: {lsb}, RSB: {rsb}")

