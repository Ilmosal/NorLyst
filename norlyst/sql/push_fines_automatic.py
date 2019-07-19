"""
Small script for reading automatic results of FINES automatic detection software and pushing the events to the database.
"""
import smtplib
import sys
import datetime
from nordb.nordic.nordicEvent import NordicEvent
from nordb.nordic.nordicMain import NordicMain
from nordb.nordic.nordicData import NordicData

def functionYes():
    if len(sys.argv) < 2:
        print("Not enough arguments!")
        sys.exit()

    SERVER = "localhost"
    FROM = "nordb@seismo.fi"
    TO = ["ilmo.salmenpera@helsinki.fi"]

    file_path = open(sys.argv[1], 'r')
    n_events = []

    event = None
    for line in file_path:
        if event is not None:
            if line[74:78] == '0F':
                main_header = NordicMain()
                main_header.observation_time = datetime.datetime.strptime(sys.argv[3:5] + line[7:10], '%y%j').date()
                main_header.origin_time = datetime.datetime.strptime(line[11:21] + '00', '%H.%M.%S.%f').time()
                main_header.epicenter_latitude = float(line[34:41])
                main_header.epicenter_longitude = float(line[43:50])
                main_header.epicenter_magnitude = float(line[50:55])

                event.main_h.append(main_header)

            if line[72:78] == 'LOCATE':
                data_line = NordicData()
                data_line.origin_date = datetime.datetime.strptime(sys.argv[3:5] + line[7:21] + '00', '%y%j:%H.%M.%S.%f').date()
                data_line.station_code = 'FIN0'

                if len(event.data) == 3:
                    event.insert2DB(solution_type = 'FINA', filename=file_path.split('/')[-1])

        if line[22:25] == 'HYP':
            event = NordicEvent(solution_type = 'FINA')

    file_path.close()

    if len(n_events) < 1:
        msg_date = datetime.datetime.now()
    else:
        msg_date = n_events[0].getOriginTime().val

    for n_event in n_events:
        n_event.insert2DB(n_event.solution_type, sys.argv[1].split('/')[-1])

    SUBJECT = "Automatic FINESS Event Report {0}".format(msg_date.date())
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

print("Imported file: " + __name__)
if __name__ == '__main__':
    functionYes()
