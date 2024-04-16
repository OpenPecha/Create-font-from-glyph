import os

directory_path = "../../data/shul_font/svg"

files_list = os.listdir(directory_path)

tibetan_names = [file.split('_')[0] for file in files_list]

output_file = "../../data/shul_font/shul_present_tibetan_glyphs.txt"
with open(output_file, 'w', encoding='utf-8') as f:
    for name in tibetan_names:
        f.write(name + '\n')

print('list saved')
