import json
from collections import defaultdict
from deck_parser import DeckSection, TokenType, Token
from deck_parser import MAIN_DECK, SIDEBOARD


class DeckValidationError(Exception):
    def to_html(self):
        return '<p><span class="badge badge-pill badge-danger">Error: </span> {msg}</p>'.format(
            msg=str(self)
        )


class DeckValidationWarning(Exception):
    def to_html(self):
        return '<p><span class="badge badge-pill badge-warning">Warning: </span> {msg}</p>'.format(
            msg=str(self)
        )


class DeckValidationInfo(Exception):
    def to_html(self):
        return '<p><span class="badge badge_pill badge-dark">Check: </span> {msg}</p>'.format(
            msg=str(self)
        )


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


class DeckSectionEmpty(DeckValidationWarning):
    def __init__(self, deck_section: DeckSection):
        msg = f"The {deck_section.name} does not contain any card! "
        super().__init__(msg)


class TooManyCardsWarning(DeckValidationWarning):
    def __init__(self, deck_section: DeckSection, current_size: int):
        msg = f"The {deck_section.name} contains more than {deck_section.min_size}. Current number: {current_size}"
        super().__init__(msg)


class UnknownCard(DeckValidationInfo):
    def __init__(self, card_name: str):
        msg = f'"{card_name}" is unrecognized!'
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
        self._unknown_cards = list()

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
        # (used solely in deck validation)
        self._cards_map: dict[str, list[Token]] = defaultdict(list)

        self._initialise_deck(tokens)

    def _initialise_deck(self, tokens: list[Token]) -> None:
        # Note: tokens come already regrouped for any duplicates from Deck Parser
        tokens_for_deck = filter(lambda t: t.is_card_token_for_deck, tokens)
        for token in tokens_for_deck:
            section = token.deck_section
            if section is not None:
                key = section.name
                self._deck_cards[key].append(token)
                self._cards_map[token.card.name].append(token)

        unknown_cards = filter(lambda t: t.is_unknown_card, tokens)
        for token in unknown_cards:
            self._unknown_cards.append(token)

    def f_group_by_colour(self) -> list[Token]:
        tokens = list()
        for section in (self._mainboard, self._sideboard):
            key = section.name
            if not len(self.cards[key]):
                continue
            # start with section token
            tokens.append(
                Token.DeckSectionToken(section_name=key, count=self.total_cards_in(key))
            )
            colours = set(
                [
                    tuple(t.card.color_identity)
                    for t in self.cards[key]
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
                        self.cards[key],
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
                    self.cards[key],
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
                    self.cards[key],
                )
            )
            total_lands = sum(t.quantity for t in colourless_lands)
            if total_lands:
                mana_colour = Token(
                    token_type=TokenType.MANA_COLOUR,
                    text="land",
                    quantity=total_lands,
                )
                tokens.append(mana_colour)
                for card_token in colourless_lands:
                    tokens.append(card_token)

        return tokens

    def f_group_by_rarity(self) -> list[Token]:
        tokens = list()
        for section in (self._mainboard, self._sideboard):
            key = section.name
            if not len(self.cards[key]):
                continue
            # start with section token
            tokens.append(
                Token.DeckSectionToken(section_name=key, count=self.total_cards_in(key))
            )
            rarities = list(set([t.card.rarity for t in self.cards[key]]))
            rarities = sorted(rarities, key=lambda r: r.value)
            for card_rarity in rarities:
                cards_token_in_group = list(
                    filter(
                        lambda t: t.is_card_token_for_deck
                        and t.card.rarity == card_rarity,
                        self.cards[key],
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

    def f_group_by_type(self) -> list[Token]:
        tokens = list()
        for section in (self._mainboard, self._sideboard):
            key = section.name
            if not len(self.cards[key]):
                continue
            # start with section token
            tokens.append(
                Token.DeckSectionToken(section_name=key, count=self.total_cards_in(key))
            )
            is_land = lambda t: "Land" in t.card.type_line
            # Spells
            cards_token_spells = list(
                filter(
                    lambda t: (t.is_card_token_for_deck) and not is_land(t),
                    self.cards[key],
                )
            )
            total_cards = sum(t.quantity for t in cards_token_spells)
            if not total_cards:
                continue
            spell_token = Token(
                token_type=TokenType.CARD_TYPE,
                text="Spells",
                quantity=total_cards,
            )
            tokens.append(spell_token)
            for card_token in cards_token_spells:
                tokens.append(card_token)

            # Lands
            cards_token_lands = list(
                filter(
                    lambda t: t.is_card_token_for_deck and is_land(t),
                    self.cards[key],
                )
            )
            total_cards = sum(t.quantity for t in cards_token_lands)
            if not total_cards:
                continue
            land_token = Token(
                token_type=TokenType.CARD_TYPE,
                text="Lands",
                quantity=total_cards,
            )
            tokens.append(land_token)
            for card_token in cards_token_lands:
                tokens.append(card_token)
        return tokens

    def f_group_by_cmc(self) -> list[Token]:
        tokens = list()
        for section in (self._mainboard, self._sideboard):
            key = section.name
            if not len(self.cards[key]):
                continue
            # start with section token
            tokens.append(
                Token.DeckSectionToken(section_name=key, count=self.total_cards_in(key))
            )
            cmcs = set([t.card.cmc for t in self.cards[key]])
            cmcs = sorted(cmcs)
            for cmc in cmcs:
                cards_token_in_group = list(
                    filter(
                        lambda t: t.is_card_token_for_deck and t.card.cmc == cmc,
                        self.cards[key],
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

    def f_group_by_type_extended(self) -> list[Token]:
        tokens = list()
        for section in (self._mainboard, self._sideboard):
            key = section.name
            if not len(self.cards[key]):
                continue
            # start with section token
            tokens.append(
                Token.DeckSectionToken(section_name=key, count=self.total_cards_in(key))
            )
            all_card_types = [t.card.type_line.lower() for t in self.cards[key]]
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
                        self.cards[key],
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

    def f_no_group(self) -> list[Token]:
        tokens = list()
        for section in (self._mainboard, self._sideboard):
            key = section.name
            if not len(self.cards[key]):
                continue
            # start with section token
            section_token = Token.DeckSectionToken(
                section_name=key, count=self.total_cards_in(key)
            )
            tokens.append(section_token)
            for card_token in self.cards[key]:
                tokens.append(card_token)
        return tokens

    def validate(self):
        errors = list()
        warnings = list()
        unknown_cards = list()

        # deck section size validation
        no_cards_in_md = sum(
            [
                t.quantity
                for t in self.cards[self._mainboard.name]
                if t.token_type != TokenType.BANNED_CARD
            ]
        )
        no_cards_in_sb = sum(
            [
                t.quantity
                for t in self.cards[self._sideboard.name]
                if t.token_type != TokenType.BANNED_CARD
            ]
        )

        md_constraint_ok = self._mainboard.min_size <= no_cards_in_md
        sb_constraint_ok = no_cards_in_sb <= self._sideboard.max_size

        if not md_constraint_ok:
            errors.append(MinDeckSizeConstraintError(self._mainboard, no_cards_in_md))

        if not sb_constraint_ok:
            errors.append(MaxDeckSizeConstraintError(self._sideboard, no_cards_in_sb))

        if no_cards_in_sb == 0:
            warnings.append(DeckSectionEmpty(deck_section=self._sideboard))

        if no_cards_in_md > 60:
            warnings.append(
                TooManyCardsWarning(
                    deck_section=self._mainboard, current_size=no_cards_in_md
                )
            )

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

        if self._unknown_cards:
            for token in self._unknown_cards:
                unknown_cards.append(UnknownCard(card_name=token.text))

        return tuple(errors), tuple(warnings), tuple(unknown_cards)

    def total_cards_in(self, section: str) -> int:
        if section not in self.cards:
            return 0
        return sum([t.quantity for t in self.cards[section]])

    def __len__(self):
        return self.total_cards_in(self._mainboard.name) + self.total_cards_in(
            self._sideboard.name
        )

    def deck_list(self, grouping: str) -> list[Token]:
        """Generate the deck list (i.e. list of tokens) according to the
        specified grouping strategy"""

        if not grouping or grouping.upper() not in self.SUPPORTED_GROUPS:
            grouping = self.NOGROUP

        if grouping == self.NOGROUP:
            return self.f_no_group()
        if grouping == self.COLOUR:
            return self.f_group_by_colour()
        if grouping == self.RARITY:
            return self.f_group_by_rarity()
        if grouping == self.CMC:
            return self.f_group_by_cmc()
        if grouping == self.SPELL:
            return self.f_group_by_type()
        if grouping == self.TYPE:
            return self.f_group_by_type_extended()
        return self.f_no_group()

    def mainboard_to_json(self) -> str:
        return self._section_to_json(self._mainboard)

    def sideboard_to_json(self) -> str:
        return self._section_to_json(self._sideboard)

    def _section_to_json(self, section: DeckSection) -> str:
        cards_to_json = list()
        for token in self.cards[section.name]:
            if not token.card:
                continue
            cards_to_json.append(
                {"amount": token.quantity, "card": token.card.to_json()}
            )
        return json.dumps(cards_to_json)

    @property
    def is_valid(self) -> bool:
        errors, *rest = self.validate()
        return len(errors) == 0

    @property
    def name(self):
        return self._name if self._name else ""

    @property
    def cards(self):
        return self._deck_cards

    def cards_in_section(self, section_name: str) -> list[Token]:
        return self._deck_cards.get(section_name, None)
