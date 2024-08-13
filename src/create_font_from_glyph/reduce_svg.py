import os
import xml.etree.ElementTree as ET
import re

def scale_path_data(path_data, scale_factor):
    def replace_func(match):
        return str(float(match.group(0)) / scale_factor)
    
    scaled_path_data = re.sub(r'-?\d+\.?\d*', replace_func, path_data)
    return scaled_path_data

def reduce_svg_size(input_svg, output_svg, scale_factor=10):
    tree = ET.parse(input_svg)
    root = tree.getroot()

    ns = {'svg': 'http://www.w3.org/2000/svg'}

    width = root.attrib.get('width', None)
    height = root.attrib.get('height', None)
    
    if width and height:
        root.set('width', str(float(width.replace('pt', '')) / scale_factor) + 'pt')
        root.set('height', str(float(height.replace('pt', '')) / scale_factor) + 'pt')

    viewBox = root.attrib.get('viewBox', None)
    if viewBox:
        viewBox_values = list(map(float, viewBox.split()))
        viewBox_values[2] /= scale_factor
        viewBox_values[3] /= scale_factor
        root.set('viewBox', ' '.join(map(str, viewBox_values)))

    for g in root.findall('.//svg:g', ns):
        transform = g.attrib.get('transform', '')
        if transform:
            translate_match = re.search(r'translate\(([^)]+)\)', transform)
            scale_match = re.search(r'scale\(([^)]+)\)', transform)
            
            if translate_match:
                translate_values = translate_match.group(1).split(',')
                translate_values = [str(float(val) / scale_factor) for val in translate_values]
                transform = re.sub(r'translate\([^)]+\)', f'translate({",".join(translate_values)})', transform)
            
            if scale_match:
                scale_values = scale_match.group(1).split(',')
                new_scale_values = [str(float(val) / scale_factor) for val in scale_values]
                transform = re.sub(r'scale\([^)]+\)', f'scale({",".join(new_scale_values)})', transform)

            g.set('transform', transform)

    for path in root.findall('.//svg:path', ns):
        d = path.attrib.get('d', '')
        if d:
            path.set('d', scale_path_data(d, scale_factor))

    tree.write(output_svg)

def process_directory(input_dir, output_dir, scale_factor=10):
    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(input_dir):
        if filename.endswith('.svg'):
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, filename)
            reduce_svg_size(input_path, output_path, scale_factor)
            print(f'Processed {filename}')

input_dir = '../../data/font_data/derge_font/v4_complete_glyphs/svg/'
output_dir = '../../data/font_data/derge_font/v4_complete_glyphs/reduced_svg'

process_directory(input_dir, output_dir, scale_factor=10)
