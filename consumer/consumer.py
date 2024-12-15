from kafka import KafkaConsumer, KafkaClient, TopicPartition
from kafka.errors import NoBrokersAvailable
from concurrent.futures import ThreadPoolExecutor
import os
import time

KAFKA_TOPIC = "jetstream"

KAFKA_BROKER = os.environ.get("KAFKA_BROKER")
print(f"Kafka Broker: {KAFKA_BROKER}")

def consume_messages(topic: str, partition: int):
    """
    Connect to a specified Kafka topic and consume messages from the specified partition
    
    Parameters:
    topic (str): The Kafka topic to consume messages from.
    partition (int): The Kafka topic partition to consume messages from.
    """
    
    print(f"Consuming topic '{topic}' partition {partition}")
    consumer = KafkaConsumer(
        bootstrap_servers=KAFKA_BROKER,
        group_id=topic,
        auto_offset_reset="earliest" # Start from the earliest message
    )
    # Assign the partition to the consumer
    p = TopicPartition(topic, partition)
    consumer.assign([p])
    
    try:
        for message in consumer:
            print(f"Received message from topic '{topic}' partition {partition}: '{message.value}'")
            # Process the message here
    except Exception as e:
        print(f"Error consuming messages from '{topic}' partition {partition}: {e}")
    finally:
        consumer.close()
    

def run():
    """
    Entrypoint of the consumer. Reads all topics within the Kafka broker
    """
    
    print("Run")
    topics = []
    try:
        kafka_client = KafkaClient(bootstrap_servers=KAFKA_BROKER, client_id="data-consumer")
        future = kafka_client.cluster.request_update()
        kafka_client.poll(future=future)
        topics = kafka_client.cluster.topics()
        
        print(f"Topics: {list(topics)}")
    except Exception as e:
        print(e)
        return

    # Create a ThreadPoolExecutor to process each topic in parallel
    if KAFKA_TOPIC not in topics:
        print(f"{time.ctime()} No topics")
        return
    
    # Get all partitions for the topic
    topic_partitions = kafka_client.cluster.partitions_for_topic(KAFKA_TOPIC)
    print(f"Topic partitions {topic_partitions}")
    
    # Each topic partition is processed concurrently in its own thread
    with ThreadPoolExecutor(max_workers=len(topic_partitions)) as executor:
        # Create a consume_messages task for each topic and submit it to the executor
        futures = {executor.submit(consume_messages, KAFKA_TOPIC, partition): partition for partition in topic_partitions}

        # Await every future
        for f in futures:
            try:
                f.result()
            except Exception as e:
                print(f"Error in thread for topic {futures[future]}: {e}")

if __name__ == "__main__":
    print("Starting...")
    
    while True:
        run()
        print("Run finished. Waiting 10 seconds")
        time.sleep(10)
