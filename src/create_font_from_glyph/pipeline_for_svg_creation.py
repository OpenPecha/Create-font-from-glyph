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

s3 = monlam_ai_ocr_s3_client
bucket_name = MONLAM_AI_OCR_BUCKET

logging.basicConfig(filename='skipped_glyph.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

downloaded_images_dir = "../../data/pecing_font/Pecing_test_10_glyphs/downloaded_images"
cleaned_images_dir = "../../data/pecing_font/Pecing_test_10_glyphs/cleaned_images"
svg_dir = "../../data/pecing_font/Pecing_test_10_glyphs/svg"
jsonl_dir = "../../data/pecing_annotations/all_pecing_batches"

def download_image(image_url):
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
        with open(os.path.join(downloaded_images_dir, f"{image_name_tibetan_only}{file_extension}"), 'wb') as f:
            f.write(image_data)
    except Exception as e:
        print(f"Error while downloading {image_name}: {e}")
    return os.path.join(downloaded_images_dir, f"{image_name_tibetan_only}{file_extension}")

# Define output image path
def get_image_output_path(cleaned_image, image_name, output_path, headlines):
    headline_starts = headlines["headline_starts"]
    headline_ends = headlines["headline_ends"]
    glyph_name = image_name.split(".")[0].split("_")[0]

    left_edge, right_edge = get_edges(cleaned_image)
    if left_edge is None:
        return None

    new_image_name = f"{glyph_name}_{int(right_edge - left_edge)}_{int(headline_starts - left_edge)}_{int(right_edge - headline_ends)}.png"
    image_output_path = os.path.join(output_path, new_image_name)
    return image_output_path

# Define edge calculation function
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

# Define headlines calculation function
def get_headlines(baselines_coord):
    min_x = min(coord[0] for coord in baselines_coord)
    max_x = max(coord[0] for coord in baselines_coord)
    headlines = {
        "headline_starts": min_x,
        "headline_ends": max_x
    }
    return headlines

# Define PNG processing function
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
        cleaned_image, os.path.basename(png_image_path), cleaned_image_path, headlines)

    if cleaned_image_path is not None:
        cleaned_image = cleaned_image.convert("RGBA") 
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

# Define bounding box calculation function
def find_glyph_bbox(image):
    gray_image = image.convert('L')
    binary_image = gray_image.point(lambda p: p < 128 and 255)
    bbox = binary_image.getbbox()
    return bbox

# Define PNG to SVG conversion function
def png_to_svg(cleaned_image_path, svg_output_path):
    image = Image.open(cleaned_image_path).convert('1')
    pbm_path = "temp.pbm"
    image.save(pbm_path)
    sanitized_filename = re.sub('[^A-Za-z0-9_.]+', '', Path(cleaned_image_path).stem)

    temp_svg_output_path = Path(f"{svg_dir}/{sanitized_filename}.svg")

    subprocess.run(["potrace", pbm_path, "-s", "--scale", "5.5", "-o", temp_svg_output_path])
    os.remove(pbm_path)

    if os.path.exists(svg_output_path):
        os.remove(svg_output_path)
    os.rename(temp_svg_output_path, svg_output_path)

def main():
    jsonl_paths = list(Path(jsonl_dir).iterdir())
    processed_ids = {}
    for jsonl_path in jsonl_paths:
        try:
            with jsonlines.open(jsonl_path) as reader:
                for line in reader:
                    if line["answer"] == "accept":
                        try:
                            image_id = line["id"].split("_")[0]
                            if image_id in processed_ids:
                                if processed_ids[image_id] >= 10:
                                    logging.info(f"Skipping duplicate ID: {image_id}")
                                    continue
                                else:
                                    processed_ids[image_id] += 1
                            else:
                                processed_ids[image_id] = 1
                            image_span = line["spans"]
                            png_image_path = download_image(line["image"])

                            cleaned_image_path = png_process(
                                png_image_path, image_span, cleaned_images_dir)

                            if cleaned_image_path is None:
                                logging.info(f"Skipping {png_image_path}")
                                continue
                            filename = os.path.basename(cleaned_image_path)
                            svg_output_path = Path(f"{svg_dir}/{Path(filename).stem}.svg")
                            png_to_svg(cleaned_image_path, svg_output_path)

                        except Exception as e:
                            logging.error(f"Error processing image {line['image']}: {e}")
                            traceback.print_exc()
        except Exception as e:
            logging.error(f"Error processing {jsonl_path}: {e}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()

