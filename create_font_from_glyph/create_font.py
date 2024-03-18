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
from io import BytesIO
from xml.etree import ElementTree as ET
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import RecordingPen




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
    print(new_image_name)
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




logging.basicConfig(level=logging.INFO)

def svg_to_glyph(svg_path):
    with open(svg_path, "rb") as svg_file:
        svg_data = svg_file.read()

    try:
        svg_root = ET.parse(BytesIO(svg_data)).getroot()
    except ET.ParseError as e:
        logging.error(f"Failed to parse SVG file: {svg_path}, error: {e}")
        return None, None

    width_str = svg_root.attrib.get("width", "0")
    height_str = svg_root.attrib.get("height", "0")

    width = float(re.sub(r'[^\d.]+', '', width_str))
    height = float(re.sub(r'[^\d.]+', '', height_str))
    glyph_name = Path(svg_path).stem

    pen = RecordingPen()
    pen.width = width
    pen.height = height

    svg_path_d = svg_root.find(".//{http://www.w3.org/2000/svg}path").attrib.get("d")
    if svg_path_d:
        parse_svg_path(svg_path_d, pen)
    else:
        logging.error(f"No 'd' attribute found in SVG path for file: {svg_path}")
        return None, glyph_name

    return pen.value, glyph_name

def parse_svg_path(svg_path_d, pen):
    commands = svg_path_d.split()
    current_pos = (0, 0)
    prev_ctrl_point = None

    for command in commands:
        if command.isalpha():
            cmd = command.upper()
            args = []

            while len(args) < 6 and commands:
                next_arg = commands.pop(0)
                if next_arg.replace('.', '', 1).isdigit():
                    args.append(float(next_arg))

            if cmd == 'M':
                pen.moveTo((args[0], args[1]))
                current_pos = (args[0], args[1])
                prev_ctrl_point = None
            elif cmd == 'L':
                pen.lineTo((args[0], args[1]))
                current_pos = (args[0], args[1])
                prev_ctrl_point = None
            elif cmd == 'Q':
                pen.qCurveTo((args[0], args[1]), (args[2], args[3]))
                current_pos = (args[2], args[3])
                prev_ctrl_point = (args[0], args[1])
            elif cmd == 'C':
                pen.curveTo((args[0], args[1]), (args[2], args[3]), (args[4], args[5]))
                current_pos = (args[4], args[5])
                prev_ctrl_point = (args[2], args[3])
            elif cmd == 'Z':
                pen.closePath()

def create_font(svg_paths, output_font_path):
    font = TTFont()

    for svg_path in svg_paths:
        glyph_data, glyph_name = svg_to_glyph(svg_path)
        if glyph_data:
            font.getGlyphSet()[glyph_name] = GlyphCoordinates(glyph_data)
        else:
            logging.error(f"Failed to create glyph data for file: {svg_path}")

    output_font_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        font.save(output_font_path)
    except Exception as e:
        logging.error(f"Failed to save font: {e}")

svg_directory = Path("data/derge_img/svg")  
output_font_path = Path("data/derge_img/ttf/Derge_font.ttf")  # output font file path



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

                            svg_files = list(svg_directory.glob("*.svg"))
                            create_font(svg_files, output_font_path)


                        except Exception as e:
                            logging.error(f"Error processing image {line['image']}: {e}")
                            traceback.print_exc()
        except Exception as e:
            logging.error(f"Error processing {jsonl_path}: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
