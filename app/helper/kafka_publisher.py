from kafka.admin import KafkaAdminClient, NewTopic
from kafka import KafkaProducer, KafkaClient
import re
import os

def create_topic(topic, broker):
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
        new_topics.append(NewTopic(name=topic, num_partitions=1, replication_factor=1))
        kafka_admin_client.create_topics(new_topics=new_topics)
        print(f"Created topic '{topic}'")
    else:
        print(f"Topic '{topic}' already exists")
    

def publish_lines(filepath, broker, producer, topic):
    """
    Publish all lines from a file to the Kafka broker on the given topic.
    Parameters:
    filepath (str): The filepath of the file to send.
    broker (str): The hostname of the Kafka broker.
    producer (str): The Kafka producer object.
    topic (str): The Kafka topic to publish on.
    """
    # Return if the file does not exist
    if not os.path.exists(filepath):
        return
    
    # print(f"Publish lines file: {filepath}")
    
    # Create the topic if it doesn't already exist
    create_topic(topic, broker)
    
    with open(filepath, "r") as file:
        for line in file:
            producer.send(topic=topic, value=bytes(line, encoding='utf-8'))
            print(f"\t\tSent {line} to Kafka topic '{topic}'")
    

def publish_staged(folder, broker, regex):
    """
    Publish all files from folder to the Kafka broker depending on the specified regex.
    Parameters:
    folder (str): The filepath where the txt files are stored.
    broker (str): The hostname of the Kafka broker.
    regex (str): The regex string for the topic to be extracted from the filename.
    """
    # Return if the file does not exist
    if not os.path.exists(folder):
        return
    
    producer = KafkaProducer(bootstrap_servers=broker, client_id="data-generator")
    pattern = re.compile(regex)
    
    # TODO: multithreading
    
    # For every file in given folder, publish all lines if regex matches with filename
    for file in os.listdir(folder):
        topic = pattern.search(file)
        # print(f"Publish STAGED: {file} compiled {topic}")
        if topic is not None:
            print(f"Publish file '{file}' to topic {topic.group(1).lstrip('0')}")
            publish_lines(os.path.join(folder,file), broker, producer, topic.group(1).lstrip("0"))
            
    producer.close()
