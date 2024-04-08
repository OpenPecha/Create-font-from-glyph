from pathlib import Path
from config import MONLAM_AI_OCR_BUCKET, monlam_ai_ocr_s3_client
from PIL import Image, ImageDraw
import urllib.parse
import os
import numpy as np
import jsonlines
import logging
import traceback
import re
import subprocess
from xml.etree import ElementTree as ET
import xml.etree.ElementTree as ET
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.ttLib import TTFont, TTLibError
import os
import xml.etree.ElementTree as ET
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.misc.transform import Identity
import xml.etree.ElementTree as ET





s3 = monlam_ai_ocr_s3_client
bucket_name = MONLAM_AI_OCR_BUCKET

logging.basicConfig(filename='skipped_glyph.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')


# get image path from url
def get_image_path(image_url):
    image_parts = (image_url.split("?")[0]).split("/")
    obj_key = "/".join(image_parts[4:])
    decoded_key = urllib.parse.unquote(obj_key)
    image_name = decoded_key.split("/")[-1]
    file_name, file_extension = os.path.splitext(image_name)
    image_name_without_suffix = re.sub(r'(_\d+)$', '', file_name)
    image_name_tibetan_only = re.sub(r'[^\u0F00-\u0FFF]', '', image_name_without_suffix)

    try:
        response = s3.get_object(Bucket=bucket_name, Key=decoded_key)
        image_data = response['Body'].read()
        with open(fr"data/derge_img/downloaded_glyph/{image_name_tibetan_only}{file_extension}", 'wb') as f:
            f.write(image_data)

    except Exception as e:
        print(fr"Error while downloading {image_name} due to {e}")
    return fr"data/derge_img/downloaded_glyph/{image_name_tibetan_only}{file_extension}"

# new image name


def get_image_output_path(cleaned_image, image_name, output_path, headlines):
    headline_starts = headlines["headline_starts"]
    headline_ends = headlines["headline_ends"]
    glyph_name = image_name.split(".")[0].split("_")[0]

    left_edge, right_edge = get_edges(cleaned_image)
    if left_edge is None:
        return None

    # new image name (Unicode_(RE-LE)_(BS-LE)_(RE-BE).png)
    new_image_name = f"{glyph_name}_{int(right_edge - left_edge)}_{int(headline_starts - left_edge)}_{int(right_edge - headline_ends)}.png"
    image_output_path = f"{output_path}/{new_image_name}"
    # .for debug

    return image_output_path


# for left and right edges

def get_edges(cleaned_image):
    if cleaned_image.mode != '1':
        cleaned_image = cleaned_image.convert('1')
    image_array = np.array(cleaned_image)
    image_array = image_array[:, 1:-1]
    black_pixels = np.where(image_array == 0)
    if black_pixels[0].size == 0 or black_pixels[1].size == 0:
        return None, None

    left_edge = np.min(black_pixels[1]) + 1
    right_edge = np.max(black_pixels[1]) + 1
    return left_edge, right_edge


# for headlines


def get_headlines(baselines_coord):
    min_x = min(coord[0] for coord in baselines_coord)
    max_x = max(coord[0] for coord in baselines_coord)
    headlines = {
        "headline_starts": min_x,
        "headline_ends": max_x
    }
    return headlines

# convert outside to white


def png_process(png_image_path, span, cleaned_image_path):
    baselines_coord = None
    polygon_points = None
    for info in span:
        if info["label"] == "Base Line":
            baselines_coord = info["points"]
        if info["label"] == "Glyph":
            polygon_points = [(x, y) for x, y in info["points"]]
    if baselines_coord is None or polygon_points is None:
        return None

    image = Image.open(png_image_path)
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(polygon_points, fill=255)
    cleaned_image = Image.new("RGB", image.size, (255, 255, 255))
    cleaned_image.paste(image, mask=mask)

    headlines = get_headlines(baselines_coord)
    cleaned_image_path = get_image_output_path(
        cleaned_image, png_image_path.split('/')[-1], cleaned_image_path, headlines)

    if cleaned_image_path is not None:
        cleaned_image = cleaned_image.convert("RGBA")  # convert white regions to transparent
        data = cleaned_image.getdata()
        newData = []
        for item in data:
            if item[0] == 255 and item[1] == 255 and item[2] == 255:
                newData.append((255, 255, 255, 0))
            else:
                newData.append(item)
        cleaned_image.putdata(newData)
        cleaned_image.save(cleaned_image_path)
        return cleaned_image_path
    else:
        return None


# for finding bounding box
def find_glyph_bbox(image):
    gray_image = image.convert('L')
    binary_image = gray_image.point(lambda p: p < 128 and 255)
    bbox = binary_image.getbbox()
    return bbox


# convert png to svg

def png_to_svg(cleaned_image_path, svg_output_path):
    image = Image.open(cleaned_image_path).convert('1')
    pbm_path = "temp.pbm"
    image.save(pbm_path)
    sanitized_filename = re.sub('[^A-Za-z0-9_.]+', '', Path(cleaned_image_path).stem)

    # create a temp svg_output_path for sanitized name
    temp_svg_output_path = Path(f"data/derge_img/svg/{sanitized_filename}.svg")

    subprocess.run(["potrace", pbm_path, "-s", "--scale", "5.5", "-o", temp_svg_output_path])
    os.remove(pbm_path)

    if os.path.exists(svg_output_path):
        os.remove(svg_output_path)

    # rename the temp svg file to the original name
    os.rename(temp_svg_output_path, svg_output_path)

#  cleaned svg


def clean_svg(input_file, output_file):

    tree = ET.parse(input_file)
    root = tree.getroot()
    for elem in root.iter('{http://www.w3.org/2000/svg}metadata'):
        root.remove(elem)

    svg_elem = root.find('{http://www.w3.org/2000/svg}svg')
    if svg_elem is not None:
        del svg_elem.attrib['version']
        del svg_elem.attrib['preserveAspectRatio']
        del svg_elem.attrib['width']
        del svg_elem.attrib['height']
    tree.write(output_file, xml_declaration=True, encoding='utf-8')


def parse_svg_path_commands(svg_path_data):
    commands = []
    current_command = ''
    numbers = ''
    for char in svg_path_data:
        if char.isalpha():  
            if current_command:
                commands.append((current_command, numbers.strip()))
            current_command = char
            numbers = ''
        elif char.isdigit() or char in '.-':  
            numbers += char
        elif char == ',':
            numbers += ' '

    if current_command:
        commands.append((current_command, numbers.strip()))

    return commands

def parse_svg(svg_path):
    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
        paths = root.findall('.//{http://www.w3.org/2000/svg}path')
        for path in paths:
            path_data = path.attrib['d']
            commands = parse_svg_path_commands(path_data)
            yield commands
    except Exception as e:
        print(f"error parsing svg: {e}")

def convert_svgs_to_glyphs(input_dir, output_ttf_path):
    if not os.path.exists(input_dir):
        print(f"no input directry")
        return

    glyphs = {}
    for filename in os.listdir(input_dir):
        if filename.endswith(".svg"):
            svg_file_path = os.path.join(input_dir, filename)
            unicode_codepoint = extract_unicode_from_filename(filename)
            glyph_name = f"uni{unicode_codepoint.upper()}"
            glyphs[glyph_name] = create_glyph_svg(svg_file_path)

    create_ttf_font(glyphs, output_ttf_path)

def extract_unicode_from_filename(filename):
    unicode_hex = filename.split("_")[1]
    unicode_value = int(unicode_hex, 16)
    return format(unicode_value, 'X')

def create_glyph_svg(svg_file_path):
    try:
        svg_commands = parse_svg(svg_file_path)
        glyph_pen = TTGlyphPen(None)
        for commands in svg_commands:
            for command in commands:
                glyph_pen._moveTo(command[1]) if command[0] == 'M' else None
                glyph_pen._lineTo(command[1]) if command[0] == 'L' else None
                glyph_pen._curveToOne(command[1], command[2], command[3]) if command[0] == 'C' else None
                glyph_pen._closePath() if command[0] == 'Z' else None

        glyph = Glyph()
        glyph_pen.end(glyph)
        return glyph
    except Exception as e:
        print(f"error converting svg to glyph: {e}")

def create_ttf_font(glyphs, output_ttf_path):
    font = TTFont()
    font.setGlyphOrder(sorted(glyphs.keys()))

    for glyph_name, glyph in glyphs.items():
        font['glyf'][glyph_name] = glyph

    font.save(output_ttf_path)
    print(f"custom font saved at {output_ttf_path}")

input_directory = "data/derge_img/glyphs"
output_ttf_path = "data/derge_img/custom_font.ttf"
convert_svgs_to_glyphs(input_directory, output_ttf_path)

    
 

def main():
    jsonl_paths = list(Path("derge/glyph_ann_reviewed_batch6_ga").iterdir())
    processed_ids = set()
    for jsonl_path in jsonl_paths:
        try:
            with jsonlines.open(jsonl_path) as reader:
                for line in reader:
                    if line["answer"] == "accept":
                        try:
                            image_id = line["id"].split("_")[0]
                            if image_id in processed_ids:
                                logging.info(f"Skipping duplicate ID: {image_id}")
                                continue
                            processed_ids.add(image_id)
                            image_span = line["spans"]
                            png_image_path = get_image_path(line["image"])

                            cleaned_image_path = png_process(
                                png_image_path, image_span, Path("data/derge_img/cleaned_images"))

                            if cleaned_image_path is None:
                                logging.info(f"Skipping {png_image_path}")
                                continue
                            filename = Path(cleaned_image_path).stem
                            svg_output_path = Path(f"data/derge_img/svg/{filename}.svg")
                            png_to_svg(cleaned_image_path, svg_output_path)

                            input_svg = Path(svg_output_path)
                            output_cleaned_svg = Path(f"data/derge_img/cleaned_svg/{filename}.svg")
                            clean_svg(input_svg, output_cleaned_svg)

                        except Exception as e:
                            logging.error(f"Error processing image {line['image']}: {e}")
                            traceback.print_exc()
        except Exception as e:
            logging.error(f"Error processing {jsonl_path}: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
