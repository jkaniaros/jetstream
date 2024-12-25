# Laborarbeit Big Data Engineering WiSe 2024/2025
> Jannis Kaniaros & Fabian Lohmüller

- [Laborarbeit Big Data Engineering WiSe 2024/2025](#laborarbeit-big-data-engineering-wise-20242025)
  - [Idea](#idea)
  - [Architecture](#architecture)
    - [Python Web Scraper + Streaming Service](#python-web-scraper--streaming-service)
    - [Apache Kafka as Message Queue](#apache-kafka-as-message-queue)
    - [Apache Spark for Data Preparation](#apache-spark-for-data-preparation)
    - [MariaDB as central storage](#mariadb-as-central-storage)
  - [Entwurf](#entwurf)
  - [Screencast](#screencast)


## Idea
Der Klimawandel wird immer kritischer - insbesondere auch stark zunehmende Winde.
Deshalb eine Applikation, die die Winddaten des DWDs abruft, um damit später ein Modell für Prognosen zu generieren.

Winddaten werden durch DWD stündlich für ca. 300 Städte erhoben, diese werden täglich online zur Verfügung gestellt.


## Architecture
1. Python Web Scraper + Streaming Service
2. Apache Kafka as Message Queue
3. Apache Spark for Data Preparation
4. MariaDB as central storage

### Python Web Scraper + Streaming Service
Stündliche Winddaten werden vom Deutschen Wetterdienst (DWD) in unterschiedlichen Zeitperioden aktualisiert. Die hier verwendeten Daten des Deutschen Wetterdienstes werden regelmäßig als Open Data kostenfrei unter folgendem
[Link für Winddaten](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/10_minutes/wind/now/) bereitgetellt.

Die Python-Anwendung `generator.py` bzw `generator` unter Docker lädt die bereitgestellten zip-Files auf der o.g. Website herunter, extrahiert die Dateien und iteriert dann über alle relevanten Wind-Logs.  
Die Menge der Wind-Logs ist dabei so groß, dass das Verhalten eher einem Stream, statt einer Batch-Verarbeitung gleicht.

Die einzelnen Zeilen der Logfiles sind im CSV-Format, wobei immer die Wetterstations-ID, das Messdatum, das Qualitätsniveau (1-10), sowie `F` für die Windstärke und `D` für die Windrichtung enthalten sind:
```csv
STATIONS_ID;MESS_DATUM;QN_3;F;D;eor
2667;2024121803;1;5.0;130;eor
```
Das Qualitätsniveau ist vom DWD folgendermaßen beschrieben ([Beschreibung Winddaten](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly/wind/BESCHREIBUNG_obsgermany_climate_hourly_wind_de.pdf)):
- QN = 1 : nur formale Prüfung
- QN = 2 : nach individuellen Kriterien geprüft
- QN = 3 : automatische Prüfung und Korrektur
- QN = 5 : historische, subjektive Verfahren
- QN = 7 : geprüft, gepflegt, nicht korrigiert
- QN = 8 : Qualitätsicherung ausserhalb ROUTINE
- QN = 9 : nicht alle Parameter korrigiert
- QN = 10 : Qualitätsprüfung und Korrektur beendet.

### Apache Kafka as Message Queue
Ein Apache Kafka Broker wird im Cluster als zentrale Message Queue eingesetzt. Es werden hierbei zwei Topics verwendet: `jetstream` für die Wetterdaten und `jetstream-description` für die Beschreibungsdatei der Wetterdaten (insbesondere sind hier Stationsinformationen zu finden).

Für den Kafka Broker wird aus Gründen der Einfachheit keine Replikation eingesetzt. Ebenfalls werden die Logfiles nach 1 Gigabyte gelöscht, sodass der Plattenspeicher der Host-Maschine nicht überfüllt wird oder Konfigurationsanpassungen (z.B. maximal verwendeter Festplattenspeicher) bei Docker notwendig sind.

### Apache Spark for Data Preparation
Zur Datenverarbeitung wird Apache Spark als zentrale Technologie verwendet. Im Cluster werden hierfür zunächst ein Spark Master sowie ein Spark Worker erstellt. Dazu dient das Bitnami-Spark-Image.

Für die Spark-Applikation wird ebenfalls das Bitnami-Spark-Image als Basisimage verwendet, allerdings sind hier noch Anpassungen notwendig, um die Kombination aus Spark, Kafka und MariaDB lauffähig zu bekommen.  
Hierzu werden Dependencies als JAR-Files heruntergeladen und im Ordner `/opt/bitnami/spark/jars/` hinterlegt. Nach der Installation der Python-Dependencies kann dann die Applikationsdatei über `spark-submit` übertragen und an die Spark-Worker zur Verarbeitung gegeben werden.

In der Spark-Applikation werden beide oben beschriebenen Kafka Topics als Stream gelesen und entsprechend verarbeitet.  
Zuerst werden hierbei die Streams ins richtige Format gebracht (Umwandlung des JSON-Byte-Arrays in CSV, anschließend von CSV in verwendbare Spalten). Dabei werden fehlerhafte Zeilen, z.B. null-Werte in der Stations-ID oder Windgeschwindigkeiten <= 0, entfernt.

Anschließend finden Aggregationen statt:
- `station_aggregations_daily`: Berechnung der durchschnittlichen Windgeschwindigkeit und -richtung pro Wetterstation auf Tagesebene.
- `station_aggregations_weekly`: Berechnung der durchschnittlichen Windgeschwindigkeit und -richtung pro Wetterstation auf Wochenebene.

Zuletzt werden die umgewandelten Wetter- und Stationsdaten sowie die Aggregationen in die entsprechenden Tabellen in MariaDB zur weiteren Verwendung abgelegt.  
Die umgewandelten Wetterdaten werden ergänzend noch auf der Konsole ausgegeben, um einen Überblick zu erhalten, ob die Verarbeitung läuft oder nicht.

### MariaDB as central storage
Für die zentrale Ablage wird MariaDB eingesetzt. Beim initialen Start von MariaDB werden alle notwendigen Datenbanken und Tabellen über ein Init-File erstellt, sofern sie noch nicht existieren.  
Die Tabelle `stations` enthält alle Informationen zu den Wetterstationen aus der Beschreibungsdatei.  
Die Tabelle `wind_data` enthält alle umgewandelten und gefilterten Daten. Hier wird sozusagen die Historie aufgebaut.  
Die Tabelle `wind_agg` enthält alle durchgeführten Aggregationen, also die durchschnittliche Windrichtung und -geschwindigkeit auf Tages- und Wochenebene pro Station. Sie ist entsprechend indiziert, um Suchen zu beschleunigen.

## Entwurf
- Build + create container: `docker-compose build --no-cache; docker-compose up -d`
- Remove everything: `docker-compose down`
- Restart: `docker-compose down; docker-compose build; docker-compose up -d`
- Show logs: `docker logs {container}`

MariaDB:
- Open terminal in MariaDB container
- Create connection to MariaDB server: `mysql -u root -p jetstream`
- Show all databases: `show databases;`
- Select database: `use jetstream;`
- Show all tables: `show tables;`
- Queries: `select * from wind_data;`

## Screencast
