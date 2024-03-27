import os
import filecmp

def find_duplicates(directory_path):
    files = [os.path.join(directory_path, f) for f in os.listdir(directory_path) if f.endswith('.svg')]
    duplicates = []
    while files:
        current_file = files.pop()
        for file in files:
            if filecmp.cmp(current_file, file, shallow=False):
                duplicates.append((current_file, file))
    return duplicates

duplicates = find_duplicates('C:/Users/tenka/monlam/create-font-from-glyph/test-create-font-from-glyph/create_font_from_glyph/data/derge_img/svg')
for file1, file2 in duplicates:
    print(f"Duplicate files: {file1} and {file2}")
