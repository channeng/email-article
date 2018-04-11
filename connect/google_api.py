from __future__ import print_function
import httplib2
import os

from apiclient import discovery
from oauth2client import client, tools
from oauth2client.file import Storage

from config import Config

_CREDENTIAL_DIR = Config.CREDENTIAL_DIR
_CLIENT_SECRET_FILE = Config.CLIENT_SECRET_FILE

try:
    import argparse
    flags = argparse.ArgumentParser(
        parents=[tools.argparser]).parse_known_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/gmail-python-quickstart.json
SCOPES = [
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/calendar.readonly'
]
APPLICATION_NAME = Config.APPLICATION_NAME


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    if not os.path.exists(_CREDENTIAL_DIR):
        os.makedirs(_CREDENTIAL_DIR)
    credential_path = os.path.join(
        _CREDENTIAL_DIR, APPLICATION_NAME.lower().replace(" ", "_") + '.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(_CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:  # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)

    return credentials


def _build_service(api, version):
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    return discovery.build(
        api, version,
        http=http,
        # cache_discovery=False to silence cache error
        # https://github.com/google/google-api-python-client/issues/299
        cache_discovery=False)


def get_gmail_service():
    service = _build_service('gmail', 'v1')
    return service


def main():
    """Shows basic usage of the Gmail API.

    Creates a Gmail API service object and outputs a list of label names
    of the user's Gmail account.
    """
    service = get_gmail_service()

    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])

    if not labels:
        print('No labels found.')
    else:
        print('Labels:')
        for label in labels:
            print(label['name'])


if __name__ == '__main__':
    main()
