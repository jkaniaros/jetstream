from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import *
import os

# Create SparkSession
spark = SparkSession.builder \
    .appName("Jetstream Consumer") \
    .master("spark://spark-master:7077") \
    .getOrCreate()

# Set Spark logging level to WARN
spark.sparkContext.setLogLevel("WARN")

# Get Kafka broker from env variable
KAFKA_BROKER = os.environ.get("KAFKA_BROKER")

# Read from Kafka
kafka_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BROKER) \
    .option("subscribe", "jetstream") \
    .option("startingOffsets", "earliest") \
    .load()

kafka_description_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BROKER) \
    .option("subscribe", "jetstream-description") \
    .option("startingOffsets", "earliest") \
    .load()
# TODO: verarbeiten

# Parse messages into readable format and apply schema
parsed_stream = kafka_stream.selectExpr("CAST(value AS STRING)") \
    .withColumn("parsed", split(col("value"), ";")) \
    .select(
        col("parsed")[0].cast(IntegerType()).alias("station_id"),
        to_timestamp(col("parsed")[1].cast(StringType()), "yyyyMMddHH").alias("measurement_date"),
        col("parsed")[2].cast(IntegerType()).alias("quality_level"),
        col("parsed")[3].cast(DoubleType()).alias("wind_speed"),
        col("parsed")[4].cast(IntegerType()).alias("wind_direction")
    )

console_query = parsed_stream.writeStream \
    .outputMode("append") \
    .format("console") \
    .option("checkpointLocation", "/tmp/kafka_checkpoint") \
    .option("truncate", "false") \
    .start()


# windowed_counts = parsed_stream \
#     .withWatermark("timestamp", "1 minute") \
#     .groupBy(
#         window(col("timestamp"), "30 seconds", "15 seconds"),
#         ) \
#     .agg(
#         count(when(col("level") == "INFO", 1)).alias("INFO_count"),
#         count(when(col("level") == "ERROR", 1)).alias("ERROR_count"),
#         count(when(col("level") == "DEBUG", 1)).alias("DEBUG_count"),
#         count(when(col("level") == "WARN", 1)).alias("WARN_count")
#     ) \
#     .select(
#         col("window.start").alias("window_start"),
#         col("window.end").alias("window_end"),
#         col("INFO_count"),
#         col("ERROR_count"),
#         col("DEBUG_count"),
#         col("WARN_count")
#     )

# # Output to console
# console_query = windowed_counts.writeStream \
#     .outputMode("update") \
#     .format("console") \
#     .option("truncate", "false") \
#     .trigger(processingTime='10 seconds') \
#     .start()

# Function to write logs to MariaDB
def write_to_mariadb(batch_df, epoch_id):
    jdbc_url = "jdbc:mysql://mariadb:3306/logs"
    
    connection_properties = {
        "user": "root",
        "password": "password",
        "driver": "com.mysql.cj.jdbc.Driver"
    }

    try:
        batch_df.write \
            .format("jdbc") \
            .mode("append") \
            .option("url", jdbc_url) \
            .option("dbtable", "log_data") \
            .options(**connection_properties) \
            .save()
    except Exception as e:
        print(f"Error writing batch {epoch_id}: {str(e)}")

# Write aggregated data to MariaDB
# mariadb_query = windowed_counts.writeStream \
#     .foreachBatch(write_to_mariadb) \
#     .outputMode("update") \
#     .trigger(processingTime="15 seconds") \
#     .start()

# Wait for termination
spark.streams.awaitAnyTermination()