from __future__ import print_function

import os
import pickle

from apiclient import discovery
from oauth2client import tools

from config import Config
try:
    import argparse
    flags = argparse.ArgumentParser(
        parents=[tools.argparser]).parse_known_args()
except ImportError:
    flags = None


CREDENTIAL_DIR = Config.CREDENTIAL_DIR
CREDENTIALS_FILE = Config.CREDENTIALS_FILE


# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/gmail-python-quickstart.json
SCOPES = [
    'https://mail.google.com/',
]


def get_credentials(name):
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    if not os.path.exists(CREDENTIAL_DIR):
        os.makedirs(CREDENTIAL_DIR)
    credential_path = os.path.join(
        CREDENTIAL_DIR, CREDENTIALS_FILE[name])
    with open(credential_path, 'rb') as token:
        credentials = pickle.load(token)

    return credentials


def _build_service(api, version, name="pocket_sg_hello"):
    credentials = get_credentials(name)
    return discovery.build(
        api, version, credentials=credentials,
        # cache_discovery=False to silence cache error
        # https://github.com/google/google-api-python-client/issues/299
        cache_discovery=False)


def get_gmail_service(name="pocket_sg_hello"):
    service = _build_service('gmail', 'v1', name=name)
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
