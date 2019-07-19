"""
This module contains small scripts for managing the database entries for NorLyst application.
"""
import sys
from os.path import realpath
from datetime import datetime

from nordb.core.usernameUtilities import log2nordb
from nordb.database.nordicSearch import searchSameEvents
from nordb.nordic.nordicEvent import NordicEvent
from nordb.core.nordic import createStringMainHeader

DETECTION_FILE_PATH = "/home/lysti/automaija"
AUTOMATIC_SOLUTION_TYPE = 'A'

DOES_DAILY_LIST_EXIST = """
    SELECT
        id
    FROM
        daily_list
    WHERE
        daily_list_date = %(new_date)s
"""

CREATE_NEW_DAILY_LIST = """
    INSERT INTO
        daily_list
        (author_lock, daily_list_date)
    VALUES
        (%(author_lock)s, %(daily_list_date)s)
    RETURNING
        id
"""

CREATE_NEW_EVENT_CLASSIFICATION = """
    INSERT INTO
        event_classification
        (daily_id, priority, event_id, classification,
        eqex, certainty, username, analysis_id)
    VALUES
        (%(daily_id)s, %(priority)s, %(event_id)s, %(classification)s,
        %(eqex)s, %(certainty)s, %(username)s, %(analysis_id)s)

"""

CREATE_NEW_ERROR_LOG = """
    INSERT INTO
        error_logs
        (daily_list_id, error_log)
    VALUES
        (%(daily_list_id)s, %(error_log)s)
"""

SEARCH_FINA_EVENT = """
    SELECT
        nordic_event.id
    FROM
        nordic_event, nordic_header_main
    WHERE
        nordic_event.id = nordic_header_main.event_id
    AND
        solution_type = 'FINA'
    AND
        nordic_header_main.origin_date = %(event_date)s
    AND
        nordic_header_main.origin_time = %(event_time)s
"""

INSERT_WFDISC_TO_FINA_EVENT = """
    INSERT INTO
        nordic_header_waveform (event_id, waveform_info)
    VALUES
        (%(event_id)s, %(waveform_info)s)
"""

def readDetectionFile(file_date = datetime.now()):
    """
    read a detection file for a certain date and push it to the database
    """
    conn = log2nordb()
    cur = conn.cursor()

    try:
        cur.execute(DOES_DAILY_LIST_EXIST, {'new_date':file_date.date()})
        existing_id = cur.fetchone()

        if existing_id is not None:
            daily_list_id = existing_id[0]

        else:
            cur.execute(CREATE_NEW_DAILY_LIST, {'author_lock':None, 'daily_list_date':file_date.date()})
            daily_list_id = cur.fetchone()[0]
            conn.commit()

    except Exception as e:
        conn.close()
        print('Failed to create a new daily list item into the postgresql database: {0}'.format(e))
        sys.exit(1)

    try:
        entries = []
        filename = 'AutomLysti.{0}{1:03d}'.format(file_date.timetuple().tm_year, file_date.timetuple().tm_yday)

        type_number = 1
        detection_file = open("{0}/{1}".format(DETECTION_FILE_PATH, filename), 'r')

        for line in detection_file:
            if line[:2] == '{0})'.format(type_number+1):    #See if the type of the detection changes
                type_number += 1

            if type_number == 4:
                event_time = datetime.strptime(line[11:21] + '00', '%H.%M.%S.%f').time()
                cur.execute(SEARCH_FINA_EVENT, {'event_date':file_date.date(), 'event_time':event_time})
                ans = cur.fetchone()

                if ans is None:
                    raise Exception('No event found for line: {0}'.format(line))

                event_id = ans[0]

                wfdisc_name = detection_file.readline().strip()

                cur.execute(INSERT_WFDISC_TO_FINA_EVENT, {'event_id': event_id, 'waveform_info':wfdisc_name.upper()})

                cur.execute(CREATE_NEW_EVENT_CLASSIFICATION,
                        {
                            'daily_id':daily_list_id,
                            'event_id':event_id,
                            'classification':type_number,
                            'priority':-1,
                            'eqex':None,
                            'certainty':None,
                            'username':'',
                            'analysis_id':-1
                        })

            if len(line) > 80 and line[79] == '1':
                search_event = NordicEvent()
                search_event.main_h.append(createStringMainHeader(line, False))
                found_events = searchSameEvents(search_event)

                if not found_events:
                    raise Exception('No event found for line: {0}'.format(line))

                event_id = -1
                for event in found_events:
                    if event.solution_type == AUTOMATIC_SOLUTION_TYPE:
                        event_id = found_events[0].event_id

                if event_id == -1:
                    raise Exception('No event with correct solution_type found. Required type: {0}'.format(AUTOMATIC_SOLUTION_TYPE))

                detection_file.readline()
                class_vals = readClassificationLine(detection_file.readline())
                if not class_vals:
                    cur.execute(CREATE_NEW_EVENT_CLASSIFICATION,
                            {
                                'daily_id':daily_list_id,
                                'event_id':event_id,
                                'classification':type_number,
                                'priority':-1,
                                'eqex':None,
                                'certainty':None,
                                'username':'',
                                'analysis_id':-1
                            })
                else:
                    cur.execute(CREATE_NEW_EVENT_CLASSIFICATION,
                            {
                                'daily_id':daily_list_id,
                                'event_id':event_id,
                                'classification':type_number,
                                'priority':-1,
                                'eqex':class_vals[1],
                                'certainty':class_vals[1],
                                'username':'',
                                'analysis_id':-1
                            })

    except Exception as e:
        print(e)
        conn.rollback()
        cur.execute(CREATE_NEW_ERROR_LOG,
                   {
                        'daily_list_id': daily_list_id,
                        'error_log': str(e)
                   })

    conn.commit()
    conn.close()

def readClassificationLine(class_line):
    """
    Function for reading a classification line from a detection file
    """
    if not len(class_line.strip()):
        return []

    class_vals = []
    values = class_line.split()

    class_vals.append(float(values[3]))
    class_vals.append(values[4])

    return class_vals

if __name__ == '__main__':
    readDetectionFile(datetime.datetime.now() - datetime.timedelta(days=1))
