from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import *
import os


# Function to write Kafka messages to MariaDB
def write_to_mariadb(batch_df, epoch_id, table):
    jdbc_url = "jdbc:mysql://mariadb:3306/jetstream"
    
    connection_properties = {
        "user": "root",
        "password": "jetstream",
        "driver": "com.mysql.cj.jdbc.Driver"
    }

    try:
        batch_df.write \
            .format("jdbc") \
            .mode("append") \
            .option("url", jdbc_url) \
            .option("dbtable", table) \
            .options(**connection_properties) \
            .save()
    except Exception as e:
        print(f"Error writing batch {epoch_id}: {str(e)}")
# Duplicate data (caused by reprocessing) should be ignored because of the primary key in the database

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
    .option("encoding", "ISO-8859-1") \
    .load()


#################### Parse messages ####################

# Parse messages into readable format and apply schema
parsed_stream = kafka_stream.selectExpr("cast(value as string)") \
    .withColumn("parsed", split(col("value"), ";")) \
    .select(
        col("parsed")[0].cast(IntegerType()).alias("station_id"),
        to_timestamp(col("parsed")[1].cast(StringType()), "yyyyMMddHH").alias("measurement_date"),
        col("parsed")[2].cast(IntegerType()).alias("quality_level"),
        col("parsed")[3].cast(DoubleType()).alias("wind_speed"),
        col("parsed")[4].cast(IntegerType()).alias("wind_direction")
    ) \
    .filter(col("station_id").isNotNull()) \
    .filter(col("wind_speed") >= 0)

parsed_description_stream = kafka_description_stream.selectExpr("cast(value as string)") \
    .withColumn("parsed", split(col("value"), r"\s+")) \
    .select (
        col("parsed")[0].cast(IntegerType()).alias("stations_id"),
        to_date(col("parsed")[1].cast(StringType()), "yyyyMMdd").alias("von_datum"),
        to_date(col("parsed")[2].cast(StringType()), "yyyyMMdd").alias("bis_datum"),
        col("parsed")[3].cast(IntegerType()).alias("stationshoehe"),
        col("parsed")[4].cast(DoubleType()).alias("geoBreite"),
        col("parsed")[5].cast(DoubleType()).alias("geoLaenge"),
        col("parsed")[6].cast(StringType()).alias("stationsname"),
        col("parsed")[7].cast(StringType()).alias("bundesland"),
        col("parsed")[8].cast(StringType()).alias("abgabe")
    )


#################### Do some aggregations ####################
# Average wind speed and direction for each station
station_aggregations_daily = parsed_stream \
    .withWatermark("measurement_date", "1 year") \
    .groupBy(
        col("station_id"),
        window(col("measurement_date"), "1 day", "1 day")  # Daily aggregation
    ) \
    .agg(
        round(avg(col("wind_speed"))).alias("avg_wind_speed"),
        round(avg(col("wind_direction"))).alias("avg_wind_direction")
    ) \
    .select(
        col("station_id"),
        col("window.start").alias("start_time"),
        col("window.end").alias("end_time"),
        col("avg_wind_speed"),
        col("avg_wind_direction")
    )


# Aggregations by week
station_aggregations_weekly = parsed_stream \
    .withWatermark("measurement_date", "1 year") \
    .groupBy(
        col("station_id"),
        window(col("measurement_date"), "1 week", "1 week")  # Weekly aggregation
    ) \
    .agg(
        round(avg(col("wind_speed"))).alias("avg_wind_speed"),
        round(avg(col("wind_direction"))).alias("avg_wind_direction")
    ) \
    .select(
        col("station_id"),
        col("window.start").alias("start_time"),
        col("window.end").alias("end_time"),
        col("avg_wind_speed"),
        col("avg_wind_direction")
    )


#################### Write to MariaDB ####################

mariadb_query = parsed_stream.writeStream \
    .foreachBatch(lambda batch_df, epoch_id: write_to_mariadb(batch_df, epoch_id, "wind_data")) \
    .outputMode("update") \
    .trigger(processingTime="15 seconds") \
    .start()

mariadb_query_aggregations_daily = station_aggregations_daily.writeStream \
    .foreachBatch(lambda batch_df, epoch_id: write_to_mariadb(batch_df, epoch_id, "wind_agg")) \
    .outputMode("update") \
    .trigger(processingTime="15 seconds") \
    .start()
    
mariadb_query_aggregations_weekly = station_aggregations_weekly.writeStream \
    .foreachBatch(lambda batch_df, epoch_id: write_to_mariadb(batch_df, epoch_id, "wind_agg")) \
    .outputMode("update") \
    .trigger(processingTime="15 seconds") \
    .start()

mariadb_query_stations = parsed_description_stream.writeStream \
    .foreachBatch(lambda batch_df, epoch_id: write_to_mariadb(batch_df, epoch_id, "stations")) \
    .outputMode("update") \
    .trigger(processingTime="15 seconds") \
    .start()


#################### Write processed data to console ####################

console_query = parsed_stream.writeStream \
    .outputMode("append") \
    .format("console") \
    .option("checkpointLocation", "/tmp/kafka_checkpoint") \
    .option("truncate", "false") \
    .trigger(processingTime='15 seconds') \
    .start()


#################### Wait for termination ####################

spark.streams.awaitAnyTermination()