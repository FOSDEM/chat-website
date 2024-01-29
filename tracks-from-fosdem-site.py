import requests
import json
from html.parser import HTMLParser

class FOSDEMStandParser(HTMLParser):
    track_list = {}
    current_href = None
    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = next((x for x in attrs if x[0] == "href"), None)
            if href and href[1].startswith('/2024/schedule/track/'):
                self.current_href = href[1]

    def handle_data(self, data):
        if self.current_href:
            # Lightning talks is the weird outlier here.
            if self.current_href.endswith('/lightning_talks/'):
                data = "Lightning talks"
            self.track_list[data] = self.current_href
            self.current_href = None

URL = "https://fosdem.org/2024/schedule/"

def main():
    """
    From the schedule page on fosdem.org, generate a list of track urls for each
    track.
    """
    req = requests.get(URL)
    if req.status_code != 200:
        raise "Status code was not 200"

    parser = FOSDEMStandParser()
    parser.feed(req.text)
    print(parser.track_list)
    
    with open('track_list.json', 'w') as f:
        f.write(json.dumps(parser.track_list))

if __name__ == '__main__':
    exit(main())
