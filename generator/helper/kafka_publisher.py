import re
import os
from kafka.admin import KafkaAdminClient, NewTopic
from kafka import KafkaProducer, KafkaClient

def create_topic(topic: str, broker: str):
    """
    Create a topic in Kafka. 
    Parameters:
    topic (str): The Kafka topic name to create.
    broker (str): The hostname of the Kafka broker.
    """
    # Create Kafka Client to get all exisiting topics. Existing topics can not be created anymore
    kafka_client = KafkaClient(bootstrap_servers=broker, client_id="data-generator")
    future = kafka_client.cluster.request_update()
    kafka_client.poll(future=future)
    topics = kafka_client.cluster.topics()

    # If topic does not exist, create a new one
    if topic not in topics:
        kafka_admin_client = KafkaAdminClient(bootstrap_servers=broker, client_id="data-generator")
        new_topics = []
        new_topics.append(NewTopic(name=topic, num_partitions=1000, replication_factor=1))
        kafka_admin_client.create_topics(new_topics=new_topics)
        print(f"Created topic '{topic}'")
    else:
        print(f"Topic '{topic}' already exists")


def publish_lines(filepath: str, broker: str, producer: str, topic: str, key: int, archive_folder: str):
    """
    Publish all lines from a file to the Kafka broker on the given topic.

    Parameters:
    filepath (str): The filepath of the file to send.
    broker (str): The hostname of the Kafka broker.
    producer (str): The Kafka producer object.
    topic (str): The Kafka topic to publish on.
    key (int): The Kafka topic key to publish on.
    archive_folder (str): The folder to archive the sent line files.
    """
    # Return if the file does not exist
    if not os.path.exists(filepath):
        return

    # Create archive folder if it doesn't exist
    if archive_folder is not None and not os.path.exists(archive_folder):
        os.makedirs(archive_folder)

    # print(f"Publish lines file: {filepath}")

    # Create the topic if it doesn't already exist
    create_topic(topic, broker)

    # If UTF-8 encoding goes wrong, try with Windows-1252
    try:
        _publish_lines_core(filepath, producer, topic, key, archive_folder, "UTF-8")
    except UnicodeDecodeError:
        _publish_lines_core(filepath, producer, topic, key, archive_folder, "Windows-1252")


def _publish_lines_core(filepath: str, producer: str, topic: str, key: int, archive_folder: str, encoding: str):
    # If archive folder is set, open the corresponding file to save the sent lines there
    if archive_folder is not None:
        archive_filename = os.path.basename(filepath).replace('merged', 'archived')
        archive_path = os.path.join(archive_folder, archive_filename)
        archive_file = open(archive_path, "a", encoding="UTF-8")
    else:
        archive_file = None

    try:
        with open(filepath, "r", encoding=encoding) as file:
            for line in file:
                line = line.strip()

                # Check if the first line contains header information. If yes, exclude it
                if line.upper().startswith("STATION") or line.upper().startswith("---"):
                        continue

                # Send with key if it is set
                if key is not None:
                    producer.send(topic=topic, key=bytes(key), value=bytes(line, encoding="UTF-8"))
                    #print(f"\t\tSent '{line}' to Kafka topic '{topic}' and key '{key}'")
                else:
                    producer.send(topic=topic, value=bytes(line, encoding="UTF-8"))
                    #print(f"\t\tSent '{line}' to Kafka topic '{topic}'")

                if archive_file is not None:
                    archive_file.write(f"{line}\n")

            producer.flush()
    finally:
        if archive_file is not None:
            archive_file.close()

def publish_folder(folder: str, broker: str, topic: str, key_regex: str, archive_folder: str):
    """
    Publish all files from folder to the Kafka broker on the specified topic in the key specified by regex.

    Parameters:
    folder (str): The filepath where the txt files are stored.
    broker (str): The hostname of the Kafka broker.
    topic (str): The topic to publish the information on.
    key_regex (str): The regex string for the key to be extracted from the filename.
    archive_folder (str): The folder to archive the sent line files.
    """
    # Return if the file does not exist
    if not os.path.exists(folder):
        return

    producer = KafkaProducer(bootstrap_servers=broker, \
                             client_id="data-generator",\
                             batch_size=0
    )
    pattern = re.compile(key_regex)

    # For every file in given folder, publish all lines
    for file in os.listdir(folder):
        key = pattern.search(file)
        if key is not None:
            key = int(key.group(1).lstrip("0"))

            print(f"Publish file '{file}' to topic '{topic}' and key '{key}'")
            publish_lines(os.path.join(folder,file), broker, producer, topic, key, archive_folder)

    producer.close()


def publish_file(filepath: str, broker: str, topic: str, key: str = None, archive_folder: str = None):
    """
    Publish all files from folder to the Kafka broker on the specified topic in the key specified by regex.

    Parameters:
    filepath (str): The filepath where the file is stored.
    broker (str): The hostname of the Kafka broker.
    topic (str): The topic to publish the information on.
    key (str): The regex string for the key to send on. Default: None.
    archive_folder (str): The folder to archive the sent line files.
    """
    # Return if the file does not exist
    if not os.path.exists(filepath):
        return

    producer = KafkaProducer(bootstrap_servers=broker, \
                             client_id="data-generator",\
                             batch_size=0
    )


    print(f"Publish file '{filepath}' to topic '{topic}' and key '{key}'")
    publish_lines(filepath, broker, producer, topic, key, archive_folder)

    producer.close()
