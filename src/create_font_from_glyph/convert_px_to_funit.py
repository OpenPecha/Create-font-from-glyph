import os
import re

def convert_pixel_to_glyph_unit(pixels, units_per_em, point_size, ppi,):
    return (pixels * units_per_em) / ((point_size * ppi) / 72)

def extract_numbers_from_filename(filename):
    numbers = re.findall(r'\d+', filename)
    return [int(num) for num in numbers]

def process_svg_files(directory, units_per_em, point_size, ppi):
    for filename in os.listdir(directory):
        if filename.endswith(".svg"):
            numbers = extract_numbers_from_filename(filename)
            glyph_units = [convert_pixel_to_glyph_unit(num, units_per_em, point_size, ppi) for num in numbers]
            print(f"file name: {filename}, glyph unit: {glyph_units}")

process_svg_files("../../data/derge_font/svg", 1000, 12, 140)
