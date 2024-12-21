from helper.file_downloader import download_all_files
from helper.zip_extractor import extract_all_product_txt_files
from helper.kafka_publisher import publish_staged, create_topic, publish_file
import shutil
import os
from kafka.admin import KafkaAdminClient, NewTopic
from kafka import KafkaClient

# Download URL of the DWDs for hourly wind data
DOWNLOAD_URL = "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly/wind/recent/"
DOWNLOAD_FOLDER = os.path.join("tmp", "input")

# File in the weather station zip file that contains the wind data. The rest only has metadata
EXTRACT_REGEX = r"^produkt_ff_stunde_\w*\.txt$"
STAGED_FOLDER = os.path.join("tmp", "staged")
KAFKA_TOPIC = "jetstream"
TOPIC_KEY_REGEX = r"_(\d+)\.txt$"

KAFKA_DESCRIPTION_TOPIC = "jetstream-description"
DESCRIPTION_FILE = "FF_Stundenwerte_Beschreibung_Stationen.txt"

KAFKA_BROKER = os.environ.get("KAFKA_BROKER")
print(f"Kafka Broker: {KAFKA_BROKER}")

def run():
    """
    Data generation entrypoint. Downloads all files from the file server and extract all zip files to `tmp/staged`
    """
    ### shutil.rmtree("tmp")
    
    # Create topics if they don't exist, so that the spark applications don't crash because of missing topics
    create_topic(KAFKA_TOPIC, KAFKA_BROKER)
    create_topic(KAFKA_DESCRIPTION_TOPIC, KAFKA_BROKER)
    
    # Download zip files from DWD and extract the relevant txt files
    download_all_files(DOWNLOAD_URL, DOWNLOAD_FOLDER)
    extract_all_product_txt_files(DOWNLOAD_FOLDER, EXTRACT_REGEX, STAGED_FOLDER)
    
    # If a station description file exists, copy it to the staged folder too
    if os.path.exists(os.path.join(DOWNLOAD_FOLDER, DESCRIPTION_FILE)):
        shutil.copy2(os.path.join(DOWNLOAD_FOLDER, DESCRIPTION_FILE), STAGED_FOLDER)
    
    
    if os.path.exists(os.path.join(STAGED_FOLDER, DESCRIPTION_FILE)):
        publish_file(os.path.join(STAGED_FOLDER, DESCRIPTION_FILE), KAFKA_BROKER, KAFKA_DESCRIPTION_TOPIC)
    
    # Publish all extracted files to Kafka
    publish_staged(STAGED_FOLDER, KAFKA_BROKER, KAFKA_TOPIC, TOPIC_KEY_REGEX)
    
    # Remove the temporary zip download folder
    if os.path.exists(DOWNLOAD_FOLDER):
        shutil.rmtree(DOWNLOAD_FOLDER)


if __name__ == "__main__":
    run()