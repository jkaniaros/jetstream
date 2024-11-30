import zipfile
import os
import re

def extract_file_from_zip(zip_filepath, extract_file_regex, output_folder):
    """
    Function to extract files specified by regex from a zip archive.
    
    Parameters:
    zip_filepath (str): The filepath where the zip archive is stored.
    extract_file_regex (str): The regex string for the files to be extracted.
    output_folder (str): The folder where the extracted files should be saved.
    """

    # Return if the zip archive does not exist
    if not os.path.exists(zip_filepath):
        return
    
    # Create output folder if it doesn"t exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Open the zip file
    with zipfile.ZipFile(zip_filepath, "r") as zip_ref:
        # Check if the desired file exists in the zip archive
        file_list = zip_ref.namelist()
        
        pattern = re.compile(extract_file_regex)
        
        # Iterate through all the files in the zip archive and search for the regex
        for file in file_list:
            if pattern.search(file):#  and not os.path.exists(os.path.join(output_folder, file)):
                # Extract the file
                zip_ref.extract(file, output_folder)
                print(f"Extracted: {file} to {output_folder}")

def extract_all_product_txt_files(in_folder, extract_file_regex, out_folder):
    """
    Function to search all zip archives in a given folder for files specified by regex.
    
    Parameters:
    in_folder (str): The folder where the zip archives are stored.
    extract_file_regex (str): The regex string for the files to be extracted.
    out_folder (str): The folder where the extracted files should be saved.
    """

    # If the zip archives folder does not exist, return
    if not os.path.exists(in_folder):
        return
    
    # Iterate through all zip files and extract the matching files
    for file in os.listdir(in_folder):
        if file.endswith(".zip"):
            extract_file_from_zip(os.path.join(in_folder, file), extract_file_regex, out_folder)
