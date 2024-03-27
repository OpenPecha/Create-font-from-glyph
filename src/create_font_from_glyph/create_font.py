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
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.svgLib import SVGPath
from fontTools.ufoLib.glifLib import Glyph
from fontTools.ttLib import TTFont
from svg.path import parse_path
from xml.dom.minidom import parse


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


# determing unicdode
def extract_codepoints(filename):
    tibetan_char = filename.split('_')[0]
    codepoints = [ord(char) for char in tibetan_char]
    return codepoints

# for assigning glyph name


def generate_glyph_name(codepoints):
    glyph_name = 'uni' + ''.join(f"{codepoint:04X}" for codepoint in codepoints)
    return glyph_name


# get the dimension of svg
def get_svg_size(svg_file_path):
    doc = parse(svg_file_path)
    path_strings = [path.getAttribute('d') for path in doc.getElementsByTagName('path')]
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')
    for path_string in path_strings:
        path_data = parse_path(path_string)
        for move in path_data:
            min_x = min(min_x, move.start.real, move.end.real)
            max_x = max(max_x, move.start.real, move.end.real)
            min_y = min(min_y, move.start.imag, move.end.imag)
            max_y = max(max_y, move.start.imag, move.end.imag)
    width = max_x - min_x
    height = max_y - min_y
    return width, height

# to parse the svg


def parse_svg_to_glyph(svg_file_path, glyph_name=None, unicodes=None, glyph_set=None):
   
    pen = TTGlyphPen(glyph_set)
    path = SVGPath(svg_file_path)
    path.draw(pen)
    glyph = pen.glyph() 
    glyph.name = glyph_name
    glyph.width, glyph.height = get_svg_size(svg_file_path)
    glyph.unicodes = unicodes or []

    # print(f"Created glyph '{glyph.name}' with width {glyph.width}, height {glyph.height}, and unicodes {glyph.unicodes}")

    return glyph



def create_glyph(directory_path, width=0, height=0, unicodes=None, glyph_set=None):
    glyph_objects = []
    processed_files = set() 
    for filename in os.listdir(directory_path):
        if filename.endswith('.svg'):
            svg_file_path = os.path.join(directory_path, filename)
            if svg_file_path in processed_files: 
                continue
            codepoints = extract_codepoints(filename)
            print(f"Processing file: {filename}, Codepoints: {codepoints}") 
            glyph_name = generate_glyph_name(codepoints)
            glyph = parse_svg_to_glyph(svg_file_path, glyph_name, codepoints, glyph_set)
            glyph_objects.append(glyph)
            processed_files.add(svg_file_path) 
    return glyph_objects



# to create new font
# def replace_glyphs_in_font(font_path, svg_directory_path, new_font_path):
#     font = TTFont(font_path)
#     glyph_objects = create_glyph(svg_directory_path)

#     for glyph_object in glyph_objects:
#         font['glyf'][glyph_object.name] = glyph_object
#         for unicode in glyph_object.unicodes:
#             font['cmap'].tables[0].cmap[unicode] = glyph_object.name

#     font.save(new_font_path)

#     print(f"new font created at  {new_font_path}.")


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

                            directory_path = "data/derge_img/svg"
                            glyphs = create_glyph(directory_path)
                            for glyph in glyphs:
                                print(f"Glyph Name: {glyph.name}, Unicode Codepoints: {glyph.unicodes}")

                        except Exception as e:
                            logging.error(f"Error processing image {line['image']}: {e}")
                            traceback.print_exc()
        except Exception as e:
            logging.error(f"Error processing {jsonl_path}: {e}")

# def main():
    
#     directory_path = r"C:\Users\tenka\monlam\create-font-from-glyph\test-create-font-from-glyph\data\derge_img\svg"
#     glyphs = create_glyph(directory_path)
#     for glyph in glyphs:
#         print(f"Glyph Name: {glyph.name}, Unicode Codepoints: {glyph.unicodes}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
