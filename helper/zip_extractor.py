import zipfile
import os
import re

def extract_file_from_zip(zip_filepath, extract_file_regex, output_folder):
    """
    Helper function to extract a file from a zip archive
    """
    if not os.path.exists(zip_filepath):
        return
    
    # create output folder if it doesn"t exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # open the zip file
    with zipfile.ZipFile(zip_filepath, "r") as zip_ref:
        # check if the desired file exists in the zip archive
        file_list = zip_ref.namelist()
        
        pattern = re.compile(extract_file_regex)
        
        for file in file_list:
            if pattern.search(file) and not os.path.exists(os.path.join(output_folder, file)):
                # extract the file
                zip_ref.extract(file, output_folder)
                print(f"Extracted: {file} to {output_folder}")

def extract_all_product_txt_files(in_folder, extract_file_regex, out_folder):
    if not os.path.exists(in_folder):
        return
    
    for file in os.listdir(in_folder):
        if file.endswith(".zip"):
            extract_file_from_zip(os.path.join(in_folder, file), extract_file_regex, out_folder)
