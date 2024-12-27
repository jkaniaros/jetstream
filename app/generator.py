import shutil
import os
import time
from helper.file_downloader import download_all_files
from helper.zip_extractor import extract_all_product_txt_files
from helper.kafka_publisher import publish_staged, create_topic, publish_file
from kafka.admin import KafkaAdminClient, NewTopic
from kafka import KafkaClient

# Download URL of the DWDs for hourly wind data
DOWNLOAD_URL = "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/wind/now/" 
# "https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly/wind/recent/"
DOWNLOAD_FOLDER = os.path.join("tmp", "input")

# File in the weather station zip file that contains the wind data. The rest only has metadata
EXTRACT_REGEX = r"^produkt_zehn_now_ff_.*.txt$" # r"^produkt_ff_stunde_\w*\.txt$"
STAGED_FOLDER = os.path.join("tmp", "staged")
KAFKA_TOPIC = "jetstream"
TOPIC_KEY_REGEX = r"_(\d+)\.txt$"

KAFKA_DESCRIPTION_TOPIC = "jetstream-description"
DESCRIPTION_FILE = "zehn_now_ff_Beschreibung_Stationen.txt"
# "FF_Stundenwerte_Beschreibung_Stationen.txt"

KAFKA_BROKER = os.environ.get("KAFKA_BROKER")
print(f"Kafka Broker: {KAFKA_BROKER}")

LOOP_WAIT_TIME = 10  # Time to wait between iterations (in seconds)

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
        extract_all_product_txt_files(DOWNLOAD_FOLDER, EXTRACT_REGEX, STAGED_FOLDER)

        # If a station description file exists, copy it to the staged folder too
        if os.path.exists(os.path.join(DOWNLOAD_FOLDER, DESCRIPTION_FILE)):
            shutil.copy2(os.path.join(DOWNLOAD_FOLDER, DESCRIPTION_FILE), STAGED_FOLDER)


        if os.path.exists(os.path.join(STAGED_FOLDER, DESCRIPTION_FILE)):
            publish_file(os.path.join(STAGED_FOLDER, DESCRIPTION_FILE),
                        KAFKA_BROKER, KAFKA_DESCRIPTION_TOPIC)

        # Publish all extracted files to Kafka
        publish_staged(STAGED_FOLDER, KAFKA_BROKER, KAFKA_TOPIC, TOPIC_KEY_REGEX)

        # Remove the temporary folder
        if os.path.exists("./tmp"):
            shutil.rmtree("./tmp")

        print(f"Finishing iteration, waiting {LOOP_WAIT_TIME} seconds")
        
        # Wait for a defined interval before the next run
        time.sleep(LOOP_WAIT_TIME)

if __name__ == "__main__":
    run()
