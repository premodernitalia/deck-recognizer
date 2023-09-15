from argparse import ArgumentParser, BooleanOptionalAction
import json
from functools import partial
from itertools import chain
import compress_json


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
    "Land Tax",
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

PREMODERN_EXTENDED_SETS = {
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
}

PREMODERN_SETS = {
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
}


def load_json_data(scryfall_db_path):
    try:
        with open(scryfall_db_path, "r") as scryfall_db_file:
            d = json.loads(scryfall_db_file.read())
    except FileNotFoundError:
        raise RuntimeError(f"DB File not found: {scryfall_db_path}! Please check.")
    else:
        return d


def in_premodern_pool(card_entry) -> bool:
    if card_entry["digital"] or "paper" not in card_entry["games"]:
        return False

    return card_entry["legalities"]["premodern"] == "legal" or (
        card_entry["name"] in BANNED_PREMODERN_CARDS
        and card_entry["set"] in PREMODERN_SETS
    )


def has_target_language(card_entry, langs: tuple[str]) -> bool:
    return card_entry["lang"] in langs


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Small script to create a Premodern DB of cards."
    )
    parser.add_argument(
        "-i",
        "--scryfall",
        help="Path to Scryfall JSON db file",
        dest="scryfall_db",
        required=True,
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Name of the generated JSON file (default: premodern_json_cards.json",
        default="premodern_json_db.json",
        dest="output_filename",
        required=False,
    )
    parser.add_argument(
        "-c",
        "--compress",
        default=False,
        help="Whether or not compress the Premodern DB file extracted.",
        dest="compressed",
        action=BooleanOptionalAction,
        required=False,
    )

    parser.add_argument(
        "-co",
        "--archive-output",
        help="Name of the generated DB archive file (if compressed option is enabled)",
        default="premodern_db_compressed.bz",
        dest="archive_filename",
        required=False,
    )

    parser.add_argument(
        "-l",
        "--languages",
        action="append",
        nargs="*",
        required=False,
        help="Languages of cards to gather (default: En). "
        "NOTE: Requires Scryfall ALL CARDS for multiple langs.",
    )

    args = parser.parse_args()
    print(args)

    if args.languages is None:
        languages = [["en"]]
    else:
        languages = args.languages

    languages = list(chain.from_iterable(languages))
    if "en" not in languages:
        languages.append("en")
    print("Langs: ", languages)
    language_filter = partial(has_target_language, langs=languages)

    scryfall_db = load_json_data(args.scryfall_db)
    premodern_cards = filter(language_filter, filter(in_premodern_pool, scryfall_db))

    premodern_cards = list(premodern_cards)
    print(len(premodern_cards))

    with open(args.output_filename, "w") as premodern_json_file:
        json.dump(premodern_cards, fp=premodern_json_file)

    if args.compressed:
        compress_json.dump(
            premodern_cards,
            args.archive_filename,
            compression_kwargs={"compresslevel": 9},
        )
