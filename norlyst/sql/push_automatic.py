"""
Small script for reading automatic results of our automatic detection software and pushing the events to the database
"""

import smtplib
import sys
import datetime
from nordb.core.nordic import createNordicEvents

if len(sys.argv) < 2:
    print("Not enough arguments!")
    sys.exit()

SERVER = "localhost"
FROM = "nordb@seismo.fi"
TO = ["ilmo.salmenpera@helsinki.fi"]

file_path = open(sys.argv[1], 'r')

n_events, n_failed = createNordicEvents(file_path, 'A')
file_path.close()

if len(n_events) < 1:
    msg_date = datetime.datetime.now()
else:
    msg_date = n_events[0].getOriginTime().val

for n_event in n_events:
    n_event.insert2DB(n_event.solution_type, sys.argv[1].split('/')[-1])

SUBJECT = "Automatic Event Report {0}".format(msg_date.date())
message = "From: {0}\nTo: {1}\nSubject: {2}\n\n".format(FROM, ", ".join(TO), SUBJECT)
message += "New Automatic Events:\n"

if len(n_events) == 0:
    message += " No Automatic Events\n"
else:
    for event in n_events:
        time_string = "{:%Y-%m-%d %H:%M:%S}".format(event.getOriginTime().val)
        message += "ID: {0:9d} ORIGIN TIME: {1} LAT: {2:4.3f} LON: {3:4.3f} MAG: {4}\n".format(event.event_id,
                                                                      time_string,
                                                                      event.getLatitude().val,
                                                                      event.getLongitude().val,
                                                                      event.getMagnitude().val)

message += "\nFailed Events:\n"
if len(n_failed) != 0:
    for fail in n_failed:
        message += fail
else:
    message += " No Failed Events"

server = smtplib.SMTP(SERVER)
server.sendmail(FROM, TO, message)
server.quit()
