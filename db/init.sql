create database if not exists jetstream;
use jetstream;

--drop table if exists stations;
--drop table if exists wind_data;

-- ensure production and staging tables exist
create table if not exists stations (
    station_id bigint not null,
    date_from timestamp not null,
    date_until timestamp not null,
    height smallint, 
    latitude double,
    longitude double,
    name text,
    state text,
    delivery text,
    primary key (station_id),
    index idx_station (station_id)
);

create table if not exists stations_staging (
    station_id bigint not null,
    date_from timestamp not null,
    date_until timestamp not null,
    height smallint, 
    latitude double,
    longitude double,
    name text,
    state text,
    delivery text,
    index idx_station (station_id)
);

create table if not exists wind_data (
    station_id bigint not null,
    measurement_date timestamp not null,
    quality_level tinyint comment '
        QN = 1 : only formal inspection;
        QN = 2 : checked according to individual criteria;
        QN = 3 : automatic checking and correction.',
    wind_speed double comment 'wind speed in m/s', 
    wind_direction smallint comment 'wind direction in degree',
    wind_direction_bucket double comment 'Buckets:
        0: [0;45[
        1: [45;90[
        2: [90;135[
        3: [135;180[
        4: [180;225[
        5: [225;270[
        6: [270;315[
        7: [315;360[',
    wind_speed_bucket double comment 'Buckets:
        0: [0;5[
        1: [5;10[
        2: [10;17[
        3: [17;inf[',
    primary key (station_id, measurement_date),
    index idx_station (station_id),
    index idx_date (measurement_date)
);

create table if not exists wind_data_staging (
    station_id bigint not null,
    measurement_date timestamp not null,
    quality_level tinyint comment '
        QN = 1 : only formal inspection;
        QN = 2 : checked according to individual criteria;
        QN = 3 : automatic checking and correction.',
    wind_speed double comment 'wind speed in m/s', 
    wind_direction smallint comment 'wind direction in degree',
    wind_direction_bucket double,
    wind_speed_bucket double,
    index idx_station (station_id),
    index idx_date (measurement_date)
);

-- create a procedure to transfer data from staging to production
delimiter $$
create procedure TransferStagingToProduction()
begin
    -- Transfer and upsert stations
    insert into stations (station_id, date_from, date_until, height, latitude, longitude, name, state, delivery)
    select s.station_id, s.date_from, s.date_until, s.height, s.latitude, s.longitude, s.name, s.state, s.delivery
    from stations_staging s
    on duplicate key update 
        date_from = values(date_from),
        date_until = values(date_until),
        height = values(height),
        latitude = values(latitude),
        longitude = values(longitude),
        name = values(name),
        state = values(state),
        delivery = values(delivery);

    -- Delete transferred rows from staging table
    delete from stations_staging ss
    where exists (
        select *
        from stations s
        where s.station_id = ss.station_id
          and s.date_from = ss.date_from
          and s.date_until = ss.date_until
          and s.height = ss.height
          and s.latitude = ss.latitude
          and s.longitude = ss.longitude
          and s.name = ss.name
          and s.state = ss.state
          and s.delivery = ss.delivery
    );

    -- Transfer and upsert wind_data
    insert into wind_data (station_id, measurement_date, quality_level, wind_speed, wind_direction, wind_direction_bucket, wind_speed_bucket)
    select ws.station_id, ws.measurement_date, ws.quality_level, ws.wind_speed, ws.wind_direction, ws.wind_direction_bucket, ws.wind_speed_bucket
    from wind_data_staging ws
    on duplicate key update 
        quality_level = values(quality_level),
        wind_speed = values(wind_speed),
        wind_direction = values(wind_direction),
        wind_direction_bucket = values(wind_direction_bucket),
        wind_speed_bucket = values(wind_speed_bucket);

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
          and w.wind_direction_bucket = ws.wind_direction_bucket
          and w.wind_speed_bucket = ws.wind_speed_bucket
    );
end$$
delimiter ;

-- schedule the procedure to run regularly using an event
create event if not exists TransferStagingEvent
on schedule every 5 second do
call TransferStagingToProduction();
