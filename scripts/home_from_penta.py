#!/usr/bin/env python
from datetime import date
from jinja2 import Environment, PackageLoader, select_autoescape
from rapidfuzz import fuzz
from track_parser import get_track_list
import xml.etree.ElementTree as ET
import json
import requests

class Room:
    """
    A generic room.
    """
    def __init__(self, title, room_name, url, raw_room=None, track_slug=None, days=()):
        self.title = title
        self.room_name = room_name
        self.raw_room_name = raw_room
        self.url = url
        self.days = [d.lower() for d in days]
        self.slug = track_slug

    @property
    def on_sunday(self):
        if 'sunday' in self.days:
            return True
        return False

    @property
    def on_saturday(self):
        if 'saturday' in self.days:
            return True
        return False


class MainTrack(Room):
    """
    A main track.
    """
    type = 'main_track'


class DevRoom(Room):
    """
    A devroom.
    """
    type = 'devroom'


class Stand(Room):
    """
    A stand.
    """
    type = 'stand'


def convert_to_human_date(d):
    if d.day == 1 or d.day == 21 or d.day == 31:
        return f"{str(d.day)}st"
    elif d.day == 2 or d.day == 22:
        return f"{str(d.day)}nd"
    elif d.day == 3:
        return f"{str(d.day)}rd"
    else:
        return f"{str(d.day)}th"


def get_track_title_and_slug_from_list(track_list, schedule_track_name):
    # This determines the likely slug based on the track name. Admittedly,
    # it's a bit of a hack but it works well enough.
    best = None
    best_ratio = 0
    for name, url in track_list.items():
        ratio = fuzz.ratio(schedule_track_name, name)
        if ratio > best_ratio:
            best_ratio = ratio
            # extract '{name}' from /20XX/schedule/track/{name}/
            best = name, url
    return best

def load_from_penta(track_list):
    # Load the data from the schedule.
    req = requests.get('https://fosdem.org/schedule/xml', allow_redirects=True)
    if req.status_code != 200:
        raise "Status code was not 200"

    root = ET.fromstring(req.text)
    conference = root.find("conference")
    days = root.findall("day")

    start = date.fromisoformat(conference.find("start").text)
    end = date.fromisoformat(conference.find("end").text)
    dates = start.strftime("%B ") + convert_to_human_date(start) + " & " + convert_to_human_date(end)
    year = start.strftime("%Y")

    schedule_tracks = {}
    for track in root.find("tracks").findall("track"):
        # For each track, store the set of rooms it's in.
        title, url = get_track_title_and_slug_from_list(track_list, track.text)
        schedule_tracks[track.text] = {
            "days": set(),
            "title": title,
            "url": url,
        }

    for day in days:
        day_name = date.fromisoformat(day.get("date")).strftime("%A").lower()
        for room in day.findall("room"):
            for event in room.findall("event"):
                track_name = event.find("track").text
                schedule_tracks[track_name]["days"].add(day_name)
                # This is how we calculate matrix room names
                matrix_room_name = room.get("track").lower().replace(" (", "_").replace(")", "_").replace(" ", "_")
                schedule_tracks[track_name]["slug"] = f"{year}-{matrix_room_name}"



    schedule = {
        "tracks": schedule_tracks,
        "year": year,
        "dates": dates
    }
    return schedule


def track_title_and_slug_from_penta(tracks, room_slug):
    """
    Return the track title (e.g. Community) based on the room slug (mcommunity)
    :param tracks:
    :param room_slug:
    :return:
    """
    if room_slug in tracks:
        return tracks[room_slug]['title'], tracks[room_slug]['slug']
    return None, None


def schedule_from_penta(tracks):
    """
    Return a schedule from Pentabarf data
    :param schedule
    :param tracks
    :return:
    """

    my_schedule = {
        'devrooms': [],
        'main_tracks': [],
        'stands': []
    }

    for track_name, track in tracks.items():
        # extract '{name}' from /20XX/schedule/track/{name}/

        # Assuming these are the main track rooms.
        if "main track" in track["title"].lower():
            # Main track
            t = MainTrack(
                title=track['title'],
                room_name=track_name,
                days=track['days'],
                url=track['url'],
                track_slug=track['slug'],
            )
            if t.room_name.lower() == 'fosdem':
                t.room_name = 'fosdem-keynotes'
        elif "devroom" in track["title"].lower():
            # Devroom
            t = DevRoom(
                title=track['title'],
                room_name=track_name,
                days=track['days'],
                url=track['url'],
                track_slug=track['slug'],
            )
        # Not currently used.
        # elif identifier == 's':
        #     # Stand
        #     t = Stand(
        #         title=track['title'],
        #         room_name=room_name,
        #         raw_room=track['slug'],
        #         track_slug=track['slug']
        #     )
        else:
            continue


        # Add to schedule
        if not t.title:
            continue
        if t.type == 'stand':
            my_schedule['stands'].append(t)
        elif t.type == 'devroom':
            my_schedule['devrooms'].append(t)
        elif t.type == 'main_track':
            my_schedule['main_tracks'].append(t)

    return my_schedule


def page_from_my_schedule(my_schedule, year, dates):
    env = Environment(
        loader=PackageLoader('home_from_penta'),
        autoescape=select_autoescape()
    )
    template = env.get_template('home.html.j2')
    for day in ['saturday', 'sunday']:
        devrooms_today = [t for t in my_schedule['devrooms'] if day in t.days]
        main_tracks_today = [t for t in my_schedule['main_tracks'] if day in t.days]

        rendered = template.render(
            fosdem_year=year,
            fosdem_dates=dates,
            devrooms=devrooms_today,
            main_tracks=main_tracks_today,
            day_name=day[0].upper() + day[1:],
            stands=my_schedule['stands']
        )
        filename = f'out/{day}.html'
        with open(filename, 'w') as fh:
            fh.write(rendered)
            print(f'{filename} built with {len(main_tracks_today)} main tracks and {len(devrooms_today)} devrooms')

    return 0


def main():
    """
    From the penta export at fosdem.org, generate a home page
    for chat.fosdem.org for Saturday and Sunday.
    """
    # Get the list of tracks (and their URLs) from the FOSDEM website.
    track_list = get_track_list()

    # Load the schedule from penta and figure out which tracks happen on which days.
    schedule = load_from_penta(track_list)

    # Sort into main tracks, devrooms, stands etc
    fosdem_schedule = schedule_from_penta(schedule["tracks"])

    # And finally generate the pages
    return page_from_my_schedule(fosdem_schedule, schedule["year"], schedule["dates"])


if __name__ == '__main__':
    exit(main())
