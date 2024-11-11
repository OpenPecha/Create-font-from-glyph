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
import csv

s3 = monlam_ai_ocr_s3_client
bucket_name = MONLAM_AI_OCR_BUCKET

logging.basicConfig(filename='skipped_glyph.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s')

def download_image(image_url, downloaded_images_dir):
    image_parts = image_url.split("?")[0].split("/")
    obj_key = "/".join(image_parts[4:])
    decoded_key = urllib.parse.unquote(obj_key)
    image_name = decoded_key.split("/")[-1]
    file_name, file_extension = os.path.splitext(image_name)
    image_name_without_suffix = re.sub(r'(_\d+)$', '', file_name)
    image_name_tibetan_only = re.sub(r'[^\u0F00-\u0FFF]', '', image_name_without_suffix)
    file_path = os.path.join(downloaded_images_dir, f"{image_name_tibetan_only}{file_extension}")

    try:
        response = s3.get_object(Bucket=bucket_name, Key=decoded_key)
        image_data = response['Body'].read()
        with open(file_path, 'wb') as f:
            f.write(image_data)
    except Exception as e:
        logging.error(f"Error while downloading {image_name}: {e}")

    return file_path

def get_image_output_path(cleaned_image, image_name, output_path, headlines):
    left_edge, right_edge = get_edges(cleaned_image)
    if left_edge is None:
        return None, None, None, None

    width = int(right_edge - left_edge)
    lsb = int(headlines["headline_starts"] - left_edge)
    rsb = int(right_edge - headlines["headline_ends"])

    glyph_name = image_name.split(".")[0].split("_")[0]
    new_image_name = f"{glyph_name}_{width}_{lsb}_{rsb}.png"
    image_output_path = os.path.join(output_path, new_image_name)

    return image_output_path, width, lsb, rsb

def get_edges(cleaned_image):
    if cleaned_image.mode != '1':
        cleaned_image = cleaned_image.convert('1')
    image_array = np.array(cleaned_image)[:, 1:-1]
    black_pixels = np.where(image_array == 0)
    if black_pixels[0].size == 0 or black_pixels[1].size == 0:
        return None, None

    left_edge = np.min(black_pixels[1]) + 1
    right_edge = np.max(black_pixels[1]) + 1
    return left_edge, right_edge

def get_headlines(baselines_coord):
    min_x = min(coord[0] for coord in baselines_coord)
    max_x = max(coord[0] for coord in baselines_coord)
    return {
        "headline_starts": min_x,
        "headline_ends": max_x
    }

def png_process(png_image_path, span, cleaned_image_path):
    baselines_coord = next((info["points"] for info in span if info["label"] == "Base Line"), None)
    polygon_points = next(((x, y) for info in span if info["label"] == "Glyph" for x, y in info["points"]), None)
    if baselines_coord is None or polygon_points is None:
        return None, None, None, None

    image = Image.open(png_image_path)
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).polygon(polygon_points, fill=255)
    cleaned_image = Image.new("RGB", image.size, (255, 255, 255))
    cleaned_image.paste(image, mask=mask)

    headlines = get_headlines(baselines_coord)
    cleaned_image_path, width, lsb, rsb = get_image_output_path(
        cleaned_image, os.path.basename(png_image_path), cleaned_image_path, headlines)

    if cleaned_image_path:
        cleaned_image = cleaned_image.convert("RGBA")
        data = cleaned_image.getdata()
        newData = [(255, 255, 255, 0) if item[:3] == (255, 255, 255) else item for item in data]
        cleaned_image.putdata(newData)
        cleaned_image.save(cleaned_image_path)
        return cleaned_image_path, width, lsb, rsb
    return None, None, None, None

def png_to_svg(cleaned_image_path, svg_output_path):
    image = Image.open(cleaned_image_path).convert('1')
    pbm_path = "temp.pbm"
    image.save(pbm_path)

    sanitized_filename = re.sub('[^A-Za-z0-9_.]+', '', Path(cleaned_image_path).stem)
    temp_svg_output_path = Path(f"{svg_output_path}/{sanitized_filename}.svg")

    subprocess.run(["potrace", pbm_path, "-s", "--scale", "5.5", "-o", temp_svg_output_path])
    os.remove(pbm_path)

    if os.path.exists(svg_output_path):
        os.remove(svg_output_path)
    os.rename(temp_svg_output_path, svg_output_path)

def process_jsonl_file(jsonl_path, writer, processed_ids, unique_base_ids, downloaded_images_dir, cleaned_images_dir, svg_dir):
    try:
        with jsonlines.open(jsonl_path) as reader:
            for line in reader:
                image_id = line["id"]
                base_id = image_id.split('_')[0]
                if '_' in image_id and base_id in unique_base_ids:
                    logging.info(f"Skipping duplicate base ID: {base_id}")
                    continue
                unique_base_ids.add(base_id)
                
                if base_id in processed_ids:
                    if processed_ids[base_id] >= 10:
                        logging.info(f"Skipping duplicate ID: {base_id}")
                        continue
                    processed_ids[base_id] += 1
                else:
                    processed_ids[base_id] = 1

                logging.info(f"Processing image ID: {image_id} (base ID: {base_id})")

                try:
                    image_span = line["spans"]
                    png_image_path = download_image(line["image"], downloaded_images_dir)
                    cleaned_image_path, width, lsb, rsb = png_process(png_image_path, image_span, cleaned_images_dir)

                    if cleaned_image_path is None:
                        logging.info(f"Skipping {png_image_path}")
                        continue

                    svg_output_path = Path(f"{svg_dir}/{Path(cleaned_image_path).stem}.svg")
                    png_to_svg(cleaned_image_path, svg_output_path)

                    rect_points = next((span["points"] for span in image_span if span["label"] == "Base Line"), None)

                    writer.writerow({
                        'id': line['id'],
                        'width': width,
                        'lsb': lsb,
                        'rsb': rsb,
                        'rect_points': rect_points
                    })

                except Exception as e:
                    logging.error(f"Error processing image {line['image']}: {e}")
                    traceback.print_exc()
    except Exception as e:
        logging.error(f"Error processing {jsonl_path}: {e}")

def main():
    downloaded_images_dir = "../../data/font_data/derge_font/variant_glyphs/downloaded_images"
    cleaned_images_dir = "../../data/font_data/derge_font/variant_glyphs/cleaned_images"
    svg_dir = "../../data/font_data/derge_font/variant_glyphs/svg"
    jsonl_dir = "../../data/annotation_data/derge_annotations/all_derge_batches"
    csv_output_path = "../../data/font_data/derge_font/variant_glyphs/mapping_csv/char_mapping.csv"

    jsonl_paths = list(Path(jsonl_dir).iterdir())
    processed_ids = {}
    unique_base_ids = set()

    with open(csv_output_path, mode='w', newline='') as csv_file:
        fieldnames = ['id', 'width', 'lsb', 'rsb', 'rect_points']
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()

        for jsonl_path in jsonl_paths:
            process_jsonl_file(jsonl_path, writer, processed_ids, unique_base_ids, downloaded_images_dir, cleaned_images_dir, svg_dir)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()