from pyspark.sql import SparkSession
from pyspark.sql.types import *
from pyspark.sql.functions import *
import os


# Function to write Kafka messages to MariaDB
def write_to_mariadb_winddata(batch_df, epoch_id):
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
            .option("dbtable", "wind_data") \
            .options(**connection_properties) \
            .save()
    except Exception as e:
        print(f"Error writing batch {epoch_id}: {str(e)}")

def write_to_mariadb_windagg(batch_df, epoch_id):
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
            .option("dbtable", "wind_agg") \
            .options(**connection_properties) \
            .save()
    except Exception as e:
        print(f"Error writing batch {epoch_id}: {str(e)}")


def write_to_mariadb_stations(batch_df, epoch_id):
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
            .option("dbtable", "stations") \
            .options(**connection_properties) \
            .save()
    except Exception as e:
        print(f"Error writing batch {epoch_id}: {str(e)}")

# TODO: Was passiert, wenn die Daten bereits enthalten sind? Generator liefert die selben Daten immer wieder...

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
# TODO: verarbeiten und in DB-Tabelle `stations` abspeichern

# Parse messages into readable format and apply schema
parsed_stream = kafka_stream.selectExpr("CAST(value AS STRING)") \
    .withColumn("parsed", split(col("value"), ";")) \
    .select(
        col("parsed")[0].cast(IntegerType()).alias("station_id"),
        to_timestamp(col("parsed")[1].cast(StringType()), "yyyyMMddHH").alias("measurement_date"),
        col("parsed")[2].cast(IntegerType()).alias("quality_level"),
        col("parsed")[3].cast(DoubleType()).alias("wind_speed"),
        col("parsed")[4].cast(IntegerType()).alias("wind_direction")
    ) \
    .filter(col("station_id").isNotNull())


# Do some aggregations
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
    

# Stream the extreme wind data and save it into a separate table `extreme_wind_data``
# extreme_wind_stream = parsed_stream.filter("wind_speed" >= 17.0)

# Write aggregated data to MariaDB
mariadb_query = parsed_stream.writeStream \
    .foreachBatch(write_to_mariadb_winddata) \
    .outputMode("update") \
    .trigger(processingTime="15 seconds") \
    .start()

mariadb_query_aggregations_daily = station_aggregations_daily.writeStream \
    .foreachBatch(write_to_mariadb_windagg) \
    .outputMode("update") \
    .trigger(processingTime="15 seconds") \
    .start()
    
mariadb_query_aggregations_weekly = station_aggregations_weekly.writeStream \
    .foreachBatch(write_to_mariadb_windagg) \
    .outputMode("update") \
    .trigger(processingTime="15 seconds") \
    .start()


# Write processed data to console
console_query = parsed_stream.writeStream \
    .outputMode("append") \
    .format("console") \
    .option("checkpointLocation", "/tmp/kafka_checkpoint") \
    .option("truncate", "false") \
    .trigger(processingTime='10 seconds') \
    .start()


# Wait for termination
spark.streams.awaitAnyTermination()