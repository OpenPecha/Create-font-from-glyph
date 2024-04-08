import os
import xml.etree.ElementTree as ET
from svg.path import parse_path, Line, Arc, CubicBezier, QuadraticBezier, Close

def translate_path(path, dy):
    translated_path = []
    for segment in path:
        if isinstance(segment, Line):
            start = segment.start + complex(0, dy)
            end = segment.end + complex(0, dy)
            translated_path.append(f"L {end.real} {end.imag}")
        elif isinstance(segment, CubicBezier):
            start = segment.start + complex(0, dy)
            control1 = segment.control1 + complex(0, dy)
            control2 = segment.control2 + complex(0, dy)
            end = segment.end + complex(0, dy)
            translated_path.append(f"C {control1.real} {control1.imag}, {control2.real} {control2.imag}, {end.real} {end.imag}")
        elif isinstance(segment, Close):
            translated_path.append("Z")
    return ' '.join(translated_path)



def adjust_headline(svg_file_path, desired_headline):
    tree = ET.parse(svg_file_path)
    root = tree.getroot()

    max_y = float('-inf')
    for element in root.iter('{http://www.w3.org/2000/svg}path'):
        path_data = element.attrib.get('d', '')
        path = parse_path(path_data)

        for segment in path:
            if segment.start.imag > max_y:
                max_y = segment.start.imag
    dy = desired_headline - max_y

    for element in root.iter('{http://www.w3.org/2000/svg}path'):
        path_data = element.attrib.get('d', '')
        path = parse_path(path_data)
        translated_path = translate_path(path, dy=dy)
        element.attrib['d'] = ' '.join(str(segment) for segment in translated_path)

    tree.write(svg_file_path)

svg_files_path = "../../data/derge_font/svg"
desired_headline = 1266

for filename in os.listdir(svg_files_path):
    if filename.endswith(".svg"):
        svg_file_path = os.path.join(svg_files_path, filename)
        adjust_headline(svg_file_path, desired_headline)
