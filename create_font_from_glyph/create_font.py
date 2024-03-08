from pathlib import Path
from config import MONLAM_AI_OCR_BUCKET, monlam_ai_ocr_s3_client
from PIL import Image, ImageDraw
import urllib.parse
import os
import svgwrite
import base64
from PIL import Image, ImageFont, ImageOps
from fontTools.ufoLib import UFOWriter
from fontTools.ttLib import TTFont
from fontTools.pens.ttGlyphPen import TTGlyphPen
import numpy as np
import jsonlines
import logging
import traceback
import re
import cv2

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
    image_width = cleaned_image.width
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
    print(image_width)
    return image_output_path


# for left and right edges

def get_edges(cleaned_image):
    if cleaned_image.mode != '1':
        cleaned_image =cleaned_image.convert('1')
    image_array = np.array(cleaned_image)
    image_array = image_array[:, 1:-1]
    black_pixels = np.where(image_array == 0) 
    if black_pixels[0].size == 0 or black_pixels[1].size == 0:
        return None, None

    left_edge = np.min(black_pixels[1]) + 1
    right_edge = np.max(black_pixels[1]) + 1
    print(f"Left edge: {left_edge}, Right edge: {right_edge}")
    return left_edge, right_edge


# for headlines


def get_headlines(baselines_coord):
    min_x = min(coord[0] for coord in baselines_coord)
    max_x = max(coord[0] for coord in baselines_coord)
    headlines = {
        "headline_starts": min_x,
        "headline_ends": max_x
    }
    print(headlines)
    return headlines

from PIL import Image, ImageDraw

# --function to process the image-- 
# 1.convert outside of poly to white
# 2.turn the background transparent
# 3.apply anti aliasing/ yet

def png_process(png_image_path, span, cleaned_output_path):
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
    cleaned_output_path = get_image_output_path(cleaned_image, png_image_path.split('/')[-1], cleaned_output_path, headlines)

    if cleaned_output_path is not None:
        cleaned_image = cleaned_image.convert("RGBA")  # convert white regions to transparent
        data = cleaned_image.getdata()
        newData = []
        for item in data:
            if item[0] == 255 and item[1] == 255 and item[2] == 255:
                newData.append((255, 255, 255, 0))
            else:
                newData.append(item)
        cleaned_image.putdata(newData)
        cleaned_image.save(cleaned_output_path)
        return cleaned_output_path
    else:
        return None



def find_glyph_bbox(image):
    gray_image = image.convert('L')
    binary_image = gray_image.point(lambda p: p < 128 and 255)
    bbox = binary_image.getbbox()
    return bbox

# convert png to svg


def create_svg_with_glyph(png_path, output_svg_path, scale_factor=10):
    with Image.open(png_path) as img:
        bbox = find_glyph_bbox(img)

        if bbox is None:
            raise ValueError("No glyph found in the image.")

        left, upper, right, lower = bbox
        with open(png_path, "rb") as f:
            png_base64 = base64.b64encode(f.read()).decode('utf-8')

        width = (right - left) * scale_factor
        height = (lower - upper) * scale_factor

        dwg = svgwrite.Drawing(output_svg_path, profile='tiny', size=(f'{width}px', f'{height}px'))
        image = svgwrite.image.Image(href=f'data:image/png;base64,{png_base64}')
        image['x'] = f'0px'
        image['y'] = f'0px'
        image['width'] = f'{width}px'
        image['height'] = f'{height}px'
        dwg.add(image)
        dwg.save()


# assing unicode / yet to write
# create font into desired format / yet to write


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
                                png_image_path, image_span, Path(f"data/derge_img/cleaned_images"))
                            if cleaned_image_path is None:
                                logging.info(f"Skipping {png_image_path}")
                                continue
                            filename = (cleaned_image_path.split("/")[-1]).split(".")[0]
                            output_path = Path(f"data/derge_img/svg/{filename}.svg")
                            create_svg_with_glyph(cleaned_image_path, output_path)

                        except Exception as e:
                            logging.error(f"Error processing image {line['image']}: {e}")
                            traceback.print_exc()
        except Exception as e:
            logging.error(f"Error processing {jsonl_path}: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
