# Cards
from dataclasses import dataclass, field
from itertools import chain
from enum import Enum
from datetime import date, datetime

# ScryfallDB
from typing import Iterable, Generator, Sequence, Optional

# from pytrie import StringTrie as Trie

# -----
# Cards
# -----


@dataclass
class CardImagery:
    border_crop: str
    art_crop: str
    large: str
    normal: str
    small: str

    def to_json(self):
        j_repr = dict()
        j_repr["border_crop"] = self.border_crop
        j_repr["art_crop"] = self.art_crop
        j_repr["large"] = self.large
        j_repr["normal"] = self.normal
        j_repr["small"] = self.small
        return j_repr


class ScryfallEnum(Enum):
    def to_json(self):
        return self.name


class Color(ScryfallEnum):
    W = 0
    U = 1
    B = 2
    R = 3
    G = 4


class Rarity(ScryfallEnum):
    COMMON = 0
    UNCOMMON = 1
    RARE = 2
    MYTHIC = 3
    SPECIAL = 4


@dataclass
class Card:
    cid: str
    scryfall_uri: str
    gatherer_uri: Optional[str]

    # card info
    name: str
    released_at: str
    release_date: date = field(init=False)
    colors: Optional[list[Color]]
    color_identity: Optional[list[Color]]
    mana_cost: Optional[str]
    cmc: Optional[float]
    type_line: Optional[str]
    oracle_text: Optional[str]
    legalities: dict[str, str]

    # set info
    set_code: str
    set_name: str
    set_type: str
    set_uri: str
    collector_number: str
    rarity: Rarity

    # card art
    art: Optional[CardImagery]
    artist: str
    frame: str
    border_color: str
    has_foil: bool = False

    def __post_init__(self):
        self.release_date = datetime.strptime(self.released_at, "%Y-%m-%d")

    def to_json(self):
        json_repr = {}
        for field_name, field_value in self.__dict__.items():
            if field_name == "release_date" or field_value is None:
                continue  # skip
            if field_name in ("colors", "color_identity"):
                json_value = [c.to_json() for c in field_value]
            elif field_name in ("art", "rarity"):
                json_value = field_value.to_json()
            else:
                json_value = field_value
            json_repr[field_name] = json_value
        return json_repr


# -----------
# Scryfall DB
# -----------

PREMODERN_SETS = (
    "4ed",
    "ice",
    "chr",
    "hml",
    "all",
    "mir",
    "vis",
    "5ed",
    "wth",
    "tmp",
    "sth",
    "exo",
    "usg",
    "ulg",
    "6ed",
    "uds",
    "mmq",
    "nem",
    "pcy",
    "inv",
    "pls",
    "7ed",
    "apc",
    "ody",
    "tor",
    "jud",
    "ons",
    "lgn",
    "scg",
)

PREMODERN_EXTENDED_SETS = (
    "4ed",
    "ice",
    "chr",
    "rin",  # Rinascimento
    "ren",  # Renaissance
    "hml",
    "ptc",  # Pro Tour Collector Set
    "all",
    "plgm",  # DCI Legends Membership
    "parl",  # Arena League 96
    "mir",
    "vis",
    "5ed",
    "por",  # Portal
    "wth",
    "wc97",  # WC97
    "ptmp",  # Tempest Promos
    "tmp",
    "jgp",  # Judge Gift Cards 1998
    "psth",  # Stronghold Promos
    "sth",
    "pexo",  # Exodus Promos
    "exo",
    "p02",  # Portal Second Age
    "ugl",  # Unglued
    "tugl",  # Unglued Tokens
    "wc98",  # WC98
    "palp",  # Asia Pacific Land Program
    "pusg",  # Urza's Saga Promos
    "usg",
    "ath",  # Anthologies
    "g99",  # Judge Gift Cards 1999
    "pal99",  # Arena League 1999
    "pulg",  # Urza's Legacy Promos
    "ulg",
    "6ed",
    "puds",  # Urza's Destiny Promos
    "uds",
    "s99",  # Starter 1999
    "wc99",  # WC99
    "pwos",  # Wizards of the Coast Online Store
    "pmmq",  # Mercadian Masques Promos
    "mmq",
    "brb",  # Battle Royal Box Set
    "psus",  # Junior Super Series
    "fnm",  # Friday Night Magic
    "g00",  # Judge Gift Cards 2000
    "pal00",  # Arena League 2000
    "pelp",  # European Land Program
    "pnem",  # Nemesis Promos
    "nem",
    "ppcy",  # Prophecy Promos
    "pcy",
    "wc00",  # WC00
    "btd",  # Beatdown Box Set
    "pinv",  # Invasion Promos
    "inv",
    "g01",  # Judge Gift Cards 2001
    "f01",  # Friday Night Magic 2001
    "mpr",  # Magic Player Reward
    "pal01",  # Arena League 2001
    "ppls",  # Planeshift Promos
    "pls",
    "7ed",
    "papc",  # Apocalypse Promos
    "apc",
    "wc01",  # WC01
    "pody",  # Odyssey Promos
    "ody",
    "dkm",  # Deckmasters
    "g02",  # Judge Gift Cards 2002
    "f02",  # Friday Night Magic 2002
    "pr2",  # Magic Player Rewards 2002
    "pal02",  # Arena League 2002
    "ptor",  # Torment Promos
    "tor",
    "pjud",  # Judgemt Promos
    "jud",
    "wc02",  # WC02
    "pons",  # Onslaught Promos
    "ons",
    "p03",  # Magic Player Reward 2003
    "f03",  # Friday Night Magic 2003
    "g03",  # Judge Gift Cards 2003
    "pal03",  # Arena League 2003
    "plgn",  # Legions Promos
    "lgn",
    "pscg",  # Scourge Promos
    "scg",
    "wc03",  # WC03
    "f04",  # Friday Night Magic 2004
)

# SCRYFALL_DEFAULT_CARDS_URL = "https://raw.githubusercontent.com/premodernitalia/deck-recognizer/main/data/premodern_cards.json"
SCRYFALL_DEFAULT_CARDS_URL = "https://raw.githubusercontent.com/premodernitalia/deck-recognizer/main/data/premodern_db_compressed.bz"
# SCRYFALL_DEFAULT_CARDS_URL = "data/premodern_db_compressed.bz"
BANNED_PREMODERN_CARDS = (
    "Amulet of Quoz",
    "Balance",
    "Brainstorm",
    "Bronze Tablet",
    "Channel",
    "Demonic Consultation",
    "Earthcraft",
    "Entomb",
    "Flash",
    "Force of Will",
    "Goblin Recruiter",
    "Grim Monolith",
    "Jeweled Bird",
    "Mana Vault",
    "Memory Jar",
    "Mind Twist",
    "Mind's Desire",
    "Mystical Tutor",
    "Necropotence",
    "Rebirth",
    "Strip Mine",
    "Tempest Efreet",
    "Tendrils of Agony",
    "Time Spiral",
    "Timmerian Fiends",
    "Tolarian Academy",
    "Vampiric Tutor",
    "Windfall",
    "Worldgorger Dragon",
    "Yawgmoth's Bargain",
    "Yawgmoth's Will",
)

# Map of different set code between Scryfall and MTGO
SET_RECODE_MAP = {
    "te": "tmp",
    "evg": "dd1",
    "ne": "nem",
    "pr": "pcy",
    "ms3": "mp2",
    "wl": "wth",
    "ul": "ulg",
    "mm": "mmq",
    "pc1": "hop",
    "ud": "uds",
    "mi": "mir",
    "ex": "exo",
    "ms2": "mps",
    "ps": "pls",
    "dar": "dom",
    "ap": "apc",
    "vi": "vis",
    "od": "ody",
    "in": "inv",
    "7e": "7ed",
    "st": "sth",
    "uz": "usg",
}


class ScryfallDB:
    """
    MTG Card Database simple implementation using Scryfall Card DB info.
    The class expects a JSON object (full scryfall db parsed) to gather
    cards info that will be used during deck list parsing.

    Optionally, It is possible to specify a list of "preferred sets" (as in sets
    allowed/normally used in MTG formats) that will be used to automatically
    pick a specific card print, when no specific set is specified.
    (See PREMODERN_SETS and PREMODERN_EXTENDED_SETS as examples)
    """

    def __init__(
        self,
        json_db: dict,
        preferred_sets: tuple[str] = PREMODERN_EXTENDED_SETS,
        banned_list: tuple[str] = BANNED_PREMODERN_CARDS,
        set_recode_map: dict[str, str] = SET_RECODE_MAP,
    ):
        self._db = json_db
        self._cards_map = dict()  # Trie()
        self._load_cards_from_db()
        self._mtg_sets_map = self._init_mtg_sets_map()
        self._preferred_sets = preferred_sets
        self._banned_list = tuple(
            [self.make_dbentry(card_name) for card_name in banned_list]
        )
        self._set_recode_map = set_recode_map

    def _load_cards_from_db(self):
        for entry in self._db:
            if entry.get("lang", "en") != "en":
                continue
            if (
                "games" in entry
                and len(entry["games"]) == 1
                and entry["games"][0] == "mtgo"
            ):
                continue  # skip Online-only Expansion Promo Sets

            art_key = (
                "image_uris"
                if "image_uris" in entry
                else "art"
                if "art" in entry
                else None
            )
            if art_key:
                card_imagery = CardImagery(
                    border_crop=entry[art_key]["border_crop"],
                    art_crop=entry[art_key]["art_crop"],
                    large=entry[art_key]["large"],
                    normal=entry[art_key]["normal"],
                    small=entry[art_key]["small"],
                )
            else:
                card_imagery = None

            if "color_identity" in entry:
                color_identity = [Color[v.upper()] for v in entry["color_identity"]]
            else:
                color_identity = None

            if "colors" in entry:
                colors = [Color[c.upper()] for c in entry["colors"]]
            else:
                colors = None

            rarity = Rarity[entry["rarity"].upper()]
            cid = entry["id"] if "id" in entry else entry["cid"]
            gatherer_uri = (
                entry["related_uris"].get("gatherer", None)
                if "related_uris" in entry
                else entry.get("gatherer_uri", None)
            )
            if "has_foil" in entry:
                has_foil = entry["has_foil"]
            else:
                has_foil = "finishes" in entry and "foil" in entry["finishes"]

            card = Card(
                cid=cid,
                scryfall_uri=entry["scryfall_uri"],
                gatherer_uri=gatherer_uri,
                name=entry["name"],
                released_at=entry["released_at"],
                colors=colors,
                color_identity=color_identity,
                mana_cost=entry.get("mana_cost", None),
                cmc=float(entry.get("cmc", 0)),
                type_line=entry.get("type_line", None),
                oracle_text=entry.get("oracle_text", None),
                legalities=entry["legalities"],
                set_code=entry["set"] if "set" in entry else entry["set_code"],
                set_name=entry["set_name"],
                set_type=entry["set_type"],
                set_uri=entry["set_uri"],
                collector_number=entry["collector_number"],
                rarity=rarity,
                art=card_imagery,
                artist=entry["artist"],
                frame=entry["frame"],
                border_color=entry["border_color"],
                has_foil=has_foil,
            )
            dbentry = self.make_dbentry(card.name)
            self._cards_map.setdefault(dbentry, list())
            self._cards_map[dbentry].append(card)

    @staticmethod
    def make_dbentry(name: str) -> str:
        return name.lower().replace(" ", "-")

    def lookup(
        self,
        card_name: Optional[str] = None,
        set_code: str = None,
        set_art_index: int = None,
        set_collector_number: str = None,
        unique: bool = True,
    ) -> Generator[Card, None, None]:
        """Lookup for Cards in the DB with the specified name.

        Parameters
        ----------
        card_name: str (default None)
            Name of the card to look up (case-insensitive)
            If the provided card name ends with an asterisk (e.g. "altar*" ), an automatic
            prefix card search will be enabled.
            If No Name is provided, a lookup by set_code and/or set_type will be enabled (if any).
        set_code: str (default None)
            If provided, cards' version from the specified `set_code` will be returned.
            If the search doesn't produce any result, the set_code will be automatically tried
            as a prefix, before giving up.
        set_art_index: int (default None)
            Optional search parameter to allow selecting card's art index, in case the card has
            multiple arts from the same set (e.g. "Island TMP 3").
            This search parameter is optional, and it will be ignored if `set_code` is not
            provided. Similarly, with this search parameter, the `unique` parameter will be
            automatically set to True.
            If the provided `set_art_index` does not exist (e.g. "Island TMP 5"), no card
            will be returned (None).
        set_collector_number: str (default None)
            Similar to art_index, this search parameter will allow to search for a card
            given its collector number. If both art_index and collector_number are
            provided in the search query, ONLY COLLECTOR_NUMBER will be used
        unique: bool (default False)
            If True, only one single entry per retrieved Card (if any) will be returned.
        Return
        ------
            (Lazy) Iterable sequence of retrieved Card instances matching the search criteria.
            Empty result set will be returned if no match is found in the DB.
        """

        is_card = (card_name is not None) and len(card_name.replace("*", ""))
        is_set = set_code is not None
        art_index_search = is_set and set_art_index is not None
        collector_number_search = is_set and set_collector_number is not None
        if not any((is_card, is_set)):
            return self._result_set(())

        entries = self.all_cards

        if is_card:
            if card_name.endswith("*"):  # prefix search
                db_key = self.make_dbentry(card_name.replace("*", "").strip())
                # entries = chain.from_iterable(self._cards_map.itervalues(prefix=db_key))
                entries = chain.from_iterable(self._cards_map.values())
            else:
                db_key = self.make_dbentry(card_name)
                entries = self._cards_map.get(db_key, tuple())

        if is_set:  # Lookup by set_code
            set_code = set_code.lower()
            if set_code in self._set_recode_map:
                set_code = self._set_recode_map[set_code]
            elif set_code not in self._mtg_sets_map:
                return self._result_set(())  # Empty result

            filter_setcode = lambda c: c.set_code == set_code
            entries_set = tuple(filter(filter_setcode, entries))
            if not entries_set:
                return self._result_set(())  # Empty result

            # art specific search
            if collector_number_search:
                set_collector_number = str(
                    set_collector_number
                )  # always make sure is string
                filter_cn = lambda c: c.collector_number == set_collector_number
                entries = tuple(filter(filter_cn, entries_set))
            elif art_index_search:
                if len(entries_set) < set_art_index:
                    return self._result_set(())  # Empty result
                return self._result_set(
                    entries_set, index=(set_art_index - 1)
                )  # zero-indexed
            else:
                entries = entries_set
        else:
            # no specific set code has been provided - therefore apply preferred_sets filter, if any
            if self._preferred_sets:
                entries = filter(lambda c: c.set_code in self._preferred_sets, entries)

        entries = tuple(entries)  # make sure entries is a tuple now
        # filter unique values
        if unique and len(entries) > 1:
            self._result_set(entries, index=0)
        return self._result_set(entries)

    @staticmethod
    def _result_set(
        entries: Sequence[Card], index: int = None
    ) -> Generator[Card, None, None]:
        if not entries:
            return None  # empty set
        else:
            entries = sorted(entries, key=lambda c: (c.released_at, c.collector_number))
            if index is not None:
                if len(entries) < index:
                    return None  # empty set
                yield entries[index]
            else:
                for e in entries:
                    yield e

    def __len__(self) -> int:
        return sum(map(len, self._cards_map.values()))

    def __contains__(self, card_name: str) -> bool:
        return len(tuple(self.lookup(card_name))) > 0

    def __getitem__(self, card_name: str) -> tuple[Card]:
        """proxy for lookup with just the card name specified"""
        return tuple(self.lookup(card_name))

    def __iter__(self) -> Iterable[Card]:
        return self.all_cards

    def _init_mtg_sets_map(self) -> dict[str, str]:
        codename_seq = set()
        for entry in self:
            set_code, set_name = entry.set_code, entry.set_name
            codename_seq.add((set_code, set_name))
        return {code: name for code, name in codename_seq}

    @property
    def mtg_sets_map(self) -> dict[str, str]:
        """returns a dictionary mapping expansion codes to their corresponding full names"""
        if not self._mtg_sets_map:
            self._mtg_sets_map = self._init_mtg_sets_map()
        return self._mtg_sets_map

    @property
    def all_cards(self) -> Iterable[Card]:
        for cards in self._cards_map.values():
            for card in cards:
                yield card

    def has_set(self, set_code: str) -> bool:
        return set_code in self._mtg_sets_map or set_code in self._set_recode_map

    def in_banned_list(self, card_name: str) -> bool:
        card_name_entry = self.make_dbentry(card_name)
        return card_name_entry in self._banned_list

    def add_set_code(self, codename: tuple[str, str]) -> None:
        """Method to add any Code-Name expansion set found in the MTG-Manager data
        that is  "missing" from Scryfall"""
        set_code, set_name = codename
        self.mtg_sets_map[set_code] = set_name
