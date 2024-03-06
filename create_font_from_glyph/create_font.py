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
        with open(fr"data/downloaded_glyph/{image_name_tibetan_only}{file_extension}", 'wb') as f:
            f.write(image_data)

    except Exception as e:
        print(fr"Error while downloading {image_name} due to {e}")
    return fr"data/downloaded_glyph/{image_name_tibetan_only}{file_extension}"




def get_image_output_path(image, image_name, output_path, headlines):
    image_width = image.width
    headline_starts = headlines["headline_starts"]
    headline_ends = headlines["headline_ends"]

    glyph_name = (image_name.split(".")[0]).split("_")[0]

    left_edge, right_edge = get_edges(image)
    if left_edge is None:
        return None
    # <Unicode>-<PNG width - margins>_<baseline start - left glyph edge>_<right glyph edge - baseline end>.png
    new_image_name = f"{glyph_name}_{int(image_width - (left_edge + right_edge))}_{int(headline_starts - left_edge)}_{int(headline_ends - right_edge)}.png"
    print(new_image_name)
    image_output_path = f"{output_path}/{new_image_name}"
    print(image_width)
    return image_output_path

# for left and right edges
def get_edges(image):
    if isinstance(image, np.ndarray):  
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif isinstance(image, Image.Image): 
        if image.mode != 'L':
            image = image.convert('L')
        gray_image = np.array(image)
    else:
        raise ValueError("Unsupported image type")

    edges = cv2.Canny(gray_image, 50, 150) 
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    left_edge = min(contours[0][:, 0, 0]) if contours else None
    right_edge = max(contours[0][:, 0, 0]) if contours else None
    print(left_edge,right_edge)
    
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


def convert_outside_polygon_to_white(image_path, span, output_path):
    baselines_coord = None
    polygon_points = None
    for info in span:
        if info["label"] == "Base Line":
            baselines_coord = info["points"]
        if info["label"] == "Glyph":
            polygon_points = [(x, y) for x, y in info["points"]]
    if baselines_coord is None or polygon_points is None:
        return None

    image = Image.open(image_path)
    mask = Image.new("L", image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(polygon_points, fill=255)
    result_image = Image.new("RGB", image.size, (255, 255, 255))
    result_image.paste(image, mask=mask)

    headlines = get_headlines(baselines_coord)
    image_output_path = get_image_output_path(image, image_path.split('/')[-1], output_path, headlines)

    if image_output_path is not None:
        result_image.save(image_output_path)
        return image_output_path
    else:
        return None


def find_glyph_bbox(image):
    gray_image = image.convert('L')
    binary_image = gray_image.point(lambda p: p < 128 and 255)
    bbox = binary_image.getbbox()
    return bbox

# convert png to svg
def create_svg_with_glyph(png_path, output_svg_path):
    with Image.open(png_path) as img:
        bbox = find_glyph_bbox(img)
        
        if bbox is None:
            raise ValueError("No glyph found in the image.")

        left, upper, right, lower = bbox
        with open(png_path, "rb") as f:
            png_base64 = base64.b64encode(f.read()).decode('utf-8')

        dwg = svgwrite.Drawing(output_svg_path, profile='tiny', size=(f'{right - left}px', f'{lower - upper}px'))
        image = svgwrite.image.Image(href=f'data:image/png;base64,{png_base64}')
        image['x'] = f'0px'
        image['y'] = f'0px'
        image['width'] = f'{right - left}px'
        image['height'] = f'{lower - upper}px'
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
                            image_path = get_image_path(line["image"])
                            cleaned_image_path = convert_outside_polygon_to_white(
                                image_path, image_span, Path(f"data/cleaned_images"))
                            if cleaned_image_path is None:
                                logging.info(f"Skipping {image_path}")
                                continue
                            filename = (cleaned_image_path.split("/")[-1]).split(".")[0]
                            output_path = Path(f"data/svg/{filename}.svg")
                            create_svg_with_glyph(cleaned_image_path, output_path)

                        except Exception as e:
                            logging.error(f"Error processing image {line['image']}: {e}")
                            traceback.print_exc()
        except Exception as e:
            logging.error(f"Error processing {jsonl_path}: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
