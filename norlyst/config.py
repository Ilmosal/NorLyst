"""
This file contains all constants for this program
"""
import os

CLASSIFICATION_COLOR_DICT = {
        1: [62, 177, 65],
        2: [147, 213, 139],
        3: [243, 36, 147],
        4: [255, 111, 111],
        5: [252, 246, 70],
        6: [210, 203, 128],
        7: [181, 99, 11],
        20: [119, 173, 255],
        21: [180, 162, 255],
}

CLASSIFICATION_STRING_DICT = {
        1: '1) Probable Earthquake',
        2: '2) Possible Earthquake',
        3: '3) No Recognizable Station',
        4: '4) No Classification, Small or only observed by FINES',
        5: '5) Probable Explosion',
        6: '6) Possible Explosion at a Mining Site',
        7: '7) Probable Explosion located at a Mining Site',
        20: 'Events with Priority',
        21: 'Important Events',
}

CLASSIFICATION_PRIORITY_DICT = {
        1: -0.5,
        2: -1.5,
        3: -2.5,
        4: -3.5,
        5: -4.5,
        6: -5.5,
        7: -6.5,
        20: 9999,
        21: 999999,
}

WAVEFORM_LOCATOR_CONFIG_FILE = os.path.dirname(os.path.realpath(__file__)) + "/waveform_locations.json"

WAVEFORM_OLD_BUFFER_SIZE = 5
WAVEFORM_PREDICTIVE_BUFFER_SIZE = 5
