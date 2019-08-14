import click
from datetime import datetime, timezone
import json
import logging
import requests
import time
from tqdm import tqdm
from typing import Generator


class DiscordApiError(Exception):
    def __init__(self, *, http_code: int, details: str) -> None:
        message = ''
        if http_code > 0:
            message += f'[HTTP code: {http_code}] '
        message += details
        super().__init__(message)


class Crawler:
    API_URL = 'https://discordapp.com/api/v6'
    HTTP_CODE_MESSAGES = {
        400: "The request was improperly formatted, or the server couldn't understand it.",
        401: "The Authorization header was missing or invalid.",
        403: "The Authorization token you passed did not have permission to the resource.",
        404: "The resource at the location specified doesn't exist.",
        405: "The HTTP method used is not valid for the location specified.",
        502: "There was not a gateway available to process your request. Wait a bit and retry.",
        '5xx': "The server had an error processing your request.",
    }
    RATE_LIMITED_RETRY = 5
    MESSAGES_LIMIT_PER_REQUEST = 100

    def __init__(self, token: str):
        self.s = requests.Session()
        self.s.headers.update({
            'Authorization': token
        })

    def _request(self, method: str, path: str, params: dict) -> requests.Response:
        for i in range(self.RATE_LIMITED_RETRY):
            res = self.s.request(method, f'{self.API_URL}{path}', params)
            if res.status_code in self.HTTP_CODE_MESSAGES:
                raise DiscordApiError(http_code=res.status_code, details=self.HTTP_CODE_MESSAGES[res.status_code])
            elif 500 <= res.status_code < 600:  # server error
                raise DiscordApiError(http_code=res.status_code, details=self.HTTP_CODE_MESSAGES['5xx'])
            elif res.status_code == 429:  # rate limits
                retry_after = res.json()['retry_after']
                logging.warning(f'Rate limited. We will sleep {retry_after} ms, and retry it.')
                time.sleep(retry_after / 1000)
                continue
            return res

        logging.critical(f'Failed to request it, although we tried at {self.RATE_LIMITED_RETRY} times.')

    def get_channel_messages(self, channel_id: int, oldest_message_id: int, newest_message_id: int):
        current_message_id = newest_message_id + 1
        while True:
            res = self._request('get', f'/channels/{channel_id}/messages', {
                'before': current_message_id,
                'limit': self.MESSAGES_LIMIT_PER_REQUEST,
            })
            messages = res.json()
            messages = list(filter(lambda message: int(message['id']) >= oldest_message_id, messages))

            yield messages

            if len(messages) < self.MESSAGES_LIMIT_PER_REQUEST:
                break
            current_message_id = int(messages[-1]['id'])


def datetime_to_str(t: datetime = datetime.now(timezone.utc)) -> str:
    return datetime.strftime(t, '%Y-%m-%d %H:%M:%S.%f %z')


def str_to_datetime(s: str) -> datetime:
    return datetime.strptime(s, '%Y-%m-%d %H:%M:%S.%f %z')


class Serializer:
    @staticmethod
    def dict_generator_to_json(generator: Generator, path: str) -> tuple:
        message_count = 0

        with open(path, 'x') as f:
            f.write('[')
            pbar = tqdm(enumerate(generator, start=1))
            try:
                for i, messages in pbar:
                    if i == 1:
                        newest_message_id = messages[0]['id']
                        newest_message_datetime = messages[0]['timestamp']
                    else:
                        f.write(',')
                    f.write(json.dumps(messages, separators=(',', ':')).strip('[]'))

                    message_count += len(messages)
            finally:
                f.write(']')

        oldest_message_id = messages[-1]['id']
        oldest_message_datetime = messages[-1]['timestamp']

        return message_count, (oldest_message_datetime, newest_message_datetime), (oldest_message_id, newest_message_id)


@click.command()
@click.option('--token', type=str, required=True, prompt=True, hide_input=True,
              help='A Discord bot/user token')
@click.option('--token-type', type=click.Choice(['Bot', 'Bearer', 'User'], case_sensitive=False), default='User',
              help='A type of Discord token')
@click.option('--channel-id', type=int, required=True,
              help='A channel ID to crawl')
@click.option('--newest-message-id', type=int, required=True,
              help='A newest message ID to crawl (We do not check its validity.)')
@click.option('--oldest-message-id', type=int, required=True,
              help='A oldest message ID to crawl (We do not check its validity.)')
@click.option('--path', type=click.Path(dir_okay=False, writable=True, resolve_path=True), required=True,
              help='A JSON file path to create and write')
def main(token, token_type, channel_id, newest_message_id, oldest_message_id, path):
    logging.basicConfig(format='%(asctime)s %(levelname)-8s %(funcName)s:%(lineno)d - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S', level=logging.INFO)
    token_str = f'{token_type} {token}' if token_type != 'User' else token

    logging.info('Started!')

    try:
        crawler = Crawler(token_str)
        generator = crawler.get_channel_messages(channel_id, oldest_message_id, newest_message_id)
        message_count, (oldest_message_datetime, newest_message_datetime), (oldest_message_id, newest_message_id) = \
            Serializer.dict_generator_to_json(generator, path)

        logging.info('')
        logging.info(f'Done to crawl {message_count} messages!')
        logging.info(f'Message IDs: from {oldest_message_id} to {newest_message_id}')
        logging.info(f'Message Timestamps: from {oldest_message_datetime} to {newest_message_datetime}')
    except Exception as e:
        logging.info('')
        logging.warning('Aborted!')
        raise e


if __name__ == '__main__':
    main()
