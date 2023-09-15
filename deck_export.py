from abc import abstractmethod, ABC
from typing import Optional
from string import ascii_uppercase
import base64

from js import document

from deck_parser import DeckSection, SIDEBOARD, MAIN_DECK, Token
from deck import Deck
from data import ScryfallDB, Card

MTG_GOLDFISH = "mtggoldfish"
MTG_ONLINE = "mtg_online"
MTG_ARENA = "mtg_arena"
MTG_SALVATION = "salvation_format"
DECKSTATS = "deckstats"

DCK_FORMAT = "dck_forge"
DEC_FORMAT = "dec_format"
DEK_FORMAT = "dek_format"
TXT_FORMAT = "txt_format"


class DeckExporter(ABC):
    """ABC for Deck Exporters"""

    def __init__(self, db: ScryfallDB = None):
        self._db = db

    @abstractmethod
    def card_entry(self, token: Token, section: DeckSection) -> str:
        """SPF for Card entry composition logic"""
        pass

    @abstractmethod
    def extension(self) -> str:
        """
        Method returning the file suffix/extension to export.
        See export_deck function
        """
        pass

    def main_header(self, deck: Deck) -> str:
        """Method to create deck list headers"""
        return ""  # No header to main section

    def side_header(self) -> str:
        """Method to create Sideboard heading separator"""
        return "\n"  # just an empty separation line

    def header(self) -> str:
        """Method to add in any info at the very top of the decklist"""
        return ""

    def footer(self) -> str:
        """Method to add in any info at the end (footer) of the decklist"""
        return ""

    def export(self, deck: Deck) -> str:
        """Main Export Algo"""
        decklist_txt = self.header()
        for section in deck.cards:
            if section == MAIN_DECK.name:
                decklist_txt += self.main_header(deck)
            else:  # Side
                decklist_txt += self.side_header()
            for card_token in deck.cards[section]:
                if not card_token.card:
                    continue
                decklist_txt += self.card_entry(card_token, section)
        decklist_txt += self.footer()
        return decklist_txt


class MTGGoldFishExporter(DeckExporter):
    REVERSE_RECODE = {v: k for k, v in ScryfallDB.SET_RECODE_MAP.items()}

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

    def card_entry(self, token: Token, section: DeckSection) -> str:
        """
        Returns a single Card Entry in  MTGoldfish format.

        Highlights:
        - some set codes will be updated to Goldfish short codes (different from Scryfall for some)
        - collector number will be converted to art index (e.g. for basic lands)

        """
        # Set Code
        if token.card.set_code in self.REVERSE_RECODE:
            set_code = self.REVERSE_RECODE[token.card.set_code].upper()
        else:
            set_code = token.card.set_code.upper()

        # Art Index
        art_index = self._collector_number_to_art_index(token.card)
        if art_index is not None:
            return f"{token.quantity} {token.card.name} <{art_index}> [{set_code}]\n"
        return f"{token.quantity} {token.card.name} [{set_code}]\n"

    def extension(self) -> str:
        return "_mtggoldfish.txt"


class MTGArenaExporter(DeckExporter):

    def card_entry(self, token: Token, section: DeckSection):
        return f"{token.quantity} {token.card.name} ({token.card.set_code.upper()}) {token.card.collector_number}\n"

    def extension(self) -> str:
        return "_mtgarena.txt"


class MTGOnlineExporter(DeckExporter):

    def card_entry(self, token: Token, section: DeckSection):
        return f"{token.quantity} {token.card.name}\n"

    def extension(self) -> str:
        return "_mtgo.txt"


class MTGDecExporter(DeckExporter):

    def main_header(self, deck: Deck) -> str:
        if deck.name:
            preamble = f"//NAME: {deck.name}\n\n"
        else:
            preamble = ""
        return f"{preamble}//Main\n"

    def side_header(self) -> str:
        return "\n//Sideboard\n"

    def card_entry(self, token: Token, section: DeckSection) -> str:
        deck_entry = f"{token.quantity} {token.card.name}\n"
        if section == SIDEBOARD.name:
            deck_entry = "SB: " + deck_entry
        return deck_entry

    def extension(self) -> str:
        return ".dec"

class MTGDekExporter(DeckExporter):

    def side_header(self) -> str:
        return "\nSideboard:\n"

    def card_entry(self, token: Token, section: DeckSection) -> str:
        return f"{token.quantity} {token.card.name}\n"

    def extension(self) -> str:
        return ".dek"


class TXTExporter(MTGDekExporter):

    def extension(self) -> str:
        return ".txt"


class DeckStatsExporter(DeckExporter):

    def main_header(self, deck: Deck) -> str:
        return "//Main\n"

    def side_header(self) -> str:
        return "\n//Sideboard\n"

    def card_entry(self, token: Token, section: DeckSection) -> str:
        return f"{token.quantity} [{token.card.set_code.upper()}] {token.card.name}\n"

    def extension(self) -> str:
        return "_deckstats.txt"


class MTGSalvationExporter(DeckExporter):
    def header(self):
        return "[DECK]\n"

    def footer(self):
        return "[/DECK]\n"

    def side_header(self):
        return "\nSideboard\n"

    def card_entry(self, token: Token, section: DeckSection):
        return f"{token.quantity}x {token.card.name}\n"

    def extension(self) -> str:
        return "_salvation.txt"


class ForgeDeckExporter(DeckExporter):
    def header(self):
        return "[metadata]\n"

    def main_header(self, deck: Deck):
        return f"Name={deck.name}\n[Main]\n"

    def side_header(self):
        return "\n[Sideboard]\n"

    def _card_art_index(self, card: Card) -> int:
        matched_cards = list(self._db.lookup(card_name=card.name, set_code=card.set_code, unique=False))
        if len(matched_cards) <= 1:
            return 1
        coll_numbers = [card.collector_number for card in matched_cards]
        try:
            coll_index = coll_numbers.index(card.collector_number)
        except ValueError:
            return 1
        else:
            return coll_index + 1

    def card_entry(self, token: Token, section: DeckSection):
        art_index = self._card_art_index(token.card)
        return f"{token.quantity} {token.card.name}|{token.card.set_code.upper()}|{art_index}\n"

    def extension(self) -> str:
        return ".dck"


DECK_EXPORTERS = {
    MTG_GOLDFISH: MTGGoldFishExporter,
    MTG_ARENA: MTGArenaExporter,
    MTG_ONLINE: MTGOnlineExporter,

    DEC_FORMAT: MTGDecExporter,
    DEK_FORMAT: MTGDekExporter,
    TXT_FORMAT: TXTExporter,

    DECKSTATS: DeckStatsExporter,
    MTG_SALVATION: MTGSalvationExporter,
    DCK_FORMAT: ForgeDeckExporter
}


def export_deck(exporter: DeckExporter, deck:Deck, id_target: str):
    """
    Utility function to exploit a generic DeckExporter instance to download the deck list.
    """

    decklist = exporter.export(deck)
    enc_decklist = base64.b64encode(decklist.encode("utf-8")).decode("utf-8")
    deck_name = deck.name.lower().replace(" ", "_") if deck.name else "premodern_deck"

    document.getElementById(id_target).href = f"data:text/plain;base64,{enc_decklist}"
    document.getElementById(id_target).download = f"{deck_name}{exporter.extension()}"

