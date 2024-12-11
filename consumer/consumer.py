from kafka import KafkaConsumer, KafkaClient
from concurrent.futures import ThreadPoolExecutor
import os
import time

KAFKA_BROKER = os.environ.get("KAFKA_BROKER")
print(f"Kafka Broker: {KAFKA_BROKER}")

def consume_messages(topic):
    print(f"Consuming topic {topic.list()}")
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
    print("Run")
    kafka_client = KafkaClient(bootstrap_servers=KAFKA_BROKER, client_id="data-consumer")
    future = kafka_client.cluster.request_update()
    kafka_client.poll(future=future)
    topics = kafka_client.cluster.topics()

    print(f"Topics: {list(topics)}")
    # Create a ThreadPoolExecutor to process each topic in parallel
    if topics:
        with ThreadPoolExecutor(max_workers=len(topics)) as executor:
            executor.map(consume_messages, topics)
            # TODO: await execution - currently immediate return!!
    else:
        print(f"{time.ctime()} No topics")
        time.sleep(5)

if __name__ == "__main__":
    print("Starting...")
    #try:
        #while True:
    run()

    #except KeyboardInterrupt:
    #   print("Exit")
