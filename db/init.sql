create database if not exists jetstream;
use jetstream;

--drop table if exists wind_data;

create table if not exists wind_data (
    id bigint not null auto_increment,
    station_id bigint not null,
    measurement_date timestamp not null,
    quality_level tinyint comment '
        QN = 1 : nur formale Prüfung;
        QN = 2 : nach individuellen Kriterien geprüft;
        QN = 3 : automatische Prüfung und Korrektur;
        QN = 5 : historische, subjektive Verfahren;
        QN = 7 : geprüft, gepflegt, nicht korrigiert;
        QN = 8 : Qualitätsicherung ausserhalb ROUTINE;
        QN = 9 : nicht alle Parameter korrigiert;
        QN = 10 : Qualitätsprüfung und Korrektur beendet.',
    wind_speed double comment 'Windgeschwindigkeit in m/s', 
    wind_direction smallint comment 'Windrichtung in Grad',
    primary key (id),
    index idx_station (station_id),
    index idx_date (measurement_date)
);