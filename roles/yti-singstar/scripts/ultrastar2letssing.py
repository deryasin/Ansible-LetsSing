#!/usr/bin/env python3
import xml.etree.cElementTree as ET
from xml.dom import minidom
import argparse
import sys
import re
import os
import shutil
import io
from PIL import Image

parser = argparse.ArgumentParser()
parser.add_argument('--input', required=True, help='Ultrastar text file')
parser.add_argument('--pitch', default=48, help="Note Correction, 48 default, use -70 for notes over 100")
parser.add_argument('--output', required=True, help="Song ID (Queen - Killer Queen => killerqueen)")
parser.add_argument('--length', required=False, default=None, help="To fix the visual bug on the end of the song please define the video length")
args = parser.parse_args()
class UltraStar2LetsSing:
    def __init__(self, input):
        self.SongTXT = input
    def parse_file(self):
        data = {"notes": []}
        with io.open(self.SongTXT, "r", encoding="Windows-1252", errors='ignore') as f:
            for line in f:
                line = line.replace('\n', '')
                line = line.replace('\r', '')
                line = line.replace('ä', 'ae')
                line = line.replace('ö', 'oe')
                line = line.replace('ü', 'ue')
                line = line.replace('ß', 'ss')
                if line.startswith("#"):
                    p = line.split(":", 1)
                    if len(p) == 2:
                        data[p[0][1:]] = p[1]
                else:
                    note_arr = line.split(" ", 4)
                    data["notes"].append(note_arr)
                    print(data["notes"])
        return data

    def map_data(self, us_data, pitch_corr):
        sing_it = {"text": [], "notes": [], "pages": [], "notes_golden": [], "notes_full": []}
        bpm = float(us_data["BPM"].replace(',', '.'))
        gap = float(us_data["GAP"].replace(',', '.')) / 1000
        min_note = 1
        last_page = 0.0
        fix = 0.0
        for note in us_data["notes"]:
            if note[0] == ":" or note[0] == "*":
                start = float(note[1]) * 60 / bpm / 4 + gap
                end = start + float(note[2]) * 60 / bpm / 4
                if last_page != 0.0:
                    if sing_it["notes_full"][-1]["t2"] > start:
                        start = sing_it["notes_full"][-1]["t2"]
                sing_it["text"].append({"t1": start, "t2": end, "value": note[4]})
                nint = int(note[3])
                if nint < min_note:
                    nint = min_note
                sing_it["notes_full"].append(
                    {"t1": start, "t2": end, "value": f"#p{nint + int(pitch_corr)}#.{note[4]}#h{'#g5' if note[0] == '*' else ''}"})
            elif note[0] == "-":
                start = last_page
                end = float(note[1]) * 60 / bpm / 4 + gap
                if sing_it["notes_full"][-1]["t2"] > end:
                    print(start)
                    end = sing_it["notes_full"][-1]["t2"]
                    print(start)
                last_page = end
                sing_it["pages"].append(
                    {"t1": start, "t2": end, "value": ""})
                    
            elif note[0] == "F":
                start = float(note[1]) * 60 / bpm / 4 + gap
                end = start + float(note[2]) * 60 / bpm / 4
                if last_page != 0.0:
                    if sing_it["notes_full"][-1]["t2"] > start:
                        start = sing_it["notes_full"][-1]["t2"]
                sing_it["text"].append({"t1": start, "t2": end, "value": note[4]})
                nint = int(note[3])
                if nint < min_note:
                    nint = min_note
                sing_it["notes"].append(
                    {"t1": start, "t2": end, "value": 1})
                sing_it["notes_full"].append(
                    {"t1": start, "t2": end, "value": f"#p1#.{note[4]}#h{'#g5' if note[0] == '*' else ''}"})
            elif note[0] == "E":
               # if end > last_page:
                start = last_page
                sing_it["pages"].append(
                    {"t1": start, "t2":  float(f"{ args.length if args.length is not None else end + 0.100 }"), "value": ""}) # VIDEO LÄNGE ALS END
        return sing_it

    def write_intervals(self, interval_arr, parent):
        for interval in interval_arr:
            ET.SubElement(parent, "Interval",
                          t1="{0:.3f}".format(interval["t1"]), t2="{0:.3f}".format(interval["t2"]),
                          value=str(interval["value"]))

    def write_vxla_file(self, sing_it, filename):
        root = ET.Element("AnnotationFile", version="3.0")

        doc = ET.SubElement(root, "IntervalLayer", datatype="STRING",
                            name="structure")
        ET.SubElement(doc, "Interval", t1="2.000", t2="3.000", value="couplet1")

        # doc = ET.SubElement(root, "IntervalLayer", datatype="STRING",
        #                     name="shortversion", units="", description="")
        # ET.SubElement(doc, "Interval", t1="0.000",
        #               t2="60.000", value="shortversion")
        doc = ET.SubElement(root, "IntervalLayer", datatype="STRING",
                            name="pages")
        self.write_intervals(sing_it["pages"], doc)

        doc = ET.SubElement(root, "IntervalLayer", datatype="STRING",
                            name="lyrics")
        self.write_intervals(sing_it["text"], doc)

        # doc = ET.SubElement(root, "IntervalLayer", datatype="STRING",
        #                     name="lyrics_cut", units="", description="")
        # self.write_intervals(sing_it["text"], doc)

        doc = ET.SubElement(root, "IntervalLayer", datatype="STRING",
                            name="notes_full")
        self.write_intervals(sing_it["notes_full"], doc)
        # if len(sing_it["notes_golden"]) > 0:
        #     doc = ET.SubElement(root, "IntervalLayer", datatype="UINT8",
        #                         name="notes_golden", units="", description="")
        #     self.write_intervals(sing_it["notes_golden"], doc)


        xmlstr = minidom.parseString(ET.tostring(root)).toprettyxml(
            encoding="Windows-1252", indent="   ")
        with open(filename, "wb") as f:
            f.write(xmlstr)

if not os.path.isfile(args.input):
    print("TXT not found")
    sys.exit(1)
else:
    input=args.input
u2ls = UltraStar2LetsSing(input)
#print(u2ls.map_data(u2ls.parse_file(), args.pitch), f"{args.output}")
u2ls.write_vxla_file(u2ls.map_data(u2ls.parse_file(), args.pitch), f"{args.output}")

        
