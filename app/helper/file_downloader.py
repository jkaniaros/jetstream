import os
import requests
from urllib.parse import urljoin
from html.parser import HTMLParser

class HtmlParser(HTMLParser):
    """
    HTML Parser that handles link entries in the HTML.
    Saves the URLs in the field `file_links`
    """
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.file_links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr in attrs:
                if attr[0] == 'href':
                    file_url = urljoin(self.base_url, attr[1])
                    self.file_links.append(file_url)


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
        print(f"Filename {filename}")

        with open(filename, "wb") as f:
            f.write(r.content)
            print(f"Downloaded {filename}")
    else:
        print(f"Failed to download {filename}")

def download_all_files(url: str, folder: str):
    """
    Function to download all file found in a specified URL and save them to a folder

    Parameters:
    url (str): The URL of the files to download. The files should be found as HTML links.
    folder (str): The folder where the files should be saved.
    """

    # Create download folder if it doesn't exist
    if not os.path.exists(folder):
        os.makedirs(folder)

    r = requests.get(url, timeout=10)
    if r.status_code == 200:
        # Call the HTML Parser from above that scrapes the HTML links
        parser = HtmlParser(url)
        parser.feed(r.text)

        for file_url in parser.file_links:
            if file_url.startswith(url):
                print(f"Downloading {file_url}")
                download_file(file_url, folder)
    else:
        print(f"Failed to access {url}")
