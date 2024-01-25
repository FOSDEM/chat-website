#!/usr/bin/env python
from datetime import date
from jinja2 import Environment, PackageLoader, select_autoescape
import requests
import xml.etree.ElementTree as ET

class Room:
    """
    A generic room.
    """
    def __init__(self, title, room_name, raw_room, track_slug=None, days=()):
        self.title = title
        self.room_name = room_name
        self.raw_room_name = raw_room
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

def load_from_penta():
    req = requests.get('https://fosdem.org/2024/schedule/xml')
    if req.status_code != 200:
        raise "Status code was not 200"
    xml = req.text
    root = ET.fromstring(xml)
    conference = root.find("conference")
    days = root.findall("day")


    schedule_tracks = {}
    schedule_rooms = {}
    for track in root.find("tracks").findall("track"):
        schedule_tracks[track.text] = {
            "rooms": set()
        }

    for day in days:
        day_name = date.fromisoformat(day.get("date")).strftime("%A").lower()
        for room in day.findall("room"):
            slug = room.get("slug")
            room_name = room.get("name")
            schedule_room = schedule_rooms.get(slug)
            if schedule_room is None:
                schedule_room = {
                    "slug": slug,
                    "title": room_name,
                    "conference_room": room_name,
                    "events_by_day": {

                    }
                }
                schedule_rooms[slug] = schedule_room
            for event in room.findall("event"):
                schedule_room["events_by_day"][day_name] = True
                schedule_tracks[event.find("track").text]["rooms"].add(room.get("name"))
        
    start = date.fromisoformat(conference.find("start").text)
    end = date.fromisoformat(conference.find("end").text)

    dates = start.strftime("%B ") + convert_to_human_date(start) + " & " + convert_to_human_date(end)

    schedule = {
        "tracks": schedule_tracks,
        "rooms": schedule_rooms,
        "year": start.strftime("%Y"),
        "dates": dates
    }
    print (schedule)
    return schedule


def tracks_by_rooms(schedule):
    """
    Order tracks by rooms
    :param schedule:
    :return:
    """
    tracks_by_room = {}
    for track_name, track in schedule['tracks'].items():
        for room_name in track['rooms']:
            # Digital editions have one room per track - I hope.
            tracks_by_room[room_name] = track
    return tracks_by_room


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


def schedule_from_penta(schedule, tracks):
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

    # Rooms are in ... .rooms
    for room_name, room in schedule['rooms'].items():
        if room['slug'].lower() == 'mtest':
            continue
        if room_name[0].lower() == 'k' or room_name[0].lower() == 'm':
            # Main track
            t = MainTrack(
                title=room['title'],
                room_name=room['conference_room'][2:],
                raw_room=room['slug']
            )
            if t.room_name.lower() == 'fosdem':
                t.room_name = 'fosdem-keynotes'
        elif room_name[0].lower() == 'd':
            # Devroom
            t = DevRoom(
                title=room['title'],
                room_name='{0}-devroom'.format(room['conference_room'][2:]),
                raw_room=room['slug']
            )
        elif room_name[0].lower() == 's':
            # Stand
            t = Stand(
                title=room['title'],
                room_name='{0}-stand'.format(room['conference_room'][2:]),
                raw_room=room['slug']
            )
        else:
            continue

        # Stands are always on the schedule
        if t.type != 'stands':
            if room['events_by_day']['saturday']:
                t.days.append('saturday')
            if room['events_by_day']['sunday']:
                t.days.append('sunday')
        # Fancy title
        t.title, t.slug = track_title_and_slug_from_penta(tracks, t.raw_room_name)

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
            stands=my_schedule['stands']
        )
        with open('out/{0}.html'.format(day), 'w') as fh:
            fh.write(rendered)

    return 0


def main():
    """
    From the penta export at fosdem.org, generate a home page
    for chat.fosdem.org for Saturday and Sunday.
    Requires Jinja2 and pyyaml to function.

    TODO
    - parameter for year
    - parameter for date
    """
    schedule = load_from_penta()
    tracks = tracks_by_rooms(schedule)

    fosdem_schedule = schedule_from_penta(schedule, tracks)

    return page_from_my_schedule(fosdem_schedule, schedule["year"], schedule["dates"])


if __name__ == '__main__':
    exit(main())
