import os
import xml.etree.ElementTree as ET
from svg.path import parse_path

def calculate_headline(svg_file_path):
    tree = ET.parse(svg_file_path)
    root = tree.getroot()

    max_y = float('-inf')

    for element in root.iter('{http://www.w3.org/2000/svg}path'):
        path_data = element.attrib.get('d', '')
        path = parse_path(path_data)

        for segment in path:
            if segment.start.imag > max_y:
                max_y = segment.start.imag
            if segment.end.imag > max_y:
                max_y = segment.end.imag

    return max_y


svg_files_path = "../../data/derge_font/svg"

for filename in os.listdir(svg_files_path):
    if filename.endswith(".svg"):
        svg_file_path = os.path.join(svg_files_path, filename)
        headline = calculate_headline(svg_file_path)
        print(f"The headline for {filename} is {headline}")
