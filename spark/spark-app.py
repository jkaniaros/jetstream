import os
from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import *
from pyspark.ml.feature import Bucketizer


# Function to write Kafka micro batches to MariaDB
def write_to_mariadb(batch_df, epoch_id, table):
    jdbc_url = "jdbc:mysql://mariadb:3306/jetstream"

    connection_properties = {
        "user": "root",
        "password": "jetstream",
        "driver": "com.mysql.cj.jdbc.Driver"
    }

    # Write everything to the staging table, because sometimes data gets corrected afterwards by DWD causing duplicate errors for primary keys
    table = f"{table}_staging"

    try:
        batch_df.write \
            .format("jdbc") \
            .mode("append") \
            .option("url", jdbc_url) \
            .option("dbtable", table) \
            .options(**connection_properties) \
            .save()

        print(f"Batch with {batch_df.count()} elements saved to database table {table}")

    except Exception as ex:
        print(f"Error writing to table {table} - batch {epoch_id}: {str(ex)}")

# Create SparkSession
spark = SparkSession.builder \
    .appName("Jetstream Consumer") \
    .master("spark://spark-master:7077") \
    .getOrCreate()

# Set Spark logging level to WARN
spark.sparkContext.setLogLevel("WARN")

# Get Kafka broker from env var
KAFKA_BROKER = os.environ.get("KAFKA_BROKER")

#################### Read from Kafka ####################
# Start from earliest offset (either from beginning or from latest commit)
jetstream = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BROKER) \
    .option("subscribe", "jetstream") \
    .option("startingOffsets", "earliest") \
    .option("checkpointLocation", "/tmp/kafka_stream_checkpoint") \
    .load()

jetstream_description = spark.readStream \
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
jetstream_parsed = jetstream.selectExpr("cast(value as string)") \
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
jetstream_description_parsed = jetstream_description.selectExpr("cast(value as string)") \
    .withColumn("parsed", split(col("value"), r"\s+")) \
    .select(
        col("parsed")[0].cast(IntegerType()).alias("station_id"),
        to_date(col("parsed")[1].cast(StringType()), "yyyyMMdd").alias("date_from"),
        to_date(col("parsed")[2].cast(StringType()), "yyyyMMdd").alias("date_until"),
        col("parsed")[3].cast(IntegerType()).alias("height"),
        col("parsed")[4].cast(DoubleType()).alias("latitude"),
        col("parsed")[5].cast(DoubleType()).alias("longitude"),
        # collect all words except for the last 2 (state, delivery) and add them back together
        concat_ws(" ", expr("slice(parsed, 7, size(parsed) - 8)")).alias("name"),
        col("parsed")[expr("size(parsed) - 2")].cast(StringType()).alias("state"), # doesn't have whitespaces
        col("parsed")[expr("size(parsed) - 1")].cast(StringType()).alias("delivery") # doesn't seem to have whitespaces
    ) \
    .filter(col("station_id").isNotNull())


#################### Do some aggregations ####################

# Binning of wind direction
# Define the splits where the different buckets should start
wind_direction_splits = [x for x in range(0, 361) if x%45 == 0] # Do a bucket for every 45 degrees
# Buckets:
    # 0: [0, 45[
    # 1: [45, 90[
    # 2: [90, 135[
    # 3: [135, 180[
    # 4: [180, 225[
    # 5: [225, 270[
    # 6: [270, 315[
    # 7: [315, 360[
wind_dir_bucketizer = Bucketizer(splits=wind_direction_splits, 
                                 inputCol="wind_direction",
                                 outputCol="wind_direction_bucket")
jetstream_bucketized = wind_dir_bucketizer.transform(jetstream_parsed)


# Binning of wind speed
# Define the splits where the different buckets should start
wind_speed_splits = [0.0, 5.0, 10.0, 17.0, float("inf")] # Do a bucket for every wind speed category (low, medium, heavy, extreme)
# Buckets:
    # 0: [0, 5[
    # 1: [5, 10[
    # 2: [10, 17[
    # 3: [17, inf[
wind_speed_bucketizer = Bucketizer(splits=wind_speed_splits,
                                   inputCol="wind_speed",
                                   outputCol="wind_speed_bucket")
jetstream_bucketized = wind_speed_bucketizer.transform(jetstream_bucketized)
# jetstream_bucketized:
    # station_id: int, 
    # measurement_date: timestamp, 
    # quality_level: int, 
    # wind_speed: double, 
    # wind_direction: int, 
    # wind_direction_bucket: double, 
    # wind_speed_bucket: double]

#################### Write to MariaDB ####################

mariadb_wind_data = jetstream_bucketized.writeStream \
    .foreachBatch(lambda batch_df, epoch_id: write_to_mariadb(batch_df, epoch_id, "wind_data")) \
    .outputMode("update") \
    .option("checkpointLocation", "/tmp/jetstream_bucketized_checkpoint") \
    .trigger(processingTime="1 second") \
    .start()
    # continuous trigger doesn't seem to work...

mariadb_stations = jetstream_description_parsed.writeStream \
    .foreachBatch(lambda batch_df, epoch_id: write_to_mariadb(batch_df, epoch_id, "stations")) \
    .outputMode("update") \
    .option("checkpointLocation", "/tmp/jetstream_description_parsed_checkpoint") \
    .trigger(processingTime="1 second") \
    .start()
    # continuous trigger doesn't seem to work...

#################### Write processed data to console ####################

console_query = jetstream_bucketized.writeStream \
    .outputMode("append") \
    .format("console") \
    .option("truncate", "false") \
    .trigger(processingTime="5 seconds") \
    .start()


#################### Wait for termination ####################

spark.streams.awaitAnyTermination()
