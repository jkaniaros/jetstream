from helper.file_downloader import download_all_files
from helper.zip_extractor import extract_all_product_txt_files
import shutil
import os

# Download URL of the DWDs for hourly wind data
DOWNLOAD_URL = "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly/wind/recent/"
DOWNLOAD_FOLDER = os.path.join("tmp", "input")

# File in the weather station zip file that contains the wind data. The rest only has metadata
EXTRACT_REGEX = r"^produkt_ff_stunde_\w*\.txt$"
STAGED_FOLDER = os.path.join("tmp", "staged")

DESCRIPTION_FILE = os.path.join(DOWNLOAD_FOLDER, "FF_Stundenwerte_Beschreibung_Stationen.txt")

def run():
    """
    Data generation entrypoint. Downloads all files from the file server and extract all zip files to `tmp/staged`
    """
    ### shutil.rmtree("tmp")
    
    download_all_files(DOWNLOAD_URL, DOWNLOAD_FOLDER)
    extract_all_product_txt_files(DOWNLOAD_FOLDER, EXTRACT_REGEX, STAGED_FOLDER)
    
    # If a station description file exists, copy it to the staged folder too
    if os.path.exists(DESCRIPTION_FILE):
        shutil.copy2(DESCRIPTION_FILE, STAGED_FOLDER)
    
    # Remove the temporary zip download folder
    shutil.rmtree(DOWNLOAD_FOLDER)


if __name__ == "__main__":
    run()