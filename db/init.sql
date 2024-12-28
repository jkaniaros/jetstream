create database if not exists jetstream;
use jetstream;

--drop table if exists stations;
--drop table if exists wind_data;
--drop table if exists wind_agg

create table if not exists stations (
    station_id bigint not null,
    von_datum timestamp not null,
    bis_datum timestamp not null,
    stationshoehe smallint, 
    geoBreite double,
    geoLaenge double,
    stationsname text,
    bundesland text,
    abgabe text,
    primary key (station_id),
    index idx_station (station_id)
);

create table if not exists wind_data (
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
    primary key (station_id, measurement_date),
    index idx_station (station_id),
    index idx_date (measurement_date)
);

-- create table if not exists wind_agg (
--     id bigint not null auto_increment,
--     station_id bigint not null,
--     start_time timestamp not null,
--     end_time timestamp not null,
--     avg_wind_speed double,
--     avg_wind_direction smallint,
--     primary key (id),
--     index idx_station (station_id),
--     index idx_start_date (start_time),
--     index idx_end_date (end_Time),
--     unique (station_id, start_time, end_time)
-- );
