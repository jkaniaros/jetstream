import shutil
import os
import time
from helper.file_downloader import download_all_files
from helper.zip_extractor import extract_all_product_txt_files
from helper.kafka_publisher import publish_folder, create_topic, publish_file
from helper.file_merge import merge_files_by_regex
from kafka.admin import KafkaAdminClient, NewTopic
from kafka import KafkaClient

# Download URL of the DWDs for 10-minutely wind data, which is updated probably every 30 minutes and contains data from 1 day
DOWNLOAD_URL = "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/wind/now/" 
# "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly/wind/recent/"


# File in the weather station zip file that contains the wind data. The rest only has metadata
EXTRACT_REGEX = r"^produkt_zehn_now_ff_.*.txt$" # r"^produkt_ff_stunde_\w*\.txt$"

DOWNLOAD_FOLDER = os.path.join("tmp", "downloaded")
EXTRACTED_FOLDER = os.path.join("tmp", "extracted")
MERGED_FOLDER = os.path.join("tmp", "merged")
ARCHIVED_FOLDER = os.path.join("tmp", "archived")

DESCRIPTION_FILE = "zehn_now_ff_Beschreibung_Stationen.txt"

KAFKA_TOPIC = "jetstream"
TOPIC_KEY_REGEX = r"_(\d+)\.txt$"
KAFKA_DESCRIPTION_TOPIC = "jetstream-description"
# "FF_Stundenwerte_Beschreibung_Stationen.txt"

KAFKA_BROKER = os.environ.get("KAFKA_BROKER")
print(f"Kafka Broker: {KAFKA_BROKER}")

LOOP_WAIT_TIME = 30  # Time to wait between iterations (in seconds)

def run():
    """
    Endless loop entrypoint. Downloads all files from the file server, extracts relevant txt files,
    processes data, and publishes to Kafka. Loops indefinitely with a waiting time in between the iterations.
    """
    max_run_ts = None  # Start with no timestamp

    # Create topics if they don't exist, so that the spark applications don't crash because of missing topics
    create_topic(KAFKA_TOPIC, KAFKA_BROKER)
    create_topic(KAFKA_DESCRIPTION_TOPIC, KAFKA_BROKER)


    while True:
        print("Stating new iteration...")

        # Download zip files from DWD and extract the relevant txt files
        _, max_run_ts = download_all_files(DOWNLOAD_URL, DOWNLOAD_FOLDER, max_run_ts)
        extract_all_product_txt_files(DOWNLOAD_FOLDER, EXTRACT_REGEX, EXTRACTED_FOLDER)

        # If a station description file exists, copy it to the extracted folder too
        if os.path.exists(os.path.join(DOWNLOAD_FOLDER, DESCRIPTION_FILE)):
            shutil.copy2(os.path.join(DOWNLOAD_FOLDER, DESCRIPTION_FILE), EXTRACTED_FOLDER)

        # If a station description file exists in the extracted folder, publish it to the Kafka description topic
        if os.path.exists(os.path.join(EXTRACTED_FOLDER, DESCRIPTION_FILE)):
            publish_file(os.path.join(EXTRACTED_FOLDER, DESCRIPTION_FILE),
                        KAFKA_BROKER, KAFKA_DESCRIPTION_TOPIC, None)

        # Merge all txt files for one station into one single file in the merge folder
        merge_files_by_regex(EXTRACTED_FOLDER, MERGED_FOLDER, TOPIC_KEY_REGEX, ARCHIVED_FOLDER)

        # Publish all extracted files to Kafka
        publish_folder(MERGED_FOLDER, KAFKA_BROKER, KAFKA_TOPIC, TOPIC_KEY_REGEX, ARCHIVED_FOLDER)

        # Remove the temporary folders, except for archive
        if os.path.exists(DOWNLOAD_FOLDER):
            shutil.rmtree(DOWNLOAD_FOLDER)
        if os.path.exists(EXTRACTED_FOLDER):
            shutil.rmtree(EXTRACTED_FOLDER)
        if os.path.exists(MERGED_FOLDER):
            shutil.rmtree(MERGED_FOLDER)

        print(f"Finishing iteration, waiting {LOOP_WAIT_TIME} seconds")

        # Wait for a defined interval before the next run
        time.sleep(LOOP_WAIT_TIME)

if __name__ == "__main__":
    run()
