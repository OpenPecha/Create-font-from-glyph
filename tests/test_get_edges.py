import numpy as np
from PIL import Image

def get_edges(image):
    if image.mode != '1':
        image = image.convert('1')
    image_array = np.array(image)
    image_array = image_array[:, 1:-1]
    black_pixels = np.where(image_array == 0) 
    if black_pixels[0].size == 0 or black_pixels[1].size == 0:
        return None, None

    left_edge = np.min(black_pixels[1]) + 1
    right_edge = np.max(black_pixels[1]) + 1
    print(f"Left edge: {left_edge}, Right edge: {right_edge}")
    return left_edge, right_edge

if __name__ == "__main__":
    # Example usage
    image_path = "ཀ_159_65_67.png"  # Provide your image path here
    image = Image.open(image_path)
    left_edge, right_edge = get_edges(image)
    if left_edge is not None and right_edge is not None:
        print("Edges found successfully.")
    else:
        print("No edges found.")
