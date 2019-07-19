/*
 Tables file for the norlyst programs own database tables in the nordb database. 

-Author table contains information about the author of an analysis
-daily list has lock information about all the events of a day
-event classification has necessary information about an analysis of an event
-event comment contains comments to events
-macroseismic observation contains macroseismic observations from the public form
 */

CREATE TYPE day_status as ENUM ('unfinished', 'finished', 'locked');

CREATE TABLE daily_list(
    id SERIAL PRIMARY KEY,
    author_lock VARCHAR(32),
    daily_list_date DATE,
    current_day_status DAY_STATUS DEFAULT 'unfinished'
);

CREATE TABLE event_classification(
    id SERIAL PRIMARY KEY,
    daily_id INTEGER REFERENCES daily_list(id),
    priority INTEGER,
    event_id INTEGER REFERENCES nordic_event(id),
    classification INTEGER,
    eqex FLOAT,
    certainty VARCHAR(5),
    username VARCHAR(32) REFERENCES nordb_user(username),
    analysis_id INTEGER,
    unimportant BOOLEAN
);

CREATE TABLE event_comment(
    id SERIAL PRIMARY KEY,
    username VARCHAR(32) REFERENCES nordb_user(username) DEFAULT CURRENT_USER,
    event_comment TEXT,
    comment_date TIMESTAMP
);

CREATE TABLE macroseismic_observation(
    id SERIAL PRIMARY KEY,
    observation_datetime TIMESTAMP,
    observation_address TEXT,
    area_description TEXT,
    observed_something BOOLEAN,
    observation TEXT,
    approximate_duration TEXT,
    sound_description TEXT,
    respondent_location TEXT,
    building_age TEXT,
    how_many_storeys TEXT,
    which_storey TEXT,
    respondent_activity TEXT,
    soil_type TEXT,
    soil_thickness TEXT,
    how_many_people TEXT,
    how_many_observed TEXT,
    how_many_frightened TEXT,
    restless_animals BOOLEAN,
    windows_rattled BOOLEAN,
    windows_rattled_loudly BOOLEAN,
    dishes_rattled BOOLEAN,
    dishes_rattled_loudly BOOLEAN,
    liquid_vibrated BOOLEAN,
    liquid_spilled BOOLEAN,
    hanging_objects_swung BOOLEAN,
    hanging_objects_swung_considerably BOOLEAN,
    doors_swung BOOLEAN,
    windows_swung BOOLEAN,
    light_objects_shifted_or_fell BOOLEAN,
    heavy_objects_shifted_or_fell BOOLEAN,
    light_furniture_shook BOOLEAN,
    heavy_furniture_shook BOOLEAN,
    furniture_knocked_over BOOLEAN,
    woodwork_creaked BOOLEAN,
    room_shook BOOLEAN,
    building_shook BOOLEAN
);

CREATE TABLE error_logs(
    id SERIAL PRIMARY KEY,
    daily_list_id INTEGER REFERENCES daily_list(id),
    log_timestamp TIMESTAMP DEFAULT NOW(),
    error_log TEXT      
);

GRANT
    UPDATE
ON
    event_classification (username, priority, analysis_id, important)
TO
    default_users;

GRANT 
    SELECT, INSERT
ON 
    daily_list, error_logs, event_comment, event_classification
TO
    default_users;

GRANT
    UPDATE
ON
    daily_list
TO
    default_users;

GRANT
    USAGE
ON
    daily_list_id_seq, error_logs_id_seq, event_comment_id_seq, event_classification_id_seq
TO
    default_users;
