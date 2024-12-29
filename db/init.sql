create database if not exists jetstream;
use jetstream;

--drop table if exists stations;
--drop table if exists wind_data;
--drop table if exists wind_agg

-- ensure production and staging tables exist
create table if not exists stations (
    station_id bigint not null,
    von_datum timestamp not null,
    bis_datum timestamp not null,
    stationshoehe smallint, 
    geobreite double,
    geolaenge double,
    stationsname text,
    bundesland text,
    abgabe text,
    primary key (station_id),
    index idx_station (station_id)
);

create table if not exists stations_staging (
    station_id bigint not null,
    von_datum timestamp not null,
    bis_datum timestamp not null,
    stationshoehe smallint, 
    geobreite double,
    geolaenge double,
    stationsname text,
    bundesland text,
    abgabe text,
    index idx_station (station_id)
);

create table if not exists wind_data (
    station_id bigint not null,
    measurement_date timestamp not null,
    quality_level tinyint comment '
        qn = 1 : nur formale prüfung;
        qn = 2 : nach individuellen kriterien geprüft;
        qn = 3 : automatische prüfung und korrektur.',
    wind_speed double comment 'windgeschwindigkeit in m/s', 
    wind_direction smallint comment 'windrichtung in grad',
    primary key (station_id, measurement_date),
    index idx_station (station_id),
    index idx_date (measurement_date)
);

create table if not exists wind_data_staging (
    station_id bigint not null,
    measurement_date timestamp not null,
    quality_level tinyint comment '
        qn = 1 : nur formale prüfung;
        qn = 2 : nach individuellen kriterien geprüft;
        qn = 3 : automatische prüfung und korrektur.',
    wind_speed double comment 'windgeschwindigkeit in m/s', 
    wind_direction smallint comment 'windrichtung in grad',
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

-- create a procedure to transfer data from staging to production
delimiter $$
create procedure TransferStagingToProduction()
begin
    -- Transfer and upsert for wind_data
    insert into stations (station_id, von_datum, bis_datum, stationshoehe, geobreite, geolaenge, stationsname, bundesland, abgabe)
    select s.station_id, s.von_datum, s.bis_datum, s.stationshoehe, s.geobreite, s.geolaenge, s.stationsname, s.bundesland, s.abgabe
    from stations_staging s
    on duplicate key update 
        von_datum = values(von_datum),
        bis_datum = values(bis_datum),
        stationshoehe = values(stationshoehe),
        geobreite = values(geobreite),
        geolaenge = values(geolaenge),
        stationsname = values(stationsname),
        bundesland = values(bundesland),
        abgabe = values(abgabe);

    -- Delete transferred rows from staging table
    delete from stations_staging ss
    where exists (
        select *
        from stations s
        where s.station_id = ss.station_id
          and s.von_datum = ss.von_datum
          and s.bis_datum = ss.bis_datum
          and s.stationshoehe = ss.stationshoehe
          and s.geobreite = ss.geobreite
          and s.geolaenge = ss.geolaenge
          and s.stationsname = ss.stationsname
          and s.bundesland = ss.bundesland
          and s.abgabe = ss.abgabe
    );

    -- Transfer and upsert for wind_data
    insert into wind_data (station_id, measurement_date, quality_level, wind_speed, wind_direction)
    select w.station_id, w.measurement_date, w.quality_level, w.wind_speed, w.wind_direction
    from wind_data_staging w
    on duplicate key update 
        quality_level = values(quality_level),
        wind_speed = values(wind_speed),
        wind_direction = values(wind_direction);

    -- Delete transferred rows from staging table
    delete from wind_data_staging ws
    where exists (
        select *
        from wind_data w
        where w.station_id = ws.station_id
          and w.measurement_date = ws.measurement_date
          and w.quality_level = ws.quality_level
          and w.wind_speed = ws.wind_speed
          and w.wind_direction = ws.wind_direction
    );
end$$
delimiter ;

-- schedule the procedure to run regularly using an event
create event if not exists TransferStagingEvent
on schedule every 5 second do
call TransferStagingToProduction();
