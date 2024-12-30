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
