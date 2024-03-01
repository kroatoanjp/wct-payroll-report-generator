from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
import logging
import os
import pickle
from types import SimpleNamespace

from dotenv import load_dotenv
from trello import TrelloClient

logger = logging.getLogger(__name__)

@dataclass
class TrelloCredentials:
    api_key: str
    api_secret: str
    token: str
    token_secret: str

    @staticmethod
    def default_credentials():
        load_dotenv(override=True) 
        return TrelloCredentials(
            api_key=os.getenv("TRELLO_API_KEY"),
            api_secret=os.getenv("TRELLO_API_SECRET"),
            token=os.getenv("TRELLO_TOKEN"),
            token_secret=os.getenv("TRELLO_TOKEN_SECRET")
        )

class TrelloBoard:
    def __init__(self, board_id, credentials, cache_folder):
        self.board_id = board_id
        self._cache_folder = cache_folder
        self._cache_file = f"{self._cache_folder}/{self.board_id}.pickle"
        self._client = TrelloClient(
            api_key=credentials.api_key,
            api_secret=credentials.api_secret,
            token=credentials.token,
            token_secret=credentials.token_secret,
        )
        self._board = self._get_board(board_id)
        self._member_id_map = self._get_member_id_map()
        self.cards = []

    def _get_board(self, target_board_id):
        logger.debug(f"Retrieving board with id: {target_board_id}")
        target_board = [board for board in self._client.list_boards() if board.id == target_board_id]
        if len(target_board) == 0:
            logger.error(f"Unable to retrieve board with id: {target_board_id}")
            raise ValueError(f"No board found with id: {target_board_id}")
        logger.debug(f"Retrieved board with id: {target_board_id}")
        return target_board[0]

    def _get_member_id_map(self):
        logger.debug(f"Retrieving board member data")
        member_data = self._board.get_members()
        logger.debug(f"Retrieved board member data")
        member_id_map = {member.id: member.username for member in member_data}
        return member_id_map

    def get_members(self):
        return list(self._member_id_map.values())

    def get_member_ids(self):
        return list(self._member_id_map.keys())

    def get_member_by_id(self, member_id):
        return self._member_id_map[member_id]

    def _get_all_cards(self):
        archived_cards = self._board.closed_cards()
        current_cards = self._board.get_cards()
        all_cards = archived_cards + current_cards
        return all_cards

    def _get_cached_board_data(self):
        logger.debug("Retrieving cached board data")
        if not os.path.isfile(self._cache_file):
            logger.info(f"No cache file found for board: {self.board_id}")
            board_data = {}
        else:
            logger.debug(f"Cache file found for board: {self.board_id}")
            logger.debug(f"Loading cached data")
            with open(self._cache_file, "rb") as infile:
                board_data = pickle.load(infile)
            logger.debug(f"Loaded cached data")
        logger.debug("Retrieved cached board data")
        return board_data

    def _write_cached_board_data(self, board_data):
        logger.debug("Writing board data to cache file")
        with open(self._cache_file, "wb") as outfile:
            pickle.dump(board_data, outfile)
        logger.debug("Wrote board data to cache file")

    def sync(self):
        logger.info("Syncing board data")
        cards = self._get_all_cards()
        board_data = self._get_cached_board_data()
        for card in cards:
            card_id = card.id
            last_activity_timestamp = datetime.timestamp(card.date_last_activity)
            card.props = SimpleNamespace()
            cached_entry_found = False
            cached_card_data = {}
            logger.debug(f"Checking cache for card: {card_id}")
            if card_id in board_data:
                logger.debug(f"Found cache entry for card: {card_id}")
                cached_card_data = board_data[card_id]
                if cached_card_data['last_activity_timestamp'] < last_activity_timestamp:
                    logger.info(f"Cache entry for card: {card_id} is expired")
                else:
                    cached_entry_found = True
            else:
                logger.info(f"No cache entry for card: {card_id}")
            if not cached_entry_found:
                cached_card_data['card_movements'] = card.list_movements() 
                cached_card_data['last_activity_timestamp'] = last_activity_timestamp
            card.props.card_movements = cached_card_data['card_movements']
            board_data[card_id] = cached_card_data
        self._write_cached_board_data(board_data)
        self.cards = cards
        logger.debug("Synced board data")

@dataclass
class TrelloBoardFactory:
    credentials: TrelloCredentials
    cache_folder: str

    def build(self, board_id):
        return TrelloBoard(board_id, self.credentials, self.cache_folder)

if __name__ == "__main__": 
    logger.setLevel(logging.DEBUG)
    credentials = TrelloCredentials.default_credentials()
    MTL_BOARD_ID = "61d77b3c650da472e3516146"
    board = TrelloBoard(MTL_BOARD_ID, credentials, 'cache/')
    board.sync()
    print(board.cards)
