from kafka import KafkaConsumer, KafkaClient
from kafka.errors import NoBrokersAvailable
from concurrent.futures import ThreadPoolExecutor
import os
import time

KAFKA_BROKER = os.environ.get("KAFKA_BROKER")
print(f"Kafka Broker: {KAFKA_BROKER}")

WAIT_SEC = 1

def consume_messages(topic):
    """
    Connect to a specified Kafka topic and consume messages from it
    
    Parameters:
    topic (str): The Kafka topic to consume messages from.
    """
    print(f"Consuming topic {topic}")
    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=KAFKA_BROKER,
        auto_offset_reset="earliest"  # Start from the earliest message
    )
    
    try:
        for message in consumer:
            print(f"Received message from {topic}: {message.value}")
            # Process the message here
    except Exception as e:
        print(f"Error consuming messages from {topic}: {e}")
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
    except NoBrokersAvailable:
        print(f"No Kafka broker available... Retrying in {WAIT_SEC} secons")

    # Create a ThreadPoolExecutor to process each topic in parallel
    if topics:
        # Use 75% of the available CPU cores
        with ThreadPoolExecutor(max_workers=int(os.cpu_count()*0.75)) as executor:
            # Create a consume_messages task for each topic and submit it to the executor
            # Each topic is processed concurrently in its own thread by the consume_messages function
            futures = {executor.submit(consume_messages, topic): topic for topic in topics}

            # Await every future
            for f in futures:
                try:
                    f.result()
                except Exception as e:
                    print(f"Error in thread for topic {futures[future]}: {e}")
    else:
        print(f"{time.ctime()} No topics")
        
        time.sleep(WAIT_SEC)
        
        # Double the waiting time up to 512 sec (8.5 min)
        if WAIT_SEC <= 256:
            WAIT_SEC *= 2

if __name__ == "__main__":
    print("Starting...")
    
    try:
        while True:
            run()

    except KeyboardInterrupt:
        print("Exit")
