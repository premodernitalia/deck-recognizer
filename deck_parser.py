import re
from dataclasses import dataclass
from enum import Enum
from collections import defaultdict
from typing import Optional, AnyStr, Union
from data import Card, ScryfallDB


class TokenType(Enum):
    # card_token
    LEGAL_CARD = "LEGAL CARD"
    BANNED_CARD = "BANNED CARD"
    RESTRICTED_CARD = "RESTRICTED CARD"
    # Deck Metadata tag
    DECK_NAME = "DECK NAME"
    DECK_SECTION_NAME = "DECK SECTION NAME"
    # Deck Placeholder deck
    CARD_TYPE = "CARD TYPE"
    CARD_RARITY = "CARD RARITY"
    CARD_CMC = "CARD CMC"
    MANA_COLOUR = "MANA COLOUR"
    # Messages
    WARNING_MESSAGE = "WARNING MESSAGE"
    UNKNOWN_CARD = "UNKNOWN CARD"
    UNKNOWN_TEXT = "UNKNOWN TEXT"
    COMMENT = "COMMENT"


@dataclass
class DeckSection:
    name: str
    min_size: int
    max_size: int = 100


MAIN_DECK = DeckSection("Main", min_size=60)
SIDEBOARD = DeckSection("Sideboard", min_size=0, max_size=15)


@dataclass
class Token:
    token_type: TokenType
    quantity: int = 0
    text: Optional[str] = None
    card: Optional[Card] = None
    is_foil: bool = False
    deck_section: Optional[DeckSection] = None
    card_request_has_setcode: bool = True

    def __post_init__(self):
        if self.card is not None:
            self.text = f"{self.quantity} {self.card.name} [{self.card.set_code}] #{self.card.collector_number}"

    # ===============
    # Factory Methods
    # ===============
    @classmethod
    def legal_card_token(
        cls,
        card: Card,
        count: int,
        deck_section: DeckSection,
        card_has_setcode: bool,
        is_foil: bool = False,
    ):
        return cls(
            token_type=TokenType.LEGAL_CARD,
            quantity=count,
            card=card,
            is_foil=is_foil,
            deck_section=deck_section,
            card_request_has_setcode=card_has_setcode,
        )

    @classmethod
    def banned_card_token(cls, card_name: str, count: int):
        return cls(token_type=TokenType.BANNED_CARD, quantity=count, text=card_name)

    # WARNING MESSAGES
    # ================
    @classmethod
    def unknown_card_token(cls, card_name: str, set_code: str, count: int):
        token_text = card_name if not set_code else f"{card_name} [{set_code}]"
        return cls(token_type=TokenType.UNKNOWN_CARD, quantity=count, text=token_text)

    @classmethod
    def warning_message_token(cls, msg: str):
        return cls(token_type=TokenType.WARNING_MESSAGE, text=msg)

    # DECK SECTION
    # ============
    @classmethod
    def deck_section_token(cls, section_name: str, count: int = 0):
        section_name = section_name.lower().strip()

        if (
            section_name == "side"
            or section_name == "sb"
            or "sideboard" in section_name
        ):
            target_deck_section = SIDEBOARD
        elif (
            section_name == "main"
            or section_name == "mainboard"
            or section_name == "deck"
            or "card" in section_name
        ):
            target_deck_section = MAIN_DECK
        else:
            target_deck_section = None

        if target_deck_section is None:
            return None

        return cls(
            token_type=TokenType.DECK_SECTION_NAME,
            text=target_deck_section.name,
            quantity=count,
        )

    @property
    def is_card_token(self):
        return self.token_type in (
            TokenType.LEGAL_CARD,
            TokenType.BANNED_CARD,
            TokenType.RESTRICTED_CARD,
        )

    @property
    def is_card_token_for_deck(self):
        return self.token_type in (TokenType.LEGAL_CARD, TokenType.RESTRICTED_CARD)

    @property
    def is_token_for_deck(self):
        return self.token_type in (
            TokenType.LEGAL_CARD,
            TokenType.BANNED_CARD,
            TokenType.RESTRICTED_CARD,
            TokenType.DECK_NAME,
        )

    @property
    def is_card_placeholder_token(self):
        return self.token_type in (
            TokenType.CARD_RARITY,
            TokenType.CARD_CMC,
            TokenType.MANA_COLOUR,
            TokenType.CARD_TYPE,
        )

    @property
    def is_deck_metadata_token(self):
        return self.token_type in (TokenType.DECK_NAME, TokenType.DECK_SECTION_NAME)

    @property
    def is_deck_section(self):
        return self.token_type == TokenType.DECK_SECTION_NAME

    @property
    def is_message_token(self):
        return self.token_type in (
            TokenType.COMMENT,
            TokenType.UNKNOWN_CARD,
            TokenType.UNKNOWN_TEXT,
            TokenType.WARNING_MESSAGE,
        )

    @property
    def foil_marker(self):
        if not self.is_card_token:
            return ""
        return " - (Foil)" if self.is_foil else ""

    @property
    def mana_symbol_tag(self):
        if self.card is None:
            return ""
        mana_cost = self.card.mana_cost
        if not mana_cost:
            return ""  # for cards w/ no mana cost (e.g. lands)
        mana_syms = mana_cost.replace("}", "-").replace("{", "").split("-")
        mana_sys = [m.strip().lower() for m in mana_syms]
        template_tag = '<i class="ms ms-{symbol} ms-cost"></i>'
        tag = ""
        for symbol in mana_sys:
            symbol = symbol.strip()
            if symbol:
                tag += template_tag.format(symbol=symbol)
        return tag

    # CSS class
    WARN_MSG_CLASS = "warn_msg"
    COMMENT_CLASS = "comment"

    DECKNAME_CLASS = "deckname"
    SECTION_CLASS = "section"
    CARDTYPE_CLASS = "cardtype"
    CMC_CLASS = "cmc"
    RARITY_CLASS = "rarity"

    def _token_css_class(self, token_type: TokenType) -> str:
        if token_type in (TokenType.UNKNOWN_CARD, TokenType.WARNING_MESSAGE):
            return self.WARN_MSG_CLASS
        if token_type == TokenType.COMMENT:
            return self.COMMENT_CLASS
        if token_type == TokenType.DECK_NAME:
            return self.DECKNAME_CLASS
        if token_type == TokenType.DECK_SECTION_NAME:
            return self.SECTION_CLASS
        if token_type == TokenType.CARD_TYPE:
            return self.CARDTYPE_CLASS
        if token_type == TokenType.CARD_RARITY:
            return self.RARITY_CLASS
        if token_type in (TokenType.CARD_CMC, TokenType.MANA_COLOUR):
            return self.CMC_CLASS
        if token_type == TokenType.UNKNOWN_TEXT:
            return ""
        return ""

    @property
    def repr_tag(self):
        if self.is_card_token:
            extra = (
                "(BANNED)"
                if self.token_type == TokenType.BANNED_CARD
                else "(RESTRICTED)"
                if self.token_type == TokenType.RESTRICTED_CARD
                else "(F)"
                if self.is_foil and self.card.has_foil
                else ""
            )
            return (
                '<a href="{image_link}" title="{card_name}" target="_blank">{card_name} [{card_set}]'
                "{extra}</a>".format(
                    image_link=self.card.art.normal,
                    card_name=self.card.name,
                    card_set=self.card.set_code.upper(),
                    extra=extra,
                )
            )
        else:
            css_class = self._token_css_class(self.token_type)
            template_tag = '<span class="{css_class}">{text}</span>'
            if (self.token_type == TokenType.MANA_COLOUR) or (
                self.token_type == TokenType.CARD_TYPE
                and self.text not in ("Spells", "Lands")
            ):
                if "{" in self.text:
                    colours = self.text.replace("{", "").replace("}", "-").split("-")
                    colours = [c.strip().lower() for c in colours]
                else:
                    # assuming text like WUG
                    colours = (
                        self.text.replace(" ", "").strip().lower(),
                    )  # works even with multi-col
                mana_tag = '<i class="ms ms-{symbol} ms-cost"></i>'
                ttext = ""
                for symbol in colours:
                    ttext += mana_tag.format(symbol=symbol)
                if self.quantity > 0:
                    ttext += f" ({self.quantity})"
            elif self.token_type == TokenType.CARD_CMC:
                ttext = "CMC: " + '<i class="ms ms-{c} ms-cost"></i>'.format(
                    c=self.text.split("-")[1].strip()
                )
            else:
                if self.quantity == 0:
                    ttext = self.text
                else:
                    ttext = f"{self.text} ({self.quantity})"

            return template_tag.format(css_class=css_class, text=ttext)

    @property
    def to_html(self) -> str:
        table_row_tag = "<tr>{cells}</tr>"
        td_template_card_mana = "<td>{amount}</td><td>{card}</td><td>{mana}</td>"
        td_template_card_nomana = '<td>{amount}</td><td colspan="2">{card}</td>'
        td_template_nocard = '<td colspan="3">{text}</td>'
        if self.is_card_token:
            if self.card.mana_cost:
                td_tag = td_template_card_mana.format(
                    amount=self.quantity, card=self.repr_tag, mana=self.mana_symbol_tag
                )
            else:
                td_tag = td_template_card_nomana.format(
                    amount=self.quantity, card=self.repr_tag
                )
        else:
            td_tag = td_template_nocard.format(text=self.repr_tag)
        return table_row_tag.format(cells=td_tag)


class DeckValidationError(Exception):
    def to_html(self):
        return '<p class="text-warning">{msg}</p>'.format(msg=str(self))


class MinDeckSizeConstraintError(DeckValidationError):
    def __init__(self, deck_section: DeckSection, current_size: int):
        msg = (
            f"The {deck_section.name} does not contain at "
            f"least {deck_section.min_size} cards. Current size: {current_size}"
        )
        super().__init__(msg)


class MaxDeckSizeConstraintError(DeckValidationError):
    def __init__(self, deck_section: DeckSection, current_size: int):
        msg = (
            f"The {deck_section.name} can contain up to "
            f"{deck_section.max_size} cards. Current size: {current_size}"
        )
        super().__init__(msg)


class TooManyCardCopies(DeckValidationError):
    def __init__(self, card_name: str, current_number: int):
        msg = (
            f"The deck contains too many copies ({current_number}) "
            f"of the card {card_name}."
        )
        super().__init__(msg)


class Deck:

    # GROUPING CONSTANTS
    NOGROUP = "NOGROUP"
    TYPE = "TYPE"
    SPELL = "SPELL"
    RARITY = "RARITY"
    CMC = "CMC"
    COLOUR = "COLOR"

    SUPPORTED_GROUPS = (COLOUR, TYPE, SPELL, RARITY, CMC)

    def __init__(
        self,
        tokens: list[Token],
        name: str = "",
        main_section: DeckSection = MAIN_DECK,
        side_section: DeckSection = SIDEBOARD,
    ):
        self._name = name
        self._mainboard = main_section
        self._sideboard = side_section

        deck_name_token = list(
            filter(lambda t: t.token_type == TokenType.DECK_NAME, tokens)
        )
        if len(deck_name_token):
            self._name = deck_name_token[0].text

        self._deck_cards: dict[str, list[Token]] = {
            self._mainboard.name: [],
            self._sideboard.name: [],
        }
        # a dictionary mapping each token associated to the same card
        # (used in deck validation)
        self._cards_map: dict[str, list[Token]] = defaultdict(list)

        self._create_deck(tokens)

    def _g_by_colour(self) -> list[Token]:
        tokens = list()
        for section in (self._mainboard, self._sideboard):
            key = section.name
            if not len(self._deck_cards[key]):
                continue
            # start with section token
            tokens.append(
                Token.deck_section_token(
                    section_name=key, count=self.total_cards_in(key)
                )
            )
            colours = set(
                [
                    tuple(t.card.color_identity)
                    for t in self._deck_cards[key]
                    if t.card.color_identity
                ]
            )
            colours = sorted(colours, key=lambda ci: ci[0].value)
            for color_identity in colours:
                cards_token_in_group = list(
                    filter(
                        lambda t: t.is_card_token_for_deck
                        and t.card.color_identity
                        and tuple(t.card.color_identity) == color_identity
                        and t.card.type_line != "Land",
                        self._deck_cards[key],
                    )
                )
                total_cards = sum(t.quantity for t in cards_token_in_group)
                if not total_cards:
                    continue
                color_identity_str = "".join(
                    ["%s" % c.name.lower() for c in color_identity]
                )
                mana_colour = Token(
                    token_type=TokenType.MANA_COLOUR,
                    text=color_identity_str,
                    quantity=total_cards,
                )
                tokens.append(mana_colour)
                for card_token in cards_token_in_group:
                    tokens.append(card_token)
            # colorless cards
            colourless_artifacts = list(
                filter(
                    lambda t: t.is_card_token_for_deck
                    and not t.card.color_identity
                    and t.card.type_line == "Artifact",
                    self._deck_cards[key],
                )
            )
            total_artifacts = sum(t.quantity for t in colourless_artifacts)
            if total_artifacts:
                mana_colour = Token(
                    token_type=TokenType.MANA_COLOUR,
                    text="c",
                    quantity=total_artifacts,
                )
                tokens.append(mana_colour)
                for card_token in colourless_artifacts:
                    tokens.append(card_token)

            colourless_lands = list(
                filter(
                    lambda t: t.is_card_token_for_deck
                    and not t.card.color_identity
                    and t.card.type_line == "Land",
                    self._deck_cards[key],
                )
            )
            total_lands = sum(t.quantity for t in colourless_lands)
            if total_lands:
                mana_colour = Token(
                    token_type=TokenType.MANA_COLOUR, text="land", quantity=total_lands,
                )
                tokens.append(mana_colour)
                for card_token in colourless_lands:
                    tokens.append(card_token)

        return tokens

    def _g_by_rarity(self) -> list[Token]:
        tokens = list()
        for section in (self._mainboard, self._sideboard):
            key = section.name
            if not len(self._deck_cards[key]):
                continue
            # start with section token
            tokens.append(
                Token.deck_section_token(
                    section_name=key, count=self.total_cards_in(key)
                )
            )
            rarities = list(set([t.card.rarity for t in self._deck_cards[key]]))
            rarities = sorted(rarities, key=lambda r: r.value)
            for card_rarity in rarities:
                cards_token_in_group = list(
                    filter(
                        lambda t: t.is_card_token_for_deck
                        and t.card.rarity == card_rarity,
                        self._deck_cards[key],
                    )
                )
                total_cards = sum(t.quantity for t in cards_token_in_group)
                rarity_token = Token(
                    token_type=TokenType.CARD_RARITY,
                    text=card_rarity.name.title(),
                    quantity=total_cards,
                )
                tokens.append(rarity_token)
                for card_token in cards_token_in_group:
                    tokens.append(card_token)
        return tokens

    def _g_by_type(self) -> list[Token]:
        tokens = list()
        for section in (self._mainboard, self._sideboard):
            key = section.name
            if not len(self._deck_cards[key]):
                continue
            # start with section token
            tokens.append(
                Token.deck_section_token(
                    section_name=key, count=self.total_cards_in(key)
                )
            )
            # Spells
            cards_token_spells = list(
                filter(
                    lambda t: t.is_card_token_for_deck and t.card.type_line != "Land",
                    self._deck_cards[key],
                )
            )
            total_cards = sum(t.quantity for t in cards_token_spells)
            if not total_cards:
                continue
            spell_token = Token(
                token_type=TokenType.CARD_TYPE, text="Spells", quantity=total_cards,
            )
            tokens.append(spell_token)
            for card_token in cards_token_spells:
                tokens.append(card_token)

            # Lands
            cards_token_lands = list(
                filter(
                    lambda t: t.is_card_token_for_deck and t.card.type_line == "Land",
                    self._deck_cards[key],
                )
            )
            total_cards = sum(t.quantity for t in cards_token_lands)
            if not total_cards:
                continue
            land_token = Token(
                token_type=TokenType.CARD_TYPE, text="Lands", quantity=total_cards,
            )
            tokens.append(land_token)
            for card_token in cards_token_lands:
                tokens.append(card_token)
        return tokens

    def _g_by_cmc(self) -> list[Token]:
        tokens = list()
        for section in (self._mainboard, self._sideboard):
            key = section.name
            if not len(self._deck_cards[key]):
                continue
            # start with section token
            tokens.append(
                Token.deck_section_token(
                    section_name=key, count=self.total_cards_in(key)
                )
            )
            cmcs = set([t.card.cmc for t in self._deck_cards[key]])
            cmcs = sorted(cmcs)
            for cmc in cmcs:
                cards_token_in_group = list(
                    filter(
                        lambda t: t.is_card_token_for_deck and t.card.cmc == cmc,
                        self._deck_cards[key],
                    )
                )
                total_cards = sum(t.quantity for t in cards_token_in_group)
                if not total_cards:
                    continue
                cmc_token = Token(
                    token_type=TokenType.CARD_CMC,
                    text=f"CMC-{int(cmc)}",
                    quantity=total_cards,
                )
                tokens.append(cmc_token)
                for card_token in cards_token_in_group:
                    tokens.append(card_token)
        return tokens

    def _g_by_type_extended(self) -> list[Token]:
        tokens = list()
        for section in (self._mainboard, self._sideboard):
            key = section.name
            if not len(self._deck_cards[key]):
                continue
            # start with section token
            tokens.append(
                Token.deck_section_token(
                    section_name=key, count=self.total_cards_in(key)
                )
            )
            all_card_types = [t.card.type_line.lower() for t in self._deck_cards[key]]
            card_types = list()
            for ctype in all_card_types:
                if ctype.startswith("creature"):
                    card_types.append("creature")
                elif "enchantment" in ctype:
                    card_types.append("enchantment")
                elif "land" in ctype:
                    card_types.append("land")
                else:
                    card_types.append(ctype)
            card_types = sorted(set(card_types))

            for card_type in card_types:
                cards_token_in_group = list(
                    filter(
                        lambda t: t.is_card_token_for_deck
                        and card_type in t.card.type_line.lower(),
                        self._deck_cards[key],
                    )
                )
                total_cards = sum(t.quantity for t in cards_token_in_group)
                if not total_cards:
                    continue

                card_type_token = Token(
                    token_type=TokenType.CARD_TYPE,
                    text=card_type.lower(),
                    quantity=total_cards,
                )
                tokens.append(card_type_token)
                for card_token in cards_token_in_group:
                    tokens.append(card_token)
        return tokens

    def _g_by_no_group(self) -> list[Token]:
        tokens = list()
        for section in (self._mainboard, self._sideboard):
            key = section.name
            if not len(self._deck_cards[key]):
                continue
            # start with section token
            section_token = Token.deck_section_token(
                section_name=key, count=self.total_cards_in(key)
            )
            tokens.append(section_token)
            for card_token in self._deck_cards[key]:
                tokens.append(card_token)
        return tokens

    def _create_deck(self, tokens: list[Token]) -> None:
        tokens_for_deck = filter(lambda t: t.is_card_token_for_deck, tokens)
        for token in tokens_for_deck:
            section = token.deck_section
            if section is not None:
                key = section.name
                self._deck_cards[key].append(token)
                card_name = token.card.name
                self._cards_map[card_name].append(token)

    def validate(self) -> Optional[list[Exception]]:
        errors = list()

        # deck section size validation
        no_cards_in_md = sum(
            [t.quantity for t in self._deck_cards[self._mainboard.name]]
        )
        no_cards_in_sb = sum(
            [t.quantity for t in self._deck_cards[self._sideboard.name]]
        )

        md_constraint_ok = self._mainboard.min_size <= no_cards_in_md
        sb_constraint_ok = no_cards_in_sb <= self._sideboard.max_size

        if not md_constraint_ok:
            errors.append(MinDeckSizeConstraintError(self._mainboard, no_cards_in_md))

        if not sb_constraint_ok:
            errors.append(MaxDeckSizeConstraintError(self._sideboard, no_cards_in_sb))

        # check card copies
        for card_name in self._cards_map:
            if not len(self._cards_map[card_name]):
                continue
            c_type = self._cards_map[card_name][0].card.type_line
            if "land" in c_type.lower():
                continue
            no_copies = sum([t.quantity for t in self._cards_map[card_name]])
            max_no_copies = (
                1
                if self._cards_map[card_name][0].token_type == TokenType.RESTRICTED_CARD
                else 4
            )
            if no_copies > max_no_copies:
                errors.append(
                    TooManyCardCopies(card_name=card_name, current_number=no_copies)
                )

        return errors

    def total_cards_in(self, section: str) -> int:
        if section not in self._deck_cards:
            return 0
        return sum([t.quantity for t in self._deck_cards[section]])

    def __len__(self):
        return self.total_cards_in(self._mainboard.name) + self.total_cards_in(
            self._sideboard.name
        )

    def deck_list(self, grouping: str) -> list[Token]:
        """"""

        if not grouping or grouping.upper() not in self.SUPPORTED_GROUPS:
            grouping = self.NOGROUP

        if grouping == self.NOGROUP:
            return self._g_by_no_group()
        if grouping == self.COLOUR:
            return self._g_by_colour()
        if grouping == self.RARITY:
            return self._g_by_rarity()
        if grouping == self.CMC:
            return self._g_by_cmc()
        if grouping == self.SPELL:
            return self._g_by_type()
        if grouping == self.TYPE:
            return self._g_by_type_extended()
        return self._g_by_no_group()

    @property
    def is_valid(self) -> bool:
        return len(self.validate()) == 0

    @property
    def name(self):
        return self._name if self._name else "Deck"


class DeckParser:
    """"""

    # Cards Regexps
    SEARCH_SINGLE_SLASH = re.compile("(?<=[^/])\\s*/\\s*(?=[^/])")
    DOUBLE_SLASH = "//"
    LINE_COMMENT_DELIMITER_OR_MD_HEADER = "#"
    ASTERISK = "* "  # Note the blank space after asterisk!
    NO_COLLECTOR_NUMBER = None

    # Core Matching Patterns (initialised in Constructor)
    # ===================================================
    REGRP_DECKNAME = "deckName"
    REX_DECK_NAME = (
        r"^(\/\/\s*)?(?P<pre>(deck|name(\s)?))(\:|=)\s*(?P<%s>([a-zA-Z0-9',\/\-\s\)\]\(\[\#]+))\s*(.*)$"
        % REGRP_DECKNAME
    )
    DECK_NAME_PATTERN = re.compile(REX_DECK_NAME, re.IGNORECASE)

    #  Group placeholders
    REGRP_TOKEN = "token"
    REGRP_COLR1 = "colr1"
    REGRP_COLR2 = "colr2"
    REGRP_MANA = "mana"

    REX_NOCARD = (
        r"^(?P<pre>[^a-zA-Z]*)\s*(?P<title>(\w+[:]\s*))?(?P<%s>[a-zA-Z]+)(?P<post>[^a-zA-Z]*)?$"
        % REGRP_TOKEN
    )
    REX_CMC = (
        r"^(?P<pre>[^a-zA-Z]*)\s*(?P<%s>(C(M)?C(\s)?\d{1,2}))(?P<post>[^\d]*)?$"
        % REGRP_TOKEN
    )
    REX_RARITY = (
        r"^(?P<pre>[^a-zA-Z]*)\s*(?P<%s>((un)?common|(mythic)?\s*(rare)?|land|special))(?P<post>[^a-zA-Z]*)?$"
        % REGRP_TOKEN
    )

    MANA_SYMBOLS = "w|u|b|r|g|c|m|wu|ub|br|rg|gw|wb|ur|bg|rw|gu"
    REX_MANA_SYMBOLS = r"\{(?P<%s>({%s}))\}" % (REGRP_MANA, MANA_SYMBOLS)

    REX_MANA_COLOURS = (
        r"(\{(%s)\})|(white|blue|black|red|green|colo(u)?rless|multicolo(u)?r)"
        % MANA_SYMBOLS
    )
    REX_MANA = r"^(?P<pre>[^a-zA-Z]*)\s*(?P<{colr1}>({manacolours}))((\s|-|\|)(?P<{colr2}>({manacolours})))?(?P<post>[^a-zA-Z]*)?$".format(
        colr1=REGRP_COLR1, colr2=REGRP_COLR2, manacolours=REX_MANA_COLOURS
    )

    # (No Card) Patterns
    NONCARD_PATTERN = re.compile(REX_NOCARD, re.IGNORECASE)
    CMC_PATTERN = re.compile(REX_CMC, re.IGNORECASE)
    CARD_RARITY_PATTERN = re.compile(REX_RARITY, re.IGNORECASE)
    MANA_PATTERN = re.compile(REX_MANA, re.IGNORECASE)
    MANA_SYMBOL_PATTERN = re.compile(REX_MANA_SYMBOLS, re.IGNORECASE)

    # Cards Group Placeholders
    # ========================
    REGRP_SET = "setcode"
    REGRP_COLLNR = "collnr"
    REGRP_CARD = "cardname"
    REGRP_CARDNO = "count"

    REX_CARD_NAME = r"(\[)?(?P<%s>[a-zA-Z0-9&',\.:!\+\"\/\-\s]+)(\])?" % REGRP_CARD
    REX_SET_CODE = r"(?P<%s>[a-zA-Z0-9_]{2,7})" % REGRP_SET
    REX_COLL_NUMBER = r"(?P<%s>\*?[0-9A-Z]+\S?[A-Z]*)" % REGRP_COLLNR
    REX_CARD_COUNT = r"(?P<%s>[\d]{1,2})(?P<mult>x)?" % REGRP_CARDNO

    # Extras - card specs
    # ===================
    REGRP_FOIL_GFISH = "foil"
    REX_FOIL_MTGGOLDFISH = r"(?P<%s>\(F\))?" % REGRP_FOIL_GFISH

    # XMage Sideboard indicator - pushed a bit further with deck section indication
    REGRP_DECK_SEC_XMAGE_STYLE = "decsec"
    REX_DECKSEC_XMAGE = r"(?P<%s>(MB|MD|SB))" % REGRP_DECK_SEC_XMAGE_STYLE

    # 1. Card-Set Request (Amount?, CardName, Set) w/ extras
    REX_CARD_SET_REQUEST = (
        r"(%s\s*:\s*)?(%s\s)?\s*%s\s*(\s|\||\(|\[|\{)\s?%s(\s|\)|\]|\})?\s*%s"
        % (
            REX_DECKSEC_XMAGE,
            REX_CARD_COUNT,
            REX_CARD_NAME,
            REX_SET_CODE,
            REX_FOIL_MTGGOLDFISH,
        )
    )
    CARD_SET_PATTERN = re.compile(REX_CARD_SET_REQUEST)

    # 2. Set-Card Request (Amount?, Set, CardName) w/ extras
    REX_SET_CARD_REQUEST = (
        r"(%s\s*:\s*)?(%s\s)?\s*(\(|\[|\{)?%s(\s+|\)|\]|\}|\|)\s*%s\s*%s\s*"
        % (
            REX_DECKSEC_XMAGE,
            REX_CARD_COUNT,
            REX_SET_CODE,
            REX_CARD_NAME,
            REX_FOIL_MTGGOLDFISH,
        )
    )
    SET_CARD_PATTERN = re.compile(REX_SET_CARD_REQUEST)

    # 3. Full-Request (Amount?, CardName, Set, Collector Number|Art Index) w/ extras - MTGArena Format
    REX_FULL_REQUEST_CARD_SET = (
        r"(%s\s*:\s*)?(%s\s)?\s*%s\s*(\||\(|\[|\{|\s)%s(\s|\)|\]|\})?(\s+|\|\s*)%s\s*%s\s*"
        % (
            REX_DECKSEC_XMAGE,
            REX_CARD_COUNT,
            REX_CARD_NAME,
            REX_SET_CODE,
            REX_COLL_NUMBER,
            REX_FOIL_MTGGOLDFISH,
        )
    )
    CARD_SET_COLLNO_PATTERN = re.compile(REX_FULL_REQUEST_CARD_SET)

    # 4. Full-Request (Amount?, Set, CardName, Collector Number|Art Index) w/ extras
    REX_FULL_REQUEST_SET_CARD = (
        r"^(%s\s*:\s*)?(%s\s)?\s*(\(|\[|\{)?%s(\s+|\)|\]|\}|\|)\s*%s(\s+|\|\s*)%s\s*%s$"
        % (
            REX_DECKSEC_XMAGE,
            REX_CARD_COUNT,
            REX_SET_CODE,
            REX_CARD_NAME,
            REX_COLL_NUMBER,
            REX_FOIL_MTGGOLDFISH,
        )
    )
    SET_CARD_COLLNO_PATTERN = re.compile(REX_FULL_REQUEST_SET_CARD)

    # 5. (MTGGoldfish mostly) (Amount?, Card Name, <Collector Number>, Set) w/ extras
    REX_FULL_REQUEST_CARD_COLLNO_SET = (
        r"^(%s\s*:\s*)?(%s\s)?\s*%s\s+(\<%s\>)\s*(\(|\[|\{)?%s(\s+|\)|\]|\}|\|)\s*%s$"
        % (
            REX_DECKSEC_XMAGE,
            REX_CARD_COUNT,
            REX_CARD_NAME,
            REX_COLL_NUMBER,
            REX_SET_CODE,
            REX_FOIL_MTGGOLDFISH,
        )
    )
    CARD_COLLNO_SET_PATTERN = re.compile(REX_FULL_REQUEST_CARD_COLLNO_SET)

    # 6. XMage format (Amount?, [Set:Collector Number] Card Name) w/ extras
    REX_FULL_REQUEST_XMAGE = r"^(%s\s*:\s*)?(%s\s)?\s*(\[)?%s:%s(\])\s+%s\s*%s$" % (
        REX_DECKSEC_XMAGE,
        REX_CARD_COUNT,
        REX_SET_CODE,
        REX_COLL_NUMBER,
        REX_CARD_NAME,
        REX_FOIL_MTGGOLDFISH,
    )
    SET_COLLNO_CARD_XMAGE_PATTERN = re.compile(REX_FULL_REQUEST_XMAGE)

    # 7. Card-Only Request (Amount?)
    REX_CARDONLY = r"(%s\s*:\s*)?(%s\s)?\s*%s\s*%s" % (
        REX_DECKSEC_XMAGE,
        REX_CARD_COUNT,
        REX_CARD_NAME,
        REX_FOIL_MTGGOLDFISH,
    )
    CARD_ONLY_PATTERN = re.compile(REX_CARDONLY)

    CARD_TYPES = [
        "artifacts",
        "enchantments",
        "creatures",
        "instants",
        "lands",
        "sorceries",
        "aura",
        "mana",
        "spell",
        "other spell",
    ]

    DECK_SECTIONS = ("side", "sideboard", "sb", "main", "card", "mainboard", "deck")

    def __init__(self, cards_db: ScryfallDB):
        self._db = cards_db

    @property
    def card_types(self):
        return self.CARD_TYPES

    def parse_card_list(self, deck_list: list[str]) -> list[Token]:
        tokens = list()
        current_deck_section = MAIN_DECK

        for line_no, line in enumerate(deck_list):
            if not line and not line.strip():
                # lookahead to see if this is the sideboard empty-line separator
                # for this to happen, these are the conditions to hold:
                # - current deck section is MAIN
                # - x60 (CARD) tokens have been parsed already - AT LEAST - this narrows down a lot!
                # - there is a NEXT LINE
                # - the NEXT LINE will be parsed as Legal Card (LOOK AHEAD)
                if (
                    len(tokens)  # there is at least one token
                    and current_deck_section.name
                    == MAIN_DECK.name  # current section is MD
                    and sum(
                        [
                            t.quantity
                            for t in filter(
                                lambda t: t.token_type == TokenType.LEGAL_CARD
                                and t.deck_section.name == MAIN_DECK.name,
                                tokens,
                            )
                        ]
                    )
                    >= 60  # there are at least 60 cards in MD
                    and line_no + 1
                    < len(deck_list)  # not last line and there is a next line
                ):
                    # look_ahead
                    token_ahead, _ = self._parse_line(
                        deck_list[line_no + 1], current_deck_section
                    )
                    if (
                        token_ahead is not None
                        and token_ahead.token_type == TokenType.LEGAL_CARD
                    ):
                        current_deck_section = SIDEBOARD
                        any_mb_token = (
                            len(
                                list(
                                    filter(
                                        lambda t: t.token_type
                                        == TokenType.DECK_SECTION_NAME
                                        and t.text == MAIN_DECK.name,
                                        tokens,
                                    )
                                )
                            )
                            > 0
                        )
                        if not any_mb_token:
                            md_token = Token.deck_section_token(MAIN_DECK.name)
                            if tokens[0].token_type == TokenType.DECK_NAME:
                                tokens.insert(1, md_token)
                            else:
                                tokens.insert(0, md_token)
                        tokens.append(Token.deck_section_token(SIDEBOARD.name))
                        continue  # skip to next line to parse (again)

            token, section = self._parse_line(line, current_deck_section)
            if token is None:
                continue

            if section.name != current_deck_section.name:
                current_deck_section = section

            if (
                not token.is_token_for_deck
                and token.token_type != TokenType.DECK_SECTION_NAME
            ):
                tokens.append(token)
                continue

            if token.token_type == TokenType.DECK_NAME:
                tokens.insert(0, token)
                continue

            if token.token_type == TokenType.DECK_SECTION_NAME:
                current_deck_section = (
                    MAIN_DECK if token.text == MAIN_DECK.name else SIDEBOARD
                )
                tokens.append(token)
                continue

            tokens.append(token)

        # Last validation
        if (
            all(
                [
                    True
                    if t.deck_section is None
                    else t.deck_section.name == MAIN_DECK.name
                    for t in tokens
                ]
            )
            and len(
                list(
                    filter(
                        lambda t: t.token_type == TokenType.DECK_SECTION_NAME
                        and t.text == MAIN_DECK.name,
                        tokens,
                    )
                )
            )
            == 0
        ):
            md_token = Token.deck_section_token(MAIN_DECK.name)
            tokens.insert(0, md_token)

        return tokens

    def _parse_line(
        self, line: str, deck_section: DeckSection
    ) -> tuple[Optional[Token], DeckSection]:

        if not line or not line.strip():
            return None, deck_section
        ref_line = line.strip().replace(chr(8216), "'").replace(chr(8217), "'")
        ref_line = self._purge_all_links(ref_line)

        if line.startswith(self.LINE_COMMENT_DELIMITER_OR_MD_HEADER):
            line = line.replace(self.LINE_COMMENT_DELIMITER_OR_MD_HEADER, "")
        else:
            line = ref_line.strip()

        # Some websites export split-card names with a single slash. Replace with double slash
        line = self.SEARCH_SINGLE_SLASH.sub(" // ", line)
        if line.startswith(self.ASTERISK):  # Markdown card-list (tapped out md export)
            line = line[2:]

        # == Patches to Corner Cases
        # ===========================
        # FIX Commander in Deckstats Export
        if line.endswith("#!Commander"):
            return None, deck_section  # Just skip this line

        token, deck_section = self._parse_card_token(line, deck_section)
        if token:
            return token, deck_section
        token = self._parse_non_card_token(line)
        if token:
            return token, deck_section

        # Only non-card token not handled in the parse_non_card_token method
        # so checking for comments again
        if ref_line.startswith(self.DOUBLE_SLASH) or ref_line.startswith(
            self.LINE_COMMENT_DELIMITER_OR_MD_HEADER
        ):
            return Token(token_type=TokenType.COMMENT, text=ref_line), deck_section
        return Token(token_type=TokenType.UNKNOWN_TEXT, text=ref_line), deck_section

    def _parse_card_token(
        self, text: str, current_deck_section: DeckSection
    ) -> Optional[tuple[Token, DeckSection]]:
        line = text.strip()
        matchers = self._get_regex_matchers(line)
        # ultimately, we will return an unknown_card_token (or None)
        # if no card will be matched with the input request text
        unknown_card_token = None
        for matcher in matchers:
            card_name = self._get_rex_group(matcher, self.REGRP_CARD)
            if not card_name:
                continue

            card_name = card_name.strip()
            amount = self._get_rex_group(matcher, self.REGRP_CARDNO)
            set_code = self._get_rex_group(matcher, self.REGRP_SET)
            coll_number = self._get_rex_group(matcher, self.REGRP_COLLNR)
            foil_group = self._get_rex_group(matcher, self.REGRP_FOIL_GFISH)
            deck_sec_from_card_line = self._get_rex_group(
                matcher, self.REGRP_DECK_SEC_XMAGE_STYLE
            )
            is_foil = foil_group is not None
            card_amount = int(amount) if amount is not None else 1
            deck_section_from_line = self._get_deck_section_from_card_line(
                deck_sec_from_card_line
            )
            set_code = set_code.lower() if set_code else None
            card_deck_section = (
                deck_section_from_line
                if deck_sec_from_card_line is not None
                else current_deck_section
            )

            if self._db.in_banned_list(card_name=card_name):
                return (
                    Token.banned_card_token(card_name=card_name, count=card_amount),
                    card_deck_section,
                )

            if card_name not in self._db:
                if amount:
                    # it seems the text could be a potential card as there is an amount specied.
                    # Therefore, we will keep this as a potential hint for an unknown card.
                    # whilst we do keep looking for another matcher to parse the request.
                    unknown_card_token = Token(
                        token_type=TokenType.UNKNOWN_CARD, text=text
                    )
                continue
            collector_number = coll_number if coll_number else self.NO_COLLECTOR_NUMBER
            # if any collector number, it will be tried to convert specific collector number
            # to an art index (useful for lands)
            try:
                art_index = int(collector_number) if collector_number else None
            except ValueError:
                art_index = None

            if set_code:
                # ok so now we know the card name is correct (as in, it's a hit in the DB).
                # let's now check the setcode
                if not self._db.has_set(set_code=set_code):
                    unknown_card_token = Token.unknown_card_token(
                        card_name=card_name, set_code=set_code, count=card_amount
                    )
                    continue

                # we now have both card name and set checked -
                # we just need to be sure about collector number (if any) and if that card can
                # be actually found in the requested set.
                # IOW: we should account for wrong request e.g. Counterspell | FEM
                matched_card = None
                if collector_number:
                    try:
                        matched_card = next(
                            self._db.lookup(
                                card_name=card_name,
                                set_code=set_code,
                                set_collector_number=collector_number,
                            )
                        )
                    except StopIteration:
                        matched_card = None

                if not matched_card and art_index:
                    try:
                        matched_card = next(
                            self._db.lookup(
                                card_name=card_name,
                                set_code=set_code,
                                set_art_index=art_index,
                            )
                        )
                    except StopIteration:
                        matched_card = None

                if not matched_card:
                    try:
                        matched_card = next(
                            self._db.lookup(
                                card_name=card_name, set_code=set_code, unique=True
                            )
                        )
                    except StopIteration:
                        matched_card = None

                if not matched_card:
                    return (
                        Token.unknown_card_token(
                            card_name=card_name, set_code=set_code, count=card_amount
                        ),
                        card_deck_section,
                    )
                return (
                    Token.legal_card_token(
                        card=matched_card,
                        count=card_amount,
                        deck_section=card_deck_section,
                        card_has_setcode=True,
                        is_foil=is_foil,
                    ),
                    card_deck_section,
                )
            # ok so at this point, we can simply ignore everything but the card name -
            # as set code does not exist
            # At this stage, we know the card name exists in the DB so a Card MUST be found
            # and exact card will be returned based on the Preferred sets specified in the DB
            card = next(self._db.lookup(card_name=card_name, unique=True))
            return (
                Token.legal_card_token(
                    card=card,
                    count=card_amount,
                    deck_section=card_deck_section,
                    card_has_setcode=False,
                    is_foil=is_foil,
                ),
                card_deck_section,
            )

        return unknown_card_token, current_deck_section

    # ================================
    # PARSE CARD TOKEN UTILITY METHODS
    # ================================

    @staticmethod
    def _purge_all_links(line: str) -> str:
        """purge any html/URL link present in lines.
        useful to get rid of amenities of MD decklist export"""

        url_pattern = r"(?P<protocol>((https|ftp|file|http):))(?P<sep>((//|\\)+))(?P<url>([\w\d:#@%/;$~_?+-=\\.&]*))"
        pattern = re.compile(url_pattern, re.IGNORECASE)
        matcher = pattern.search(line)
        if matcher:
            for group in matcher.groups():
                line = line.replace(group, "").strip()
        if line.endswith("()"):
            return line[:-2]
        return line

    def _get_rex_group(
        self, matcher: re.Match[AnyStr], group_name: str
    ) -> Optional[str]:
        try:
            rex_group = matcher.group(group_name)
        except IndexError:
            return None
        return rex_group

    def _get_regex_matchers(self, line: str) -> list[re.Match[AnyStr]]:
        matches = list()
        patterns_with_coll_number = (
            self.CARD_SET_COLLNO_PATTERN,
            self.SET_CARD_COLLNO_PATTERN,
            self.CARD_COLLNO_SET_PATTERN,
            self.SET_COLLNO_CARD_XMAGE_PATTERN,
        )

        for pattern in patterns_with_coll_number:
            match = pattern.search(line)
            if (
                match
                and self._get_rex_group(match, self.REGRP_SET)
                and self._get_rex_group(match, self.REGRP_COLLNR)
            ):
                matches.append(match)

        other_patterns = (
            self.CARD_SET_PATTERN,
            self.SET_CARD_PATTERN,
            self.CARD_ONLY_PATTERN,
        )

        for pattern in other_patterns:
            match = pattern.search(line)
            if match:
                matches.append(match)

        return matches

    @staticmethod
    def _get_deck_section_from_card_line(
        deck_sec_in_line: str,
    ) -> Optional[DeckSection]:
        if not deck_sec_in_line:
            return None
        if deck_sec_in_line in ("MB", "MD"):
            return MAIN_DECK
        else:
            return SIDEBOARD

    # -------------------------------------------------------------------------

    def _parse_non_card_token(self, text: str) -> Optional[Token]:
        if self._is_deck_section_name(text):
            token_text = self._noncard_token_match(text)
            return Token.deck_section_token(token_text)

        if self._is_card_cmc_token(text):
            token_text = self._get_cardcmc_match(text)
            return Token(token_type=TokenType.CARD_CMC, text=token_text)

        if self._is_card_rarity_token(text):
            token_match = self._card_rarity_token_match(text)
            if token_match and len(token_match.strip()):
                return Token(token_type=TokenType.CARD_RARITY, text=token_match)
            return None

        if self._is_card_type(text):
            token_match = self._noncard_token_match(text)
            return Token(token_type=TokenType.CARD_TYPE, text=token_match)

        if self._is_mana_token(text):
            token_match = self._get_mana_token_match(text)
            return Token(token_type=TokenType.MANA_COLOUR, text=token_match)

        if self._is_deck_name(text):
            deck_name = self._deck_name_match(text)
            return Token(token_type=TokenType.DECK_NAME, text=deck_name.strip())

        return None

    def _get_cardcmc_match(self, text: str) -> str:
        matched_token = self._card_cmc_token_match(text)
        matched_token = matched_token.upper()
        if "CC" in matched_token:
            matched_token = matched_token.replace("CC", "").strip()
        else:
            matched_token = matched_token.replace("CMC", "").strip()
        return f"CMC: {matched_token}"

    def _get_mana_token_match(self, text: str) -> str:
        first_mana, *second_mana = self._mana_token_match(text)
        token_text = "{%s}%s" % (
            first_mana,
            "{%s}" % second_mana if second_mana else "",
        )
        return token_text

    # ====================================
    # PARSE NON-CARD TOKEN UTILITY METHODS
    # ====================================

    # -----------------------------------------------------------------------------
    # Note: Card types, CMC, and Rarity Tokens are **only** used for style formatting
    # in the Import Editor. This won't affect the import process in any way.
    # The use of these tokens has been borrowed by Deckstats.net format export.
    # -----------------------------------------------------------------------------

    def _is_deck_section_name(self, text: str) -> bool:
        non_card_token = self._noncard_token_match(text)
        if not non_card_token:
            return False
        return non_card_token.lower() in self.DECK_SECTIONS

    def _is_deck_name(self, text: str) -> bool:
        if not text:
            return False
        line = text.strip()
        match = self.DECK_NAME_PATTERN.search(line)
        return match is not None

    def _is_card_type(self, text: str) -> bool:
        non_card_token = self._noncard_token_match(text)
        if not non_card_token:
            return False
        return non_card_token.lower() in self.CARD_TYPES

    def _is_card_rarity_token(self, text: str) -> bool:
        return len(self._card_rarity_token_match(text)) > 0

    def _is_card_cmc_token(self, text: str) -> bool:
        return len(self._card_cmc_token_match(text)) > 0

    def _is_mana_token(self, text: str) -> bool:
        return len(self._mana_token_match(text)) > 0

    # ---- MATCH METHODS ------

    def _noncard_token_match(self, text: str) -> str:
        if not text:
            return ""
        line = text.strip()
        match = self.NONCARD_PATTERN.search(line)
        if not match:
            return ""
        return match.group(self.REGRP_TOKEN)

    def _card_rarity_token_match(self, text: str) -> str:
        if not text:
            return ""
        line = text.strip()
        card_rarity_match = self.CARD_RARITY_PATTERN.search(line)
        if not card_rarity_match:
            return ""
        return card_rarity_match.group(self.REGRP_TOKEN)

    def _card_cmc_token_match(self, text: str) -> str:
        if not text:
            return ""
        line = text.strip()
        token_match = self.CMC_PATTERN.search(line)
        if not token_match:
            return ""
        return token_match.group(self.REGRP_TOKEN)

    def _mana_token_match(self, text: str) -> Union[str, tuple[str, str]]:
        if not text:
            return ""
        line = text.strip()
        match = self.MANA_PATTERN.search(line)
        if not match:
            return ""
        first_mana = match.group(self.REGRP_COLR1)
        mana_symbol_match = self.MANA_SYMBOL_PATTERN.search(first_mana)
        if mana_symbol_match:
            first_mana = mana_symbol_match.group(self.REGRP_MANA)

        second_mana = match.group(self.REGRP_COLR2)
        mana_symbol_match = self.MANA_SYMBOL_PATTERN.search(second_mana)
        if mana_symbol_match:
            second_mana = mana_symbol_match.group(self.REGRP_MANA)

        return first_mana, second_mana

    def _deck_name_match(self, text: str) -> str:
        if not text:
            return ""
        line = text.strip()
        match = self.DECK_NAME_PATTERN.search(line)
        if match:
            return match.group(self.REGRP_DECKNAME)
        return ""


if __name__ == "__main__":
    import json

    db = json.load(open("data/premodern_cards.json"))
    from data import ScryfallDB

    cards = ScryfallDB(db)
    parser = DeckParser(cards)
    parser.parse_card_list(["17 Island (mir) 336"])
