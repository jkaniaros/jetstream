from helper.file_downloader import download_all_files
from helper.zip_extractor import extract_all_product_txt_files
import shutil

DOWNLOAD_URL = "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly/wind/recent/"
DOWNLOAD_FOLDER = "tmp/input"

EXTRACT_REGEX = r"^produkt_ff_stunde_\w*\.txt$"
STAGED_FOLDER = "tmp/staged"

def run():
    ### shutil.rmtree("tmp")
    
    download_all_files(DOWNLOAD_URL, DOWNLOAD_FOLDER)
    extract_all_product_txt_files(DOWNLOAD_FOLDER, EXTRACT_REGEX, STAGED_FOLDER)
    
    shutil.rmtree(DOWNLOAD_FOLDER)


if __name__ == "__main__":
    run()