import os
from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import *


# Function to write Kafka messages to MariaDB
def write_to_mariadb(batch_df, epoch_id, table):
    jdbc_url = "jdbc:mysql://mariadb:3306/jetstream"

    connection_properties = {
        "user": "root",
        "password": "jetstream",
        "driver": "com.mysql.cj.jdbc.Driver"
    }

    # Write everything to the staging table,
        # because sometimes data gets corrected afterwards by DWD causing duplicate errors for primary keys
    table = f"{table}_staging"

    try:
        batch_df.write \
            .format("jdbc") \
            .mode("append") \
            .option("url", jdbc_url) \
            .option("dbtable", table) \
            .options(**connection_properties) \
            .save()

        print(f"Batch with {batch_df.count()} elements successfully saved to database table {table}")

    except Exception as ex:
        print(f"Error writing to table {table} - batch {epoch_id}: {str(ex)}")

# Create SparkSession
spark = SparkSession.builder \
    .appName("Jetstream Consumer") \
    .master("spark://spark-master:7077") \
    .getOrCreate()

# Set Spark logging level to WARN
spark.sparkContext.setLogLevel("WARN")

# Get Kafka broker from env variable
KAFKA_BROKER = os.environ.get("KAFKA_BROKER")

#################### Read from Kafka ####################
# Start from earliest offset (either from beginning or from latest commit)
kafka_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BROKER) \
    .option("subscribe", "jetstream") \
    .option("startingOffsets", "earliest") \
    .option("checkpointLocation", "/tmp/kafka_stream_checkpoint") \
    .load()

kafka_description_stream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BROKER) \
    .option("subscribe", "jetstream-description") \
    .option("startingOffsets", "earliest") \
    .option("encoding", "ISO-8859-1") \
    .option("checkpointLocation", "/tmp/kafka_description_stream_checkpoint") \
    .load()


#################### Parse messages ####################

# Split by either semicolon or whitespace (depending on file type (CSV / space separated))
# Apply schema
# Remove faulty data

# Wind data
parsed_stream = kafka_stream.selectExpr("cast(value as string)") \
    .withColumn("parsed", split(col("value"), ";")) \
    .select(
        col("parsed")[0].cast(IntegerType()).alias("station_id"),
        to_timestamp(col("parsed")[1].cast(StringType()), "yyyyMMddHHmm").alias("measurement_date"),
        col("parsed")[2].cast(IntegerType()).alias("quality_level"),
        col("parsed")[3].cast(DoubleType()).alias("wind_speed"),
        col("parsed")[4].cast(IntegerType()).alias("wind_direction")
    ) \
    .filter(col("station_id").isNotNull()) \
    .filter(col("wind_speed") >= 0)

# Station description
parsed_description_stream = kafka_description_stream.selectExpr("cast(value as string)") \
    .withColumn("parsed", split(col("value"), r"\s+")) \
    .select(
        col("parsed")[0].cast(IntegerType()).alias("station_id"),
        to_date(col("parsed")[1].cast(StringType()), "yyyyMMdd").alias("von_datum"),
        to_date(col("parsed")[2].cast(StringType()), "yyyyMMdd").alias("bis_datum"),
        col("parsed")[3].cast(IntegerType()).alias("stationshoehe"),
        col("parsed")[4].cast(DoubleType()).alias("geoBreite"),
        col("parsed")[5].cast(DoubleType()).alias("geoLaenge"),
        # collect all words except for the last 2 (bundesland, abgabe) and add them back together
        concat_ws(" ", expr("slice(parsed, 7, size(parsed) - 8)")).alias("stationsname"),
        col("parsed")[expr("size(parsed) - 2")].cast(StringType()).alias("bundesland"), # doesn't have whitespaces
        col("parsed")[expr("size(parsed) - 1")].cast(StringType()).alias("abgabe") # doesn't seem to have whitespaces
    ) \
    .filter(col("station_id").isNotNull())


#################### Write to MariaDB ####################

mariadb_query = parsed_stream.writeStream \
    .foreachBatch(lambda batch_df, epoch_id: write_to_mariadb(batch_df, epoch_id, "wind_data")) \
    .outputMode("update") \
    .option("checkpointLocation", "/tmp/parsed_stream_checkpoint") \
    .trigger(processingTime="1 second") \
    .start()
    # continuous trigger doesn't seem to work...

mariadb_query_stations = parsed_description_stream.writeStream \
    .foreachBatch(lambda batch_df, epoch_id: write_to_mariadb(batch_df, epoch_id, "stations")) \
    .outputMode("update") \
    .option("checkpointLocation", "/tmp/parsed_description_stream_checkpoint") \
    .trigger(processingTime="1 second") \
    .start()
    # continuous trigger doesn't seem to work...

#################### Write processed data to console ####################

console_query = parsed_stream.writeStream \
    .outputMode("append") \
    .format("console") \
    .option("truncate", "false") \
    .trigger(processingTime="5 seconds") \
    .start()


#################### Wait for termination ####################

spark.streams.awaitAnyTermination()
