from pathlib import Path
from config import MONLAM_AI_OCR_BUCKET, monlam_ai_ocr_s3_client
from PIL import Image, ImageDraw
import subprocess
import urllib.parse
import os
import svgwrite
import base64
from PIL import Image, ImageFont
from fontTools.ufoLib import UFOWriter
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
import numpy as np
import jsonlines
import logging
import traceback

s3 = monlam_ai_ocr_s3_client
bucket_name = MONLAM_AI_OCR_BUCKET

logging.basicConfig(filename='skipped_glyph.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

# convert png to svg


def png_to_svg(input_png, output_svg):
    image = Image.open(input_png).convert('1')
    pbm_path = "temp.pbm"
    image.save(pbm_path)
    subprocess.run(["potrace", pbm_path, "-s", "--scale", "5.5", "-o", output_svg])
    os.remove(pbm_path)

# get image path from url


def get_image_path(image_url):
    image_parts = (image_url.split("?")[0]).split("/")
    obj_key = "/".join(image_parts[4:])
    decoded_key = urllib.parse.unquote(obj_key)
    image_name = decoded_key.split("/")[-1]

    try:
        response = s3.get_object(Bucket=bucket_name, Key=decoded_key)  # download the image from the bucket
        image_data = response['Body'].read()
        with open(fr"data/downloaded_glyph/{image_name}", 'wb') as f:
            f.write(image_data)

    except Exception as e:
        print(fr"Error while downloading {image_name} due to {e}")
    return fr"data/downloaded_glyph/{image_name}"

# convert outside polygon to white


def convert_outside_polygon_to_white(image_path, span, output_path):
    baselines_coord = None
    polygon_points = None
    for info in span:
        if info["label"] == "Base Line":
            baselines_coord = info["points"]
        if info["label"] == "Glyph":
            polygon_points = [(x, y) for x, y in info["points"]]
    if baselines_coord == None or polygon_points == None:
        return None
    image = Image.open(image_path)
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(polygon_points, fill=255)
    result_image = Image.new("RGB", image.size, (255, 255, 255))
    result_image.paste(image, mask=mask)
    headlines = get_headlines(baselines_coord)
    image_output_path = f"{output_path}/{image_path.split('/')[-1]}"
    if image_output_path is not None:
        result_image.save(image_output_path)
        return image_output_path

# for headlines


def get_headlines(baselines_coord):
    min_x = min(coord[0] for coord in baselines_coord)
    max_x = max(coord[0] for coord in baselines_coord)
    headlines = {
        "top_left_x": min_x,
        "top_right_x": max_x
    }
    return headlines

# for left and right edges


def get_edges(image):
    if image.mode != 'L':
        image = image.convert('L')
    image_array = np.array(image)
    left_edge = None
    right_edge = None
    for x in range(image_array.shape[1]):
        for y in range(image_array.shape[0]):
            if image_array[y, x] == 0:
                left_edge = x
                break
        if left_edge is not None:
            break
    for x in range(image_array.shape[1] - 1, -1, -1):
        for y in range(image_array.shape[0]):
            if image_array[y, x] == 0:
                right_edge = x
                break
        if right_edge is not None:
            break
    return left_edge, right_edge

# finding the bounding box


def find_glyph_bbox(image):
    gray_image = image.convert('L')
    pixels = gray_image.load()
    width, height = image.size
    left, upper, right, lower = width, height, 0, 0
    for y in range(height):
        for x in range(width):
            if pixels[x, y] != 255:
                left = min(left, x)
                upper = min(upper, y)
                right = max(right, x)
                lower = max(lower, y)
    return left, upper, right + 1, lower + 1

# create sgv


def create_svg_with_glyph(png_path, output_svg_path):
    try:
        with Image.open(png_path) as img:
            width, height = img.size
            left, upper, right, lower = find_glyph_bbox(img)
            png_base64 = base64.b64encode(img.tobytes()).decode('utf-8')
            dwg = svgwrite.Drawing(output_svg_path, profile='tiny', size=(f'{width}px', f'{height}px'))
            image = svgwrite.image.Image(href=f'data:image/png;base64,{png_base64}')
            image['x'] = f'{left}px'
            image['y'] = f'{upper}px'
            image['width'] = f'{right - left}px'
            image['height'] = f'{lower - upper}px'
            dwg.add(image)
            dwg.save()
    except Exception as e:
        print(f"Error creating SVG with glyph: {e}")

# create font into desired format


def create_into_desired_format(cleaned_image_path):
    try:
        image_name = os.path.basename(cleaned_image_path)
        input_dir = "data/cleaned_images"
        output_ufo = f"data/ufo/{image_name}.ufo"
        output_ttf = f"data/ttf/{image_name}.ttf"
        font_file = "data/font/font.ttf"
        font_size = 12
        font_name = "My Font"

        font = UFOWriter(font_file)
        ttf_font = ImageFont.truetype(font_file, font_size)

        for filename in os.listdir(input_dir):
            if filename.endswith(".png"):
                unicode_value, width, lsb, rsb = filename[:-4].split("-")
                unicode_value = int(unicode_value, 16)
                width = int(width)
                lsb = int(lsb)
                rsb = int(rsb)
                image = Image.open(os.path.join(input_dir, filename))
                glyph_pen = TTGlyphPen(font)
                glyph_pen.moveTo((0, 0))
                glyph_pen.lineTo((width, 0))
                glyph_pen.lineTo((width, image.height))
                glyph_pen.lineTo((0, image.height))
                glyph_pen.closePath()
                glyph = glyph_pen.glyph()
                glyph.width = width
                glyph.leftMargin = lsb
                glyph.rightMargin = rsb
                glyph.font = font_name
                glyph.font_size = font_size
                font.newGlyph(hex(unicode_value)[2:].upper())
                font.glyphs[hex(unicode_value)[2:].upper()].fromTTGlyph(glyph)

        ttf_font_metadata = {"name": {"fontFamily": font_name}}
        ttf_font.set(**ttf_font_metadata)

        font.writeToFile(output_ufo)
        ttf_font = TTFont(output_ufo)
        ttf_font.save(output_ttf)

        print(f"Font created successfully: {output_ttf}")

    except Exception as e:
        print(f"Error creating font: {e}")


def main():
    jsonl_paths = list(Path("derge/glyph_ann_reviewed_batch6_ga").iterdir())
    for jsonl_path in jsonl_paths:
        try:
            with jsonlines.open(jsonl_path) as reader:
                for line in reader:
                    if line["answer"] == "accept":
                        try:
                            image_span = line["spans"]
                            image_path = get_image_path(line["image"])
                            cleaned_image_path = convert_outside_polygon_to_white(
                                image_path, image_span, Path(f"data/cleaned_images"))
                            if cleaned_image_path is None:
                                logging.info(f"Skipping {image_path}")
                                continue
                            filename = Path(cleaned_image_path).stem
                            output_path = Path(f"data/glyph_images/{filename}.svg")
                            png_to_svg(cleaned_image_path, output_path)
                        except Exception as e:
                            logging.error(f"Error processing image {line['image']}: {e}")
                            traceback.print_exc()
        except Exception as e:
            logging.error(f"Error processing {jsonl_path}: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
