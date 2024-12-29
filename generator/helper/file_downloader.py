import os
from datetime import datetime
import requests
from urllib.parse import urljoin
from html.parser import HTMLParser

class HtmlParser(HTMLParser):
    """
    HTML Parser that handles link entries in the HTML.
    Saves the URLs in the field `file_links` and tracks the latest update timestamp.
    """
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.file_links = [] # To store all links
        self.latest_timestamp = None  # To store the maximum timestamp

    def handle_starttag(self, tag, attrs):
        # Check for <a> tag (links)
        if tag == "a":
            for attr in attrs:
                if attr[0] == "href":
                    file_url = urljoin(self.base_url, attr[1])
                    self.file_links.append(file_url)


    def handle_data(self, data):
        # Check if the data is a timestamp
        data = data.strip()
        try:
            # Attempt to parse the first 16 characters of data as a timestamp. Data contains of TS + Size
            timestamp = datetime.strptime(data[:17], "%d-%b-%Y %H:%M")
            # Update the maximum timestamp
            if self.latest_timestamp is None or timestamp > self.latest_timestamp:
                self.latest_timestamp = timestamp
        except ValueError:
            # Not a valid timestamp, so skip
            pass



def download_file(url: str, folder: str):
    """
    Function to download a file from a specified URL and save it to a folder

    Parameters:
    url (str): The URL of the file to download.
    folder (str): The folder where the file should be saved.
    """

    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        # Get filename from URL
        filename = os.path.join(folder, url.split("/")[-1])
        #print(f"Filename {filename}")

        with open(filename, "wb") as f:
            f.write(r.content)
            #print(f"Downloaded {filename}")
    else:
        print(f"Failed to download {filename}")

def download_all_files(url: str, folder: str, min_timestamp: datetime) -> (int, datetime):
    """
    Function to download all file found in a specified URL and save them to a folder. Download is only executed, if the maximum timestamp on the page is greater than the provided one.

    Parameters:
    url (str): The URL of the files to download. The files should be found as HTML links.
    folder (str): The folder where the files should be saved.
    min_timestamp (datetime): The minimum required datetime to download files.
    
    Returns:
    result (int): 0 if ok, -1 if access failed, 1 if no download was executed because of timestamp comparison
    timestamp (datetime): The latest timestamp found on the URL.
    """

    # Create download folder if it doesn't exist
    if not os.path.exists(folder):
        os.makedirs(folder)

    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        # Call the HTML Parser from above that scrapes the HTML links
        parser = HtmlParser(url)
        parser.feed(r.text)

        print(f"Newest update timestamp from url: {parser.latest_timestamp} - given timestamp: {min_timestamp}")
        if min_timestamp is None or parser.latest_timestamp > min_timestamp:
            for file_url in parser.file_links:
                if file_url.startswith(url):
                    print(f"Downloading {file_url}")
                    download_file(file_url, folder)
            return (0, parser.latest_timestamp)

        # If no download was necessary
        return (1, parser.latest_timestamp)
    else:
        print(f"Failed to access {url}")
        return (-1, "")
