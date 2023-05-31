from abc import abstractmethod
from typing import Optional
from string import ascii_uppercase

from deck_parser import Deck
from data import ScryfallDB, Card

MTG_GOLDFISH = "mtggoldfish"
MTG_ARENA_NO_VERSION = "arena_no_version"
MTG_ARENA_WITH_VERSION = "arena_w_version"
DCK_FORMAT = "dck_forge"
DEC_FORMAT = "dec_format"


class DeckExporter:
    @abstractmethod
    def export(self, deck: Deck) -> str:
        pass


class MTGGoldFishExporter(DeckExporter):
    REVERSE_RECODE = {v: k for k, v in ScryfallDB.SET_RECODE_MAP.items()}

    def __init__(self, db: ScryfallDB):
        self._db = db

    def _collector_number_to_art_index(self, card: Card) -> Optional[str]:
        matched_cards = list(self._db.lookup(card_name=card.name, set_code=card.set_code, unique=False))
        if len(matched_cards) <= 1:
            return None
        coll_numbers = [card.collector_number for card in matched_cards]
        try:
            coll_index = coll_numbers.index(card.collector_number)
        except ValueError:
            return None
        else:
            return ascii_uppercase[coll_index]

    def export(self, deck: Deck) -> str:
        """Export list in MTGO format for easy quick upload on MTGGoldfish in case"""
        decklist_txt = ""
        for section in deck.cards:
            for card_token in deck.cards[section]:
                if not card_token.card:
                    continue
                # Set Code
                if card_token.card.set_code in self.REVERSE_RECODE:
                    set_code = self.REVERSE_RECODE[card_token.card.set_code].upper()
                else:
                    set_code = card_token.card.set_code.upper()

                # Art Index
                art_index = self._collector_number_to_art_index(card_token.card)
                if art_index is not None:
                    line = (
                        f"{card_token.quantity} {card_token.card.name} <{art_index}> [{set_code}]\n"
                    )
                else:
                    line = (
                        f"{card_token.quantity} {card_token.card.name} [{set_code}]\n"
                    )
                decklist_txt += line
            decklist_txt += "\n"  # empty line as separator for the next section
        return decklist_txt


DECK_EXPORTERS = {
    MTG_GOLDFISH: MTGGoldFishExporter,
    MTG_ARENA_NO_VERSION: None,
    MTG_ARENA_WITH_VERSION: None,
    DEC_FORMAT: None,
    DCK_FORMAT: None
}