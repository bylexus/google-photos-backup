#!/usr/bin/python
##
# Simple python script for downloading / backing up your Google Photos
# Usage: see separate README.md for details.
# Simple example:
#
# python google-photo-backup-py -c google-oauth-client-secret.json
#
# (c) 2019 Alexander Schenkel <alex+google-photo@alexi.ch>

import json
import os
from dateutil.parser import parse
import datetime
import httplib2
from oauth2client.client import flow_from_clientsecrets
import argparse
from oauth2client import tools
from oauth2client.file import Storage
from apiclient.discovery import build


def getCredentials(cmdFlags):
    client_secret = os.path.expanduser(cmdFlags.client_secret)
    flow = flow_from_clientsecrets(client_secret,
                                   scope='https://www.googleapis.com/auth/photoslibrary.readonly',
                                   redirect_uri='http://localhost')

    storage = Storage('credentials-store')
    credentials = storage.get()
    if not credentials:
        credentials = tools.run_flow(flow, storage, cmdFlags)
    return credentials


def mediaGenerator(collection):
    req = collection.list()

    while req != None:
        res = req.execute()
        if 'mediaItems' in res:
            for item in res['mediaItems']:
                yield item
            req = collection.list_next(req, res)
        else:
            break


def processPhoto(mediaItem, baseDir, http):
    filename = mediaItem['filename']
    dt = parse(mediaItem['mediaMetadata']['creationTime'])
    dt = dt if dt else datetime.datetime.now()
    year = str(dt.year)
    month = "{:02d}".format(dt.month)

    os.makedirs(os.path.join(dest_dir, year, month), exist_ok=True)
    dest_file = os.path.join(dest_dir, year, month, filename)
    print("{}: ".format(dest_file), end="")
    if os.path.exists(dest_file):
        print("Skipping, file does already exist.")
    else:
        downloadOption = "d"
        if 'video' in mediaItem['mediaMetadata']:
            downloadOption = 'dv'
        (response, imageContent) = http.request(
            "{}={}".format(mediaItem['baseUrl'], downloadOption))
        if imageContent:
            with open(dest_file, 'wb') as filename:
                print("Writing {:d} bytes".format(len(imageContent)))
                filename.write(imageContent)
        else:
            print("Error retrieving image content. Reason: {}".format(response.reason))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Downloads your photos from Google Photos",
        parents=[tools.argparser])
    parser.add_argument('-c', '--client-secret',
                        help="Google OAuth2 Client Secrete json file")
    parser.add_argument('dest_path', help="Destination path for the photos")
    flags = parser.parse_args()
    dest_dir = os.path.expanduser(flags.dest_path)

    credentials = getCredentials(flags)

    http = credentials.authorize(httplib2.Http())
    service = build('photoslibrary', 'v1', http=http)

    os.makedirs(dest_dir, exist_ok=True)
    collection = service.mediaItems()

    itemGenerator = mediaGenerator(collection)

    # each item is a mediaItem, see here: https://developers.google.com/photos/library/reference/rest/v1/mediaItems#MediaItem
    # download using the mediaItems baseUrl, see https://developers.google.com/photos/library/guides/access-media-items#base-urls
    for item in itemGenerator:
        processPhoto(item, baseDir=dest_dir, http=http)
