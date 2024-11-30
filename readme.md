# Laborarbeit Big Data Engineering WiSe 2024/2025
> Jannis Kaniaros & Fabian Lohmüller

## Idee
Klimawandel wird immer kritischer - insbesondere auch stark zunehmende Winde.
Deshalb eine Applikation, die die Winddaten des DWDs abruft, um damit später ein Modell für Prognosen zu generieren.

Winddaten werden durch DWD stündlich für ca. 300 Städte generiert, diese können regelmäßig abgerufen werden.

[Link für DWD File Download](https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly/wind/recent/)


## Architektur
1. Python Web Scraper
2. Python Streaming Service
3. Apache Kafka als Message Queue
4. Apache Spark 
5. MariaDB als zentrale Ablage für Serving Layer

## Entwurf

## Screencast