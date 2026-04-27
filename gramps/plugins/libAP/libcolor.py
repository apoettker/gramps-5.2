# -*- coding: utf-8 -*-
#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2020  Alois Poettker
#
#------------------------------------------------------------------------
#
# standard python modules
#
#------------------------------------------------------------------------
import math, colorsys

class Color(object):
    """"""
    IttenC1 = {
        'R': {'CMYK':( 00, 25, 15, 00), 'RGB':(249,208,204), 'HEX': '#f9d0cc', 'name': 'Rot'},
        'G': {'CMYK':( 45, 00, 35, 00), 'RGB':(203,230,215), 'name': 'Grün'},
        'B': {'CMYK':( 30, 15, 00, 00), 'RGB':(189,206,232), 'name': 'Blau'},

        'S': {'CMYK':( 00, 00, 00,100), 'RGB':(  0,  0,  0), 'name': 'Black'},
        'W': {'CMYK':( 00, 00, 00, 00), 'RGB':(255,255,255), 'name': 'White'},
    }
    IttenC2 = {
        'R': {'CMYK':( 00, 45, 30, 00), 'RGB':(244,167,159), 'HEX': '#f4a79f', 'name': 'Rot'},
        'G': {'CMYK':( 25, 00, 20, 00), 'RGB':(155,208,182), 'name': 'Grün'},
        'B': {'CMYK':( 50, 25, 00, 00), 'RGB':(138,173,215), 'name': 'Blau'},
    }
    IttenC3 = {
        'R': {'CMYK':( 00, 65, 50, 00), 'RGB':(238,119,107), 'HEX': '#ee776b', 'name': 'Rot'},
        'G': {'CMYK':( 60, 00, 55, 00), 'RGB':(114,188,139), 'name': 'Grün'},
        'B': {'CMYK':( 65, 40, 00, 00), 'RGB':(100,139,194), 'name': 'Blau'},

        'S': {'CMYK':( 00, 00, 00,100), 'RGB':(  0,  0,  0), 'name': 'Black'},
        'W': {'CMYK':( 00, 00, 00, 00), 'RGB':(255,255,255), 'name': 'White'},
    }
    IttenC4 = {
        'R': {'CMYK':( 00, 85, 70, 00), 'RGB':(226, 72, 68), 'name': 'Rot'},
        'G': {'CMYK':( 80, 00, 75, 00), 'RGB':( 00,165, 97), 'name': 'Grün'},
        'B': {'CMYK':( 85, 50, 00, 00), 'RGB':( 10,113,180), 'name': 'Blau'},
    }
    IttenC5 = {
          'R': {'CMYK':( 00,100,100, 00), 'RGB':(227, 35, 34), 'name': 'Rot'},
        'ROR': {'CMYK':( 00, 95, 90, 00), 'RGB':(231, 67, 33), 'name': 'Rot-Orangerot'},
         'OR': {'CMYK':( 00, 90, 80, 00), 'RGB':(234, 98, 31), 'name': 'Orangerot'},
        'ORO': {'CMYK':( 00, 78, 90, 00), 'RGB':(238,120, 30), 'name': 'Orangerot-Orange'},
          'O': {'CMYK':( 00, 65,100, 00), 'RGB':(241,142, 28), 'name': 'Orange'},
        'OYO': {'CMYK':( 00, 53,100, 00), 'RGB':(247,170, 20), 'name': 'Orange-Gelborange'},
         'YO': {'CMYK':( 00, 40,100, 00), 'RGB':(253,198, 11), 'name': 'Gelborange'},
        'YOY': {'CMYK':( 00, 20,100, 00), 'RGB':(249,214,  6), 'name': 'Gelborange-Gelb'},
          'Y': {'CMYK':( 00, 00,100, 00), 'RGB':(244,229, 00), 'name': 'Gelb'},
        'YGY': {'CMYK':( 30, 00,100, 00), 'RGB':(192,208, 19), 'name': 'Gelb-Gelbgrün'},
         'GY': {'CMYK':( 60, 00,100, 00), 'RGB':(140,187, 38), 'name': 'Gelbgrün'},
        'GYG': {'CMYK':( 80, 00, 95, 00), 'RGB':( 70,165, 65), 'name': 'Gelbgrün-Grün'},
          'G': {'CMYK':(100, 00, 90, 00), 'RGB':( 00,142, 91), 'name': 'Grün'},
        'GBG': {'CMYK':(100, 00, 65, 00), 'RGB':(  3,146,139), 'name': 'Grün-Blaugrün'},
         'BG': {'CMYK':(100, 00, 40, 00), 'RGB':(  6,150,187), 'name': 'Blaugrün'},
        'BGB': {'CMYK':(100, 30, 20, 00), 'RGB':( 24,132,182), 'name': 'Blaugrün-Blau'},
          'B': {'CMYK':(100, 60, 00, 00), 'RGB':( 42,113,176), 'name': 'Blau'},
        'BPB': {'CMYK':(100, 75, 00, 00), 'RGB':( 55, 96,165), 'name': 'Blau-Violettblau'},
         'PB': {'CMYK':(100, 90, 00, 00), 'RGB':( 68, 78,153), 'name': 'Violettblau'},
        'PBP': {'CMYK':( 70, 95, 00, 00), 'RGB':( 89, 68,146), 'name': 'Violettblau-Violett'},
          'P': {'CMYK':( 80,100, 00, 00), 'RGB':(109, 57,139), 'name': 'Violett'},
        'PRP': {'CMYK':( 60,100, 00, 00), 'RGB':(153, 30,132), 'name': 'Violett-Rotviolett'},
         'RP': {'CMYK':( 40,100, 00, 00), 'RGB':(196,  3,125), 'name': 'Rotviolett'},
        'RPR': {'CMYK':( 20,100, 50, 00), 'RGB':(212, 19, 80), 'name': 'Rotviolett-Rot'},

          'S': {'CMYK':( 00, 00, 00,100), 'RGB':(  0,  0,  0), 'name': 'Black'},
          'W': {'CMYK':( 00, 00, 00, 00), 'RGB':(255,255,255), 'name': 'White'},
    }
    IttenC6 = {
        'R': {'CMYK':( 00,100,100, 15), 'RGB':(217, 00, 00), 'name': 'Rot'},
        'G': {'CMYK':(100, 00, 90, 15), 'RGB':( 00,217, 22), 'name': 'Grün'},
        'B': {'CMYK':(100, 90, 00, 15), 'RGB':( 00, 22,217), 'name': 'Blau'},
    }
    IttenC7 = {
        'R': {'CMYK':( 00,100,100, 30), 'RGB':(179, 00, 00), 'name': 'Rot'},
        'G': {'CMYK':(100, 00, 90, 30), 'RGB':( 00,179, 18), 'name': 'Grün'},
        'B': {'CMYK':(100, 90, 00, 25), 'RGB':(  1, 73,132), 'name': 'Blau'},

        'S': {'CMYK':( 00, 00, 00,100), 'RGB':(  0,  0,  0), 'name': 'Black'},
        'W': {'CMYK':( 00, 00, 00, 00), 'RGB':(255,255,255), 'name': 'White'},
    }
    IttenC8 = {
        'R': {'CMYK':( 00,100,100, 45), 'RGB':(100, 00, 00), 'name': 'Rot'},
        'G': {'CMYK':(100, 00, 90, 45), 'RGB':( 00,140, 14), 'name': 'Grün'},
        'B': {'CMYK':(100, 90, 00, 45), 'RGB':( 00, 14,140), 'name': 'Blau'},
    }
    IttenC9 = {
        'R': {'CMYK':( 00,100,100, 60), 'RGB':(120, 14, 18), 'name': 'Rot'},
        'G': {'CMYK':(100, 00, 90, 60), 'RGB':( 00, 80, 41), 'name': 'Grün'},
        'B': {'CMYK':(100, 90, 00, 60), 'RGB':( 00, 47, 91), 'name': 'Blau'},

        'S': {'CMYK':( 00, 00, 00,100), 'RGB':(  0,  0,  0), 'name': 'Black'},
        'W': {'CMYK':( 00, 00, 00, 00), 'RGB':(255,255,255), 'name': 'White'},
    }
    CIELAB = {  # CieLAB-Circle max. Chromazität
        # https://de.wikipedia.org/wiki/Lab-Farbraum
         10 : {'Lab':(50,   74,   13), 'CMYK':(  2, 96, 31,1), 'RGB':(188, 00, 78)},
         20 : {'Lab':(50,   71,   26), 'CMYK':(  3, 94, 53,1), 'RGB':(187, 00, 61)},
         30 : {'Lab':(50,   69,   40), 'CMYK':(  3, 94, 73,1), 'RGB':(200, 39, 53)},
         40 : {'Lab':(50,   61,   51), 'CMYK':(  8, 88, 92,1), 'RGB':(225, 44, 28)},
         50 : {'Lab':(60,   48,   58), 'CMYK':(  3, 69, 88,0), 'RGB':(246, 90, 20)},
         60 : {'Lab':(60,   38,   65), 'CMYK':( 10, 63,100,2), 'RGB':(255,128, 00)},
         70 : {'Lab':(70,   26,   71), 'CMYK':(  6, 46, 94,1), 'RGB':(255,157, 00), 'HEX':('#ff9e00')},
         80 : {'Lab':(75,   14,   79), 'CMYK':(  9, 33, 99,1), 'RGB':(255,199, 00)},
         90 : {'Lab':(85,    0,   90), 'CMYK':(  7, 13, 99,0), 'RGB':(255,223, 00)},
        100 : {'Lab':(80,-13.9,   79), 'CMYK':( 28,  7, 98,0), 'RGB':(198,205, 00)},
        110 : {'Lab':(75,-23.9,   66), 'CMYK':( 43,  3, 95,0), 'RGB':(158,197, 00), 'HEX':('#9ec500')},
        120 : {'Lab':(70,-32.5,   56), 'CMYK':( 55,  2, 92,0), 'RGB':(106,191, 00)},
        130 : {'Lab':(60,-41.8,   50), 'CMYK':( 72,  9,100,1), 'RGB':( 70,179, 31)},
        140 : {'Lab':(60,-49.8,   42), 'CMYK':( 77,  2, 96,0), 'RGB':( 00,168, 44), 'HEX':('#00a82c')},
        150 : {'Lab':(55,-56.3,   33), 'CMYK':( 87,  6, 94,1), 'RGB':( 00,157, 56)},
        160 : {'Lab':(50,-65.8,   24), 'CMYK':( 99,  7, 92,1), 'RGB':( 00,145, 68)},
        170 : {'Lab':(50,-64.0,   11), 'CMYK':( 99,  8, 76,1), 'RGB':( 00,144, 96)},
        180 : {'Lab':(50,-60.0,    0), 'CMYK':( 99,  9, 64,1), 'RGB':( 00,145,117)},
        190 : {'Lab':(50,-59.1,-10.4), 'CMYK':(100,  9, 54,1), 'RGB':( 00,143,134), 'HEX':('#008f86')},
        200 : {'Lab':(50,-56.4,-20.5), 'CMYK':(100,  9, 42,2), 'RGB':( 00,227,145)},
        210 : {'Lab':(55,-47.6,-27.5), 'CMYK':( 96,  6, 31,1), 'RGB':( 00,141,169)},
        220 : {'Lab':(55,-46.0,-38.6), 'CMYK':(100,  5, 17,0), 'RGB':( 00,140,183)},
        230 : {'Lab':(60,-38.6,-46.0), 'CMYK':( 93,  1,  4,0), 'RGB':( 00,125,181), 'HEX':('#007db5')},
        240 : {'Lab':(55,-30.0,-52.0), 'CMYK':( 95, 16,  0,0), 'RGB':( 00,109,172)},
        250 : {'Lab':(45,-18.8,-51.7), 'CMYK':( 99, 39,  0,0), 'RGB':( 00,107,187)},
        260 : {'Lab':(45, -8.7,-49.2), 'CMYK':( 90, 47,  0,0), 'RGB':( 00, 92,185)},
        270 : {'Lab':(40,    0,-50.0), 'CMYK':( 91, 59,  0,0), 'RGB':( 00, 87,179)},
        280 : {'Lab':(35,    9,-49.2), 'CMYK':( 92, 71,  0,0), 'RGB':( 00, 81,185)},
        290 : {'Lab':(30,   17,-47.0), 'CMYK':( 92, 81,  2,0), 'RGB':( 55, 74,181)},
        300 : {'Lab':(30,   25,-43.3), 'CMYK':( 84, 86,  3,1), 'RGB':(104, 76,186)},
        310 : {'Lab':(30,   35,-42.1), 'CMYK':( 78, 92,  0,1), 'RGB':(125, 69,168)},
        320 : {'Lab':(35,   42,-35.4), 'CMYK':( 63, 91,  0,0), 'RGB':(140, 61,157)},
        330 : {'Lab':(40,   48,-27.5), 'CMYK':( 49, 89,  1,0), 'RGB':(159, 43,149)},
        340 : {'Lab':(40,   56,-20.5), 'CMYK':( 91, 94,  4,1), 'RGB':(172, 25,131)},
        350 : {'Lab':(45,   69,-12.2), 'CMYK':( 21, 97,  2,0), 'RGB':(183, 00,115)},
        360 : {'Lab':(50,   75,    0), 'CMYK':(  3, 96,  0,0), 'RGB':(188, 00, 96)}
    }
    LabRGB = { # CieLAB-Circle
         10: {'RGB':(188, 00, 78)},
         20: {'RGB':(187, 00, 61)},
         30: {'RGB':(200, 39, 53)},
         40: {'RGB':(225, 44, 28)},
         50: {'RGB':(246, 90, 20)},
         60: {'RGB':(255,128, 00)},
         70: {'RGB':(255,157, 00)},
         80: {'RGB':(255,199, 00)},
         90: {'RGB':(255,223, 00)},
        100: {'RGB':(198,205, 00)},
        110: {'RGB':(158,197, 00)},
        120: {'RGB':(106,191, 00)},
        130: {'RGB':( 70,179, 31)},
        140: {'RGB':( 00,168, 44)},
        150: {'RGB':( 00,157, 56)},
        160: {'RGB':( 00,145, 68)},
        170: {'RGB':( 00,144, 96)},
        180: {'RGB':( 00,145,117)},
        190: {'RGB':( 00,143,134)},
        200: {'RGB':( 00,144,155)},
        210: {'RGB':( 00,141,169)},
        220: {'RGB':( 00,140,183)},
        230: {'RGB':( 00,125,181)},
        240: {'RGB':( 00,109,172)},
        250: {'RGB':( 00,107,187)},
        260: {'RGB':( 00, 92,185)},
        270: {'RGB':( 00, 87,179)},
        280: {'RGB':( 00, 81,185)},
        290: {'RGB':( 55, 74,181)},
        300: {'RGB':(104, 76,186)},
        310: {'RGB':(125, 69,168)},
        320: {'RGB':(140, 61,157)},
        330: {'RGB':(159, 43,149)},
        340: {'RGB':(172, 25,131)},
        350: {'RGB':(183, 00,115)},
        360: {'RGB':(188, 00, 96)}
    }

    def __init__(self):
        """
        Initialize the color element class.
        """
        self.BACKGROUND = {}
        # rot, grün, blau
        self.BACKGROUND['Itten'] = {
            'C1': {'R': self.IttenC1['R']['RGB'], 'G': self.IttenC1['G']['RGB'], 'B': self.IttenC1['B']['RGB']},
            'C2': {'R': self.IttenC2['R']['RGB'], 'G': self.IttenC2['G']['RGB'], 'B': self.IttenC2['B']['RGB']},
            'C3': {'R': self.IttenC3['R']['RGB'], 'G': self.IttenC3['G']['RGB'], 'B': self.IttenC3['B']['RGB']},
            'C4': {'R': self.IttenC4['R']['RGB'], 'G': self.IttenC4['G']['RGB'], 'B': self.IttenC4['B']['RGB']},
            'C5': {'R': self.IttenC5['R']['RGB'], 'G': self.IttenC5['G']['RGB'], 'B': self.IttenC5['B']['RGB']},
            'C6': {'R': self.IttenC6['R']['RGB'], 'G': self.IttenC6['G']['RGB'], 'B': self.IttenC6['B']['RGB']},
            'C7': {'R': self.IttenC7['R']['RGB'], 'G': self.IttenC7['G']['RGB'], 'B': self.IttenC7['B']['RGB']},
            'C8': {'R': self.IttenC8['R']['RGB'], 'G': self.IttenC8['G']['RGB'], 'B': self.IttenC8['B']['RGB']},
            'C9': {'R': self.IttenC9['R']['RGB'], 'G': self.IttenC9['G']['RGB'], 'B': self.IttenC9['B']['RGB']},
        }
        """
        # 1x Pro + 6x Gen: rot, Orange, gelb, gelb-grün, grün, grün-blau, blau
        self.BACKGROUND['Itten07C1'] = [
            self.IttenC1[ 1], self.IttenC1[ 3], self.IttenC1[ 5], self.IttenC1[ 7],
            self.IttenC1[ 9], self.IttenC1[11], self.IttenC1[13]
        ]
        self.BACKGROUND['Itten07C3'] = [
            self.IttenC3[ 1], self.IttenC3[ 3], self.IttenC3[ 5], self.IttenC3[ 7],
            self.IttenC3[ 9], self.IttenC3[11], self.IttenC3[13]
        ]
        self.BACKGROUND['Itten07C5'] = [
            self.IttenC5['R'], self.IttenC5['O'], self.IttenC5['Y'], self.IttenC5['G'],
            self.IttenC5['BG'], self.IttenC5['B'], self.IttenC5['P']
        ]

        self.BACKGROUND['LabCMYK07'] = [
            self.CIELAB[40], self.CIELAB[70], self.CIELAB[90], self.CIELAB[130], \
            self.CIELAB[160], self.CIELAB[200], self.CIELAB[240]
        ]
        # 1x Pro + 7x Gen
        self.BACKGROUND['LabRGB08'] = [
            self._colorLabRGB[40], self._colorLabRGB[60], self._colorLabRGB[90], self._colorLabRGB[130], \
            self._colorLabRGB[190], self._colorLabRGB[230], self._colorLabRGB[280], self._colorLabRGB[330]
        ]
        self.BACKGROUND['LabCMYK08'] = [
            self.CIELAB[40], self.CIELAB[60], self.CIELAB[90], self.CIELAB[130], \
            self.CIELAB[190], self.CIELAB[230], self.CIELAB[280], self.CIELAB[330]
        ]
        """
        # 1x Pro + 9x Gen
        self.BACKGROUND['LabRGB10'] = [
            self.CIELAB[ 40]['RGB'], self.CIELAB[ 50]['RGB'], self.CIELAB[ 70]['RGB'], \
            self.CIELAB[ 90]['RGB'], self.CIELAB[110]['RGB'], self.CIELAB[140]['RGB'], \
            self.CIELAB[190]['RGB'], self.CIELAB[230]['RGB'], self.CIELAB[270]['RGB'], \
            self.CIELAB[310]['RGB']
        ]
        self.BACKGROUND['Itten10C5'] = [
            self.IttenC5['R'], self.IttenC5['OR'], self.IttenC5['O'], self.IttenC5['YO'],
            self.IttenC5['Y'], self.IttenC5['GY'], self.IttenC5['G'], self.IttenC5['BG'],
            self.IttenC5['B'], self.IttenC5['PB'],
        ]

        # 1x Pro + 10x Gen
        self.BACKGROUND['LabRGB11'] = [
            self.CIELAB[ 40]['RGB'], self.CIELAB[ 50]['RGB'], self.CIELAB[ 70]['RGB'], self.CIELAB[ 90]['RGB'], \
            self.CIELAB[110]['RGB'], self.CIELAB[140]['RGB'], self.CIELAB[190]['RGB'], self.CIELAB[230]['RGB'], \
            self.CIELAB[270]['RGB'], self.CIELAB[310]['RGB'], self.CIELAB[340]['RGB']
        ]

        """
        # 1x Pro + 10x Gen
        self.BACKGROUND['Itten11C1'] = [
            self.IttenC1[ 1], self.IttenC1[ 3], self.IttenC1[ 5], self.IttenC1[ 7],
            self.IttenC1[ 9], self.IttenC1[11], self.IttenC1[13], self.IttenC1[15],
            self.IttenC1[17], self.IttenC1[19], self.IttenC1[21]
        ]
        self.BACKGROUND['Itten11C3'] = [
            self.IttenC3[ 1], self.IttenC3[ 3], self.IttenC3[ 5], self.IttenC3[ 7],
            self.IttenC3[ 9], self.IttenC3[11], self.IttenC3[13], self.IttenC3[15],
            self.IttenC3[17], self.IttenC3[19], self.IttenC3[21]
        ]
        # 1x Pro + 12x Gen
        self.BACKGROUND['LabCMYK13'] = [
            self.CIELAB[40], self.CIELAB[70], self.CIELAB[90], self.CIELAB[130], \
            self.CIELAB[160], self.CIELAB[190], self.CIELAB[220], self.CIELAB[250],
            self.CIELAB[280], self.CIELAB[310], self.CIELAB[340], self.CIELAB[360], \
            self.CIELAB[30]
        ]
        # 1x Pro + 13x Gen
        self.BACKGROUND['Itten14C1'] = [
            self.IttenC1[ 1], self.IttenC1[ 3], self.IttenC1[ 5], self.IttenC1[ 7], \
            self.IttenC1[ 9], self.IttenC1[10], self.IttenC1[11], self.IttenC1[12], \
            self.IttenC1[13], self.IttenC1[14], self.IttenC1[15], self.IttenC1[17], \
            self.IttenC1[19], self.IttenC1[21]
        ]
        """
        # 1x Pro + 13x Gen
        self.BACKGROUND['Itten12C5'] = [
            self.IttenC5['R'], self.IttenC5['OR'], self.IttenC5['O'], self.IttenC5['YO'],
            self.IttenC5['Y'], self.IttenC5['GY'], self.IttenC5['G'], self.IttenC5['BG'],
            self.IttenC5['B'], self.IttenC5['PB'], self.IttenC5['P'], self.IttenC5['RP']
        ]
        # 1x Pro + 13x Gen
        self.BACKGROUND['LabRGB14'] = [
            self.CIELAB[ 40]['RGB'], self.CIELAB[ 50]['RGB'], self.CIELAB[ 60]['RGB'], self.CIELAB[ 80]['RGB'], \
            self.CIELAB[100]['RGB'], self.CIELAB[120]['RGB'], self.CIELAB[140]['RGB'], self.CIELAB[160]['RGB'], \
            self.CIELAB[190]['RGB'], self.CIELAB[230]['RGB'], self.CIELAB[270]['RGB'], self.CIELAB[300]['RGB'], \
            self.CIELAB[330]['RGB'], self.CIELAB[360]['RGB'],
        ]

        # 1x Pro + 19x Gen
        self.BACKGROUND['LabRGB20'] = [
            self.CIELAB[ 40]['RGB'], self.CIELAB[ 50]['RGB'], self.CIELAB[ 70]['RGB'], self.CIELAB[ 90]['RGB'], \
            self.CIELAB[100]['RGB'], self.CIELAB[120]['RGB'], self.CIELAB[130]['RGB'], self.CIELAB[140]['RGB'], \
            self.CIELAB[160]['RGB'], self.CIELAB[190]['RGB'], self.CIELAB[210]['RGB'], self.CIELAB[230]['RGB'], \
            self.CIELAB[260]['RGB'], self.CIELAB[280]['RGB'], self.CIELAB[300]['RGB'], self.CIELAB[310]['RGB'], \
            self.CIELAB[330]['RGB'], self.CIELAB[350]['RGB'], self.CIELAB[ 10]['RGB'], self.CIELAB[ 30]['RGB'],
        ]
        """
        # 1x Pro + 19x Gen
        self.BACKGROUND['LabCMYK20'] = [
            self.CIELAB[40], self.CIELAB[60], self.CIELAB[80], self.CIELAB[90], \
            self.CIELAB[100], self.CIELAB[110], self.CIELAB[130], self.CIELAB[150], \
            self.CIELAB[170], self.CIELAB[190], self.CIELAB[210], self.CIELAB[230], \
            self.CIELAB[250], self.CIELAB[270], self.CIELAB[290], self.CIELAB[310], \
            self.CIELAB[330], self.CIELAB[350], self.CIELAB[10], self.CIELAB[30]
        ]
        # 1x Pro + 22x Gen
        self.BACKGROUND['Itten23C1'] = [
            self.IttenC1[ 1], self.IttenC1[ 2], self.IttenC1[ 3], self.IttenC1[ 4], \
            self.IttenC1[ 5], self.IttenC1[ 6], self.IttenC1[ 7], self.IttenC1[ 8], \
            self.IttenC1[ 9], self.IttenC1[10], self.IttenC1[11], self.IttenC1[12], \
            self.IttenC1[11], self.IttenC1[14], self.IttenC1[15], self.IttenC1[16], \
            self.IttenC1[17], self.IttenC1[18], self.IttenC1[19], self.IttenC1[20],
            self.IttenC1[21], self.IttenC1[22], self.IttenC1[23]
        ]
        self.BACKGROUND['Itten24C5'] = [
            self.IttenC5['R'], self.IttenC5['ROR'], self.IttenC5['OR'], self.IttenC5['ORO'],
            self.IttenC5['O'], self.IttenC5['OYO'], self.IttenC5['YO'], self.IttenC5['YOY'],
            self.IttenC5['Y'], self.IttenC5['YGY'], self.IttenC5['GY'], self.IttenC5['GYG'],
            self.IttenC5['G'], self.IttenC5['GBG'], self.IttenC5['BG'], self.IttenC5['BGB'],
            self.IttenC5['B'], self.IttenC5['BPB'], self.IttenC5['PB'], self.IttenC5['PBP'],
            self.IttenC5['P'], self.IttenC5['PRP'], self.IttenC5['RP'], self.IttenC5['RPR']
        ]
        # 1x Pro + 35x Gen
        self.BACKGROUND['LabRGB36'] = [
            self._colorLabRGB[40], self._colorLabRGB[50], self._colorLabRGB[60], self._colorLabRGB[70], \
            self._colorLabRGB[80], self._colorLabRGB[90], self._colorLabRGB[100], self._colorLabRGB[110], \
            self._colorLabRGB[120], self._colorLabRGB[130], self._colorLabRGB[140], self._colorLabRGB[150], \
            self._colorLabRGB[160], self._colorLabRGB[170], self._colorLabRGB[180], self._colorLabRGB[190], \
            self._colorLabRGB[200], self._colorLabRGB[210], self._colorLabRGB[220], self._colorLabRGB[230], \
            self._colorLabRGB[240], self._colorLabRGB[250], self._colorLabRGB[260], self._colorLabRGB[270], \
            self._colorLabRGB[280], self._colorLabRGB[290], self._colorLabRGB[300], self._colorLabRGB[310], \
            self._colorLabRGB[320], self._colorLabRGB[330], self._colorLabRGB[340], self._colorLabRGB[350], \
            self._colorLabRGB[360], self._colorLabRGB[10], self._colorLabRGB[20], self._colorLabRGB[30]
        ]
        # 1x Pro + 35x Gen
        self.BACKGROUND['LabCMYK36'] = [
            self.CIELAB[40], self.CIELAB[50], self.CIELAB[60], self.CIELAB[70], \
            self.CIELAB[80], self.CIELAB[90], self.CIELAB[100], self.CIELAB[110], \
            self.CIELAB[120], self.CIELAB[130], self.CIELAB[140], self.CIELAB[150], \
            self.CIELAB[160], self.CIELAB[170], self.CIELAB[180], self.CIELAB[190], \
            self.CIELAB[200], self.CIELAB[210], self.CIELAB[220], self.CIELAB[230], \
            self.CIELAB[240], self.CIELAB[250], self.CIELAB[260], self.CIELAB[270], \
            self.CIELAB[280], self.CIELAB[290], self.CIELAB[300], self.CIELAB[310], \
            self.CIELAB[320], self.CIELAB[330], self.CIELAB[340], self.CIELAB[350], \
            self.CIELAB[360], self.CIELAB[10], self.CIELAB[20], self.CIELAB[30]
        ]
        """
        self.defaultMale = '#E0E0FF'   # light blue
        self.MALE = '#000A66'   # dark blue
        self.defaultFemale = '#FFE0E0'   # light red
        self.FEMALE = '#660000'   # dark red
        self.defaultFamily = '#FFFFCC'   # light yellow
        self.linkWIDTH = 4

        pass

    # HEX functions ----------------------------------------------------------------------------------------- #
    def HEXtoRGB(self, hexValue='#000000'):
        hexValue = hexValue.lstrip('#')
        lhv = len(hexValue)

        return tuple(int(hexValue[i:i + lhv // 3], 16) for i in range(0, lhv, lhv // 3))

    def HEXtoHLS(self, hexValue='#000000'):
        rgbColor = self.HEXtoRGB(hexValue) # rgbColor in [0 ... 1]
        return colorsys.rgb_to_hls(rgbColor[0] /255, rgbColor[1] /255, rgbColor[2] /255)

    def HEXtoLAB(self, hexValue='#000000'):
        """"""
        rgbColor = self.HEXtoRGB(hexValue)
        return self.RGBtoLAB(rgbColor)

    # RGB functions ----------------------------------------------------------------------------------------- #
    def RGBtoHEX(self, rgbColor=[0,0,0]):
        return '#%02x%02x%02x' % tuple(rgbColor)

    def RGBtoHLS(self, rgbColor=[0,0,0]):
        return colorsys.rgb_to_hls(rgbColor)

    # https://stackoverflow.com/questions/7880264/convert-lab-color-to-rgb
    def RGBtoLAB(self, rgbColor=[0,0,0], rgb_scale=255):
        """"""
        _debug_ = False

        RGB = [0, 0, 0]
        for num, value in enumerate(rgbColor):
            value = float(value) / rgb_scale
            RGB[num] = ((value + 0.055) / 1.055) ** 2.4 \
                if value > 0.04045 else \
                value / 12.92
            RGB[num] *= 100
        if _debug_: print('RGB : %s' % RGB)

        # Transformation from RGB to XYZ
        XYZ = [0.0, 0.0, 0.0]
        XYZ[0] = RGB[0] * 0.4124564 + RGB[1] * 0.3575761 + RGB[2] * 0.1804375
        XYZ[1] = RGB[0] * 0.2126729 + RGB[1] * 0.7151522 + RGB[2] * 0.0721750
        XYZ[2] = RGB[0] * 0.0193339 + RGB[1] * 0.1191920 + RGB[2] * 0.9503041
        if _debug_: print('XYZi : %s' % XYZ)

        # Observer = 10°, Illuminant = D65 # Observer= 2°, Illuminant= D65
        XYZ[0] = XYZ[0] / 94.811    # 95.047
        XYZ[1] = XYZ[1] / 100.0     # 100.000
        XYZ[2] = XYZ[2] / 107.304   # 108.883
        if _debug_: print('XYZii : %s' % XYZ)

        for num, value in enumerate(XYZ):
            XYZ[num] = value ** (1/3) \
                if value > 0.008856 else \
                (7.787 * value) + (16 / 116)
        if _debug_: print('XYZiii : %s' % XYZ)

        # Transformation from XYZ to LAB
        LAB = [0, 0, 0]
        LAB[0] = (116 * XYZ[1]) - 16       # = L*
        LAB[1] = 500 * (XYZ[0] - XYZ[1])   # = a*
        LAB[2] = 200 * (XYZ[1] - XYZ[2])   # = b*

        return LAB

    # HLS functions ----------------------------------------------------------------------------------------- #
    def HLStoHEX(self, hlscolor=[0,0,0]):
        rgbcolor = colorsys.hls_to_rgb(hlscolor[0], hlscolor[1], hlscolor[2]) # hlscolor in [0 ... 1]!
        rgbcolor = [round(rgb *255) for rgb in rgbcolor] # rgbcolor in [0 ... 255]!
        return '#%02x%02x%02x' % tuple(rgbcolor)

    def HLStoRGB(self, hlscolor=[0,0,0]):
        rgbcolor = colorsys.hls_to_rgb(hlscolor[0], hlscolor[1], hlscolor[2]) # hlscolor in [0 ... 1]!
        return [round(rgb *255) for rgb in rgbcolor] # rgbcolor in [0 ... 255]!

    # CMYK functions ---------------------------------------------------------------------------------------- #
    def CMYKtoHEX(self, cmykColor=[0,0,0,0], cmyk_scale=100):
        rgbColor = self.CMYKtoRGB(cmykColor)
        return '#%02x%02x%02x' % tuple(rgbColor)

    def CMYKtoRGB(self, cmykColor=[0,0,0,0], cmyk_scale=100, rgb_scale=255):
        """"""
        [c,m,y,k] = cmykColor
        r = rgb_scale * (1.0 - c / float(cmyk_scale)) * (1.0 - k / float(cmyk_scale))
        g = rgb_scale * (1.0 - m / float(cmyk_scale)) * (1.0 - k / float(cmyk_scale))
        b = rgb_scale * (1.0 - y / float(cmyk_scale)) * (1.0 - k / float(cmyk_scale))

        return (int(r), int(g), int(b))

    def CMYKtoLAB(self, cmykColor=[0,0,0,0], cmyk_scale=100):
        """"""
        rgbColor = self.CMYKtoRGB(cmykColor)
        return self.RGBtoLAB(rgbColor)

    # LAB functions ----------------------------------------------------------------------------------------- #
    def LABtoHEX(self, labColor=[0,0,0,0]):
        """"""
        rgbColor = self.LABtoRGB(labColor)
        return self.RGBtoHEX(rgbColor)

    def LABtoRGB(self, labColor=[0,0,0], rgb_scale=255):
        """"""
        _debug_ = False

        # Transformation from LAB to XYZ
        if labColor[0] > 100: labColor[0] = 100
        Y = (labColor[0] + 16) / 116
        X = labColor[1] / 500 + Y
        Z = Y - (labColor[2] / 200)
        XYZ = [X, Y, Z]
        if _debug_: print('XYZiii : %s' % XYZ)

        for num, value in enumerate(XYZ):
            if value ** 3 > 0.008856: XYZ[num] = value ** 3
            else: XYZ[num] = (value - 16 / 116) / 7.787
        if _debug_: print('XYZii : %s' % XYZ)

        # Observer = 10°, Illuminant= D65  # Observer= 2°, Illuminant= D65
        XYZ[0] = XYZ[0] * 94.811  / 100   # 95.047
        # XYZ[1] = XYZ[1] * 100.0   / 100   # 100.000
        XYZ[2] = XYZ[2] * 107.304 / 100   # 108.883
        if _debug_: print('XYZi : %s' % XYZ)

        # Transformation from XYZ to RGB
        R = XYZ[0] *  3.2406 + XYZ[1] * -1.5372 + XYZ[2] * -0.4986;
        G = XYZ[0] * -0.9689 + XYZ[1] *  1.8758 + XYZ[2] *  0.0415;
        B = XYZ[0] *  0.0557 + XYZ[1] * -0.2040 + XYZ[2] *  1.0570;
        RGB = [R, G, B]
        if _debug_: print('RGB : %s' % RGB)

        for num, value in enumerate(RGB):
            if value > 0.0031308: RGB[num] = 1.055 * (value ** (1/2.4)) - 0.055
            else: RGB[num] = value * 12.92
            RGB[num] = abs(int(RGB[num] * rgb_scale))   # values maybee negative!
            if RGB[num] > rgb_scale: RGB[num] = rgb_scale

        return RGB

    def string2name(self, string, threshold):
        # convert the 'colors' string to a dictionary of names and colors
        name_color = {}
        tmp = string.split(' ')
        while len(tmp) > 1:
            surname = tmp.pop(0)
            background_color = tmp.pop(0)
            rgb_color = self.HEXtoRGB(background_color)
            label_color = '#000000' if self.isLight(rgb_color, threshold) else '#FFFFFF'
            name_color[surname] = [background_color, label_color]

        return name_color

    def isLight(self, rgbColor=[0,128,255], threshold=127.5):
        """"""
        [r,g,b] = rgbColor
        hsp = math.sqrt(0.299 * (r * r) + 0.587 * (g * g) + 0.114 * (b * b))

        return hsp > threshold # Org: 127.5   # isLight!

    def getColorStyle(max_generations):
        """"""
        color_style = 'LabRGB20'   # Default
        if max_generations < 11: color_style = 'LabRGB10'
        elif max_generations < 15: color_style = 'LabRGB14'
        elif max_generations < 21: color_style = 'LabRGB20'

        return color_style

""" Backup:
    _colorLabRGB = {
        10 : {'Lab':(55,      79,   14), 'RGB':(248, 29,112)},
        20 : {'Lab':(55,      80,   29), 'RGB':(252, 51, 88)},
        30 : {'Lab':(55,      78,   45), 'RGB':(252, 30, 60)},
        40 : {'Lab':(55,      80,   68), 'RGB':(255, 16, 13)},
        50 : {'Lab':(60,      61,   73), 'RGB':(250, 87,  0)},
        60 : {'Lab':(65,      43,   74), 'RGB':(243,123,  0)},
        70 : {'Lab':(75,      29,   80), 'RGB':(255,163,  0)},
        80 : {'Lab':(80,      14,   79), 'RGB':(249,187, 21)},
        90 : {'Lab':(90,       0,   85), 'RGB':(255,224, 32)},
       100 : {'Lab':(95,   -15.6,   89), 'RGB':(245,247, 24)},
       110 : {'Lab':(95,   -32.5,   89), 'RGB':(215,255, 13)},
       120 : {'Lab':(90,   -47.5,   82), 'RGB':(166,249, 29)},
       130 : {'Lab':(90,   -67.5,   80), 'RGB':(106,255, 34)},
       140 : {'Lab':(85,   -72.8,   61), 'RGB':(25,245, 83)},
       150 : {'Lab':(85,   -69.3,   40), 'RGB':( 0,244,131)},
       160 : {'Lab':(85,   -65.8,   24), 'RGB':( 0,243,163)},
       170 : {'Lab':(90,   -59.1,   10), 'RGB':(48,255,205)},
       180 : {'Lab':(90,   -55.0,    0), 'RGB':(46,255,224)},
       190 : {'Lab':(90,   -49.2, -8.7), 'RGB':(64,253,242)},
       200 : {'Lab':(90,   -47.0,-17.1), 'RGB':(47,252,255)},
       210 : {'Lab':(85,   -39.0,-22.5), 'RGB':(67,234,253)},
       220 : {'Lab':(80,   -34.5,-28.9), 'RGB':(53,217,251)},
       230 : {'Lab':(75,   -28.9,-34.5), 'RGB':(44,201,246)},
       240 : {'Lab':(70,   -25.0,-43.3), 'RGB':( 0,187,249)},
       250 : {'Lab':(70,   -17.1,-47.0), 'RGB':(52,183,255)},
       260 : {'Lab':(65,    -9.6,-54.2), 'RGB':(44,166,255)},
       270 : {'Lab':(55.0,  -65,     0), 'RGB':( 0,136,245)},
       280 : {'Lab':(50.13, -73,     9), 'RGB':(14,117,248)},
       290 : {'Lab':(40.33, -89,     3), 'RGB':( 0, 81,245)},
       300 : {'Lab':(30.63,-108,     3), 'RGB':( 0, 21,250)},
       310 : {'Lab':(45.74, -88,     1), 'RGB':(155, 33,255)},
       320 : {'Lab':(50.84, -70,     7), 'RGB':(203,  0,244)},
       330 : {'Lab':(60.91, -52,     5), 'RGB':(255, 18,239)},
       340 : {'Lab':(60.85, -30,     8), 'RGB':(255, 42,202)},
       350 : {'Lab':(55.84, -14,     8), 'RGB':(247,  0,161)},
       360 : {'Lab':(55,     80,     0), 'RGB':(246, 27,136)}
    }
"""
