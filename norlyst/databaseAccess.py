"""
This module contains tools for accessing most of the important database operations.
"""
from nordb.core.usernameUtilities import log2nordb
from nordb import getNordic

from misc import EventClassification

class DatabaseAccesser():
    """
    This class holds connection and access functions to the nordb database
    """
    def __init__(self):
        self.__conn = log2nordb()

    def __del__(self):
        self.__conn.close()

    def lockDayForUser(self, lock_date):
        """
        Function for locking a day for a single user. Returns True if locking was successful and False if not
        """
        cur = self.__conn.cursor()

        current_user = self.getCurrentUser()

        cur.execute(LOCK_DAILY_LIST, {'daily_list_date': lock_date})

        ans = cur.fetchone()
        self.__conn.commit()

        if ans is None:
            return False
        elif ans[0] == current_user:
            return True
        else:
            return False

    def getCurrentUser(self):
        """
        Get current database user
        """
        cur = self.__conn.cursor()

        cur.execute(GET_CURRENT_USER)

        return cur.fetchone()[0]

    def unlockDayForUser(self, lock_date):
        """
        Function for unlocking a day. Returns True if unlocking was succesful and False if not.
        """
        cur = self.__conn.cursor()

        cur.execute(UNLOCK_DAILY_LIST, {'daily_list_date': lock_date})

        ans = cur.fetchone()
        self.__conn.commit()

        if ans is None:
            return False
        else:
            return True

    def isDateLockedToUser(self, lock_date):
        """
        Function for checking if the date is locked to this user. Each operation on event_classification and event_comment tables should call this before excuting
        """
        cur = self.__conn.cursor()

        cur.execute(IS_DATE_LOCKED, {'daily_list_date':lock_date})
        ans = cur.fetchone()

        if ans is None:
            return False
        elif ans[0] == self.getCurrentUser():
            return True
        else:
            return False

    def isEventLockedToUser(self, event_classification_id):
        """
        Function for checking if the event is locked to this user. Returns True if the user can modify the event and false if not.
        """
        cur = self.__conn.cursor()

        cur.execute(IS_EVENT_CLASSIFICATION_LOCKED, {'event_classification_id':event_classification_id})
        ans = cur.fetchone()

        if ans is None:
            return False

        return ans[0]

    def getEventClassifications(self, daily_list_date, update_queue):
        """
        Function for fetching event classifications and events from the database, inserting the events inside the classifications and returning them to the program. Returns None if no events are found.
        """
        cur = self.__conn.cursor()

        cur.execute(GET_DAILY_LIST, {'daily_list_date': daily_list_date})
        ans = cur.fetchone()

        if ans is None:
            return []

        daily_id, author_lock = ans

        cur.execute(GET_EVENT_CLASSIFICATIONS, {'daily_list_id': daily_id})
        event_classifications = []
        event_ids = []

        for ec_array in cur.fetchall():
            args = list(ec_array)
            args.append(update_queue)
            event_classifications.append(EventClassification(*args))
            event_ids.append(ec_array[3])
            if ec_array[8] != -1:
                event_ids.append(ec_array[8])

        events = getNordic(event_ids, db_conn = self.__conn)

        for event in events:
            for e_classification in event_classifications:
                if e_classification.event_id == event.event_id:
                    e_classification.setEvent(event)
                    break
                elif e_classification.analysis_id == event.event_id:
                    e_classification.setAnalysis(event)


        return event_classifications

    def analysisIdUpdate(self, event_classification_id, analysis_id):
        """
        Function for updating the analysis_id in the database. Returns True if this was successful and False if not.
        """
        if not self.isEventLockedToUser(event_classification_id):
            return False

        cur = self.__conn.cursor()

        cur.execute(UPDATE_ANALYSIS_ID, {'event_classification_id':event_classification_id, 'analysis_id': analysis_id})
        ans = cur.fetchone()

        if ans is None:
            return False

        self.__conn.commit()
        return ans[0]

    def priorityUpdate(self, event_classification_id, priority):
        """
        function for updating the priority value in the database. Returns True if this was successful and False if not.
        """
        if not self.isEventLockedToUser(event_classification_id):
            return False
        cur = self.__conn.cursor()

        cur.execute(UPDATE_PRIORITY, {'event_classification_id':event_classification_id, 'priority': priority})
        ans = cur.fetchone()

        if ans is None:
            return False

        self.__conn.commit()
        return ans[0]

    def usernameUpdate(self, event_classification_id, username):
        """
        Function for updating the username value in the database. Returns True if this was successful and False if not.
        """
        if not self.isEventLockedToUser(event_classification_id):
            return False

        cur = self.__conn.cursor()

        cur.execute(UPDATE_USERNAME, {'event_classification_id':event_classification_id, 'username': username})
        ans = cur.fetchone()

        if ans is None:
            return False

        self.__conn.commit()
        return ans[0]

    def setEventAsDone(self, event_classification_id, done):
        """
        Set event to be done.
        """
        if not self.isEventLockedToUser(event_classification_id):
            return False

        cur = self.__conn.cursor()

        cur.execute(UPDATE_DONE, {'event_classification_id':event_classification_id})
        ans = cur.fetchone()

        if ans is None:
            return False

        self.__conn.commit()
        return ans[0]


    def setEventAsUnimportant(self, event_classification_id, unimportant = True):
        """
        Set event to be unimportant. Returns True if this was successful and False if not.
        """
        if not self.isEventLockedToUser(event_classification_id):
            return False

        cur = self.__conn.cursor()

        cur.execute(UPDATE_UNIMPORTANT, {'event_classification_id':event_classification_id, 'unimportant': unimportant})
        ans = cur.fetchone()

        if ans is None:
            return False

        self.__conn.commit()
        return ans[0]

GET_DAILY_LIST = """
    SELECT
        id, author_lock
    FROM
        daily_list
    WHERE
        daily_list_date = %(daily_list_date)s
"""

GET_EVENT_CLASSIFICATIONS = """
    SELECT
        id, daily_id, priority, event_id, classification, eqex, certainty, username, analysis_id, unimportant, done
    FROM
        event_classification
    WHERE
        daily_id = %(daily_list_id)s
"""

IS_DATE_LOCKED_TO_USER = """
    SELECT
        1
    FROM
        daily_list
    WHERE
        author_lock = CURRENT_USER
    AND
        daily_list_date = %(daily_list_date)s
"""

IS_DATE_LOCKED = """
    SELECT
        author_lock
    FROM
        daily_list
    WHERE
        daily_list_date = %(daily_list_date)s
"""

LOCK_DAILY_LIST = """
    UPDATE
        daily_list
    SET
        author_lock = COALESCE(author_lock, CURRENT_USER)
    WHERE
        daily_list_date = %(daily_list_date)s
    RETURNING
        author_lock
"""

UNLOCK_DAILY_LIST = """
    UPDATE
        daily_list
    SET
        author_lock = NULL
    WHERE
        daily_list_date = %(daily_list_date)s
    AND
        author_lock = CURRENT_USER
    RETURNING
        author_lock
"""

GET_CURRENT_USER = """
    SELECT
        CURRENT_USER

"""

IS_EVENT_CLASSIFICATION_LOCKED = """
    SELECT
        (author_lock = CURRENT_USER)
    FROM
        daily_list, event_classification
    WHERE
        daily_list.id = event_classification.daily_id
    AND
        event_classification.id = %(event_classification_id)s
"""

UPDATE_ANALYSIS_ID = """
    UPDATE
        event_classification
    SET
        analysis_id = %(analysis_id)s
    WHERE
        id = %(event_classification_id)s
    AND
        (
        SELECT
            author_lock = CURRENT_USER
        FROM
            daily_list, event_classification
        WHERE
            daily_list.id = event_classification.daily_id
        AND
            event_classification.id = %(event_classification_id)s
        )
    RETURNING True
"""

UPDATE_PRIORITY = """
    UPDATE
        event_classification
    SET
        priority = %(priority)s
    WHERE
        id = %(event_classification_id)s
    AND
        (
        SELECT
            author_lock = CURRENT_USER
        FROM
            daily_list, event_classification
        WHERE
            daily_list.id = event_classification.daily_id
        AND
            event_classification.id = %(event_classification_id)s
        )
    RETURNING
        True
"""

UPDATE_USERNAME = """
    UPDATE
        event_classification
    SET
        username = %(username)s
    WHERE
        id = %(event_classification_id)s
    AND
        (
        SELECT
            author_lock = CURRENT_USER
        FROM
            daily_list, event_classification
        WHERE
            daily_list.id = event_classification.daily_id
        AND
            event_classification.id = %(event_classification_id)s
        )
    RETURNING
        True
"""

UPDATE_UNIMPORTANT = """
    UPDATE
        event_classification
    SET
        unimportant = %(unimportant)s
    WHERE
        id = %(event_classification_id)s
    AND
        (
        SELECT
            author_lock = CURRENT_USER
        FROM
            daily_list, event_classification
        WHERE
            daily_list.id = event_classification.daily_id
        AND
            event_classification.id = %(event_classification_id)s
        )
    RETURNING
        True
"""

UPDATE_DONE = """
    UPDATE
        event_classification
    SET
        done = True
    WHERE
        id = %(event_classification_id)s
    AND
        (
        SELECT
            author_lock = CURRENT_USER
        FROM
            daily_list, event_classification
        WHERE
            daily_list.id = event_classification.daily_id
        AND
            event_classification.id = %(event_classification_id)s
        )
    RETURNING
        True
"""



