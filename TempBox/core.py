import httpx
import json
import time


# ------------------------- Custom Exceptions -------------------------

class TempEmailError(Exception):
    """Base exception class for TempEmail."""


class HTTPRequestError(TempEmailError):
    """Exception raised when there's an HTTP error."""


class JSONDecodeError(TempEmailError):
    """Exception raised when there's a JSON decoding error."""


# ------------------------- HTTP Helper Class -------------------------

class HTTPHelper:
    BASE_URL = 'https://www.1secmail.com/api/v1/'

    @staticmethod
    def _parse_json(response):
        try:
            return response.json()
        except json.JSONDecodeError:
            raise JSONDecodeError(
                f"Failed to decode JSON. Status Code: {response.status_code}, Content: {response.text}")

    @classmethod
    def make_request(cls, action, **params):
        try:
            with httpx.Client() as client:
                response = client.get(cls.BASE_URL, params={"action": action, **params})
                response.raise_for_status()
                return cls._parse_json(response)
        except httpx.HTTPError as http_err:
            raise HTTPRequestError(f"HTTP error occurred: {http_err}")
        except Exception as err:
            raise TempEmailError(f"Error occurred: {err}")


# ------------------------- Attachment Representation -------------------------

class Attachment:
    def __init__(self, filename=None, content_type=None, size=None, download_url=None):
        self.filename = filename
        self.content_type = content_type
        self.size = size
        self.download_url = download_url

    @classmethod
    def from_api_response(cls, data, login, domain, message_id):
        return cls(
            filename=data.get('filename'),
            content_type=data.get('contentType'),
            size=data.get('size'),
            download_url=f"{HTTPHelper.BASE_URL}?action=download&login={login}&domain={domain}&id={message_id}&file={data.get('filename')}"
        )

    def __str__(self):
        return f"Filename: {self.filename}, Type: {self.content_type}, Size: {self.size} bytes"


# ------------------------- Mail Representation -------------------------

class Mail:
    def __init__(self, id=None, sender="", subject="", date="", body="", text_body="", html_body="", attachments=None):
        self.id = id
        self.sender = sender or "Unknown Sender"
        self.subject = subject or "No Subject"
        self.date = date or "Unknown Date"
        self.body = body or "No Body"
        self.text_body = text_body or "No Text Body"
        self.html_body = html_body or "No HTML Body"
        self.attachments = attachments or []

    @classmethod
    def from_api_response(cls, data):
        attachments = [
            Attachment.from_api_response(attachment_data, data.get('login'), data.get('domain'), data.get('id'))
            for attachment_data in data.get('attachments', [])
        ]
        return cls(
            id=data.get('id'),
            sender=data.get('from'),
            subject=data.get('subject'),
            date=data.get('date'),
            body=data.get('body'),
            text_body=data.get('textBody'),
            html_body=data.get('htmlBody'),
            attachments=attachments
        )

    def __str__(self):
        return f"From: {self.sender}\nSubject: {self.subject}\nDate: {self.date}\n\n{self.text_body}"


# ------------------------- Main TempEmail class -------------------------

class TempEmail:

    def get_domain_list(self):
        return HTTPHelper.make_request('getDomainList') or []

    def gen_random_mailbox(self, count=1):
        return HTTPHelper.make_request('genRandomMailbox', count=count) or []


# ------------------------- Mailbox Representation -------------------------

class Mailbox:
    """Represents a mailbox for a specific email address."""

    def __init__(self, login, domain):
        """Initialize a mailbox with login and domain."""
        self.login = login
        self.domain = domain

    def get_messages(self):
        """Retrieve messages for the mailbox."""
        return HTTPHelper.make_request('getMessages', login=self.login, domain=self.domain) or []

    def read_message(self, message_id):
        response_data = HTTPHelper.make_request('readMessage', login=self.login, domain=self.domain, id=message_id)
        if response_data:
            return Mail.from_api_response(response_data)
        return None

    def download_attachment(self, message_id, filename):
        with httpx.Client() as client:
            response = client.get(HTTPHelper.BASE_URL,
                                  params={'action': 'download', 'login': self.login, 'domain': self.domain,
                                          'id': message_id, 'file': filename})
            return response.content

    def wait_for_message(self, sender_filter=None, subject_filter=None, timeout=300, interval=10):
        """
        Waits for a new message to arrive in the mailbox with optional filters.

        :param sender_filter: The sender email address to filter messages by.
        :param subject_filter: A keyword to filter messages by their subject.
        :param timeout: The total time (in seconds) to wait for a message.
        :param interval: The time interval (in seconds) between consecutive checks.
        :return: A Mail object that matches the filters if one arrives within the timeout. Otherwise a default Mail object with None values.
        """
        start_time = time.time()
        seen_message_ids = set()  # To keep track of messages we've already seen

        while time.time() - start_time < timeout:
            messages = self.get_messages()

            # Filter out messages we've already seen
            new_messages = [msg for msg in messages if msg.get('id') not in seen_message_ids]

            if new_messages:
                print("Received new messages:", new_messages)

                # Add new message IDs to the seen set
                seen_message_ids.update([msg.get('id') for msg in new_messages])

                # If filters are provided, apply them
                for msg in new_messages:
                    if sender_filter and msg.get('from') != sender_filter:
                        continue
                    if subject_filter and subject_filter.lower() not in msg.get('subject', '').lower():
                        continue

                    # If a message matches all filters, fetch its full details as a Mail object and return
                    return self.read_message(msg.get('id'))

            print(f"Waiting for new email. {int(timeout - (time.time() - start_time))} seconds remaining.")
            time.sleep(interval)

        print("Timeout reached without receiving a matching message.")
        return Mail()
