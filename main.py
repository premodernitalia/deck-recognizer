import bz2
import json
from functools import partial

import pyodide.ffi

from deck_parser import DeckParser, Deck
from data import ScryfallDB, SCRYFALL_DEFAULT_CARDS_URL
from deck_export import DECK_EXPORTERS
from deck_export import (MTG_GOLDFISH, MTG_ARENA_WITH_VERSION,
                         MTG_ARENA_NO_VERSION, DEC_FORMAT, DCK_FORMAT)

from js import document, console, initialise_previews
from js import showDirectoryPicker, Object

import pyodide_js
from pyodide.ffi import to_js

from pyodide.ffi import create_proxy
from pyodide.http import pyfetch

NO_GROUP_ID = "nogroup"
COLOUR_ID = "color"
RARITY_ID = "rarity"
CMC_ID = "cmc"
SPELL_ID = "spell"
TYPE_ID = "card_type"

FILTER_BUTTONS = {
    NO_GROUP_ID: document.getElementById(NO_GROUP_ID),
    COLOUR_ID: document.getElementById(COLOUR_ID),
    RARITY_ID: document.getElementById(RARITY_ID),
    CMC_ID: document.getElementById(CMC_ID),
    SPELL_ID: document.getElementById(SPELL_ID),
    TYPE_ID: document.getElementById(TYPE_ID),
}

GROUPING = {
    NO_GROUP_ID: Deck.NOGROUP,
    COLOUR_ID: Deck.COLOUR,
    RARITY_ID: Deck.RARITY,
    CMC_ID: Deck.CMC,
    SPELL_ID: Deck.SPELL,
    TYPE_ID: Deck.TYPE,
}

CARDS_DB = None


async def init_db(*args):
    global CARDS_DB
    if CARDS_DB is None:
        console.log("Cards DB INIT.")
        response = await pyfetch(SCRYFALL_DEFAULT_CARDS_URL, method="GET")
        bz_data = await response.memoryview()
        file = bz2.decompress(bz_data)
        json_data = json.loads(file)
        CARDS_DB = ScryfallDB(json_db=json_data)
        console.log("Cards DB INIT Completed.")
    else:
        console.log("Cards DB already initialised!")
    return CARDS_DB


async def parse_deck_list(grouping: str):
    cards_db = await init_db()

    optimise_card_art = document.getElementById("optimise_cardlist").checked
    deck_parser = DeckParser(cards_db=cards_db, optimise_card_art=optimise_card_art)
    card_list = document.getElementById("card_list_entry").value
    card_list = [l.strip() for l in card_list.split("\n")]
    tokens = deck_parser.parse_card_list(card_list)
    deck = Deck(tokens=tokens)
    display_tokens = deck.deck_list(grouping=grouping)

    if display_tokens:
        rows = ""
        for token in display_tokens:
            rows += token.to_html

        document.getElementById("card_list_parsed").innerHTML = rows
        document.getElementById("card_list_parsed").style.display = "table"
        document.getElementById("instructions").style.display = "none"
        document.getElementById("table-wrapper").style.columnCount = 2;

        # call JS function to initialise previews
        initialise_previews()

        deck_name_badge = "" if not deck.name else f'<p><span class="badge badge-pill badge-info">Deck Name: </span>{deck.name}</p>'
        msg = ""
        error_list = ""
        warning_list = ""
        success_badge = ""
        unknown_cards_list = ""

        errors, warnings, unknown_cards = deck.validate()
        for error in errors:
            error_list += error.to_html()
        for warning in warnings:
            warning_list += warning.to_html()
        for unknown_card in unknown_cards:
            unknown_cards_list += unknown_card.to_html()

        if len(errors) == 0:  # DECK IS VALID
            success_badge = '<p><span class="badge badge-pill badge-success">Success:</span> Deck is valid!</p>'

            # Get list ready for posting
            mtg_goldfish_func = partial(export_mtg_goldfish, deck=deck, cards_db=CARDS_DB)
            document.getElementById("id_maindeck_cards").value = deck.mainboard_to_json()
            document.getElementById("id_sideboard_cards").value = deck.sideboard_to_json()

            # FIXME
            # document.getElementById("id_deck_list").value = mtgo_decklist_export
            if deck.name:
                document.getElementById("id_deck_name").value = deck.name

            # Configure Download buttons
            document.getElementById("export_mtggoldfish").addEventListener("click",
                                                                           create_proxy(
                                                                               mtg_goldfish_func))

            document.getElementById("download").style.display = "inline"

        if deck_name_badge:
            msg += deck_name_badge
        if error_list:
            msg += error_list
        if warning_list:
            msg += warning_list
        if success_badge:
            msg += success_badge
        if unknown_cards_list:
            msg += unknown_cards_list

        document.getElementById("messages").innerHTML = msg
        document.getElementById("col-messages").style.display = "inline"

    else:
        document.getElementById("card_list_parsed").innerHTML = ""
        document.getElementById("col-messages").style.display = "none"
        document.getElementById("card_list_parsed").style.display = "none"
        document.getElementById("instructions").style.display = "block"
        document.getElementById("table-wrapper").style.columnCount = 1;
        document.getElementById("download").style.display = "none"


NATIVE_FS = None


async def save_list_to_file(decklist: str, deck_name: str, format_name: str) -> None:
    global NATIVE_FS
    if NATIVE_FS is None:
        modeObject = to_js({"mode": "readwrite"}, dict_converter=Object.fromEntries)
        dir_handler = await showDirectoryPicker()
        if await dir_handler.queryPermission(modeObject) != "granted":
            if await dir_handler.requestPermission(modeObject) != "granted":
                raise Exception("Unable to read and write directory")
        try:
            NATIVE_FS = await pyodide_js.mountNativeFS("/deck_export", dir_handler)
        except pyodide.ffi.JsException:
            NATIVE_FS = None
            console.log("Exception in setting up folder")

    if NATIVE_FS is not None:
        deck_name = deck_name.lower().replace(" ", "_")
        fname = f"{format_name}_{deck_name}.txt"
        console.log("Saving File: ", fname)
        with open("/deck_export/" + fname, "w") as mtg_export_file:
            mtg_export_file.write(decklist)
        await NATIVE_FS.syncfs()


async def export_mtg_goldfish(event, deck: Deck, cards_db: ScryfallDB):
    deck_exporter = DECK_EXPORTERS[MTG_GOLDFISH](db=cards_db)
    decklist = deck_exporter.export(deck)
    await save_list_to_file(decklist, deck_name=deck.name, format_name="mtgo_goldfish")


async def parse_deck_grouping_key(key: str):
    if key not in FILTER_BUTTONS.keys():
        key = NO_GROUP_ID

    for bid, button in FILTER_BUTTONS.items():
        if bid == key:
            continue
        button.classList.remove("active")

    await parse_deck_list(grouping=GROUPING[key])


@create_proxy
async def parse_deck_no_group(*args, **kwargs):
    await parse_deck_grouping_key(key=NO_GROUP_ID)


@create_proxy
async def parse_deck_group_colour(*args, **kwargs):
    await parse_deck_grouping_key(key=COLOUR_ID)


@create_proxy
async def parse_deck_group_rarity(*args, **kwargs):
    await parse_deck_grouping_key(key=RARITY_ID)


@create_proxy
async def parse_deck_group_cmc(*args, **kwargs):
    await parse_deck_grouping_key(key=CMC_ID)


@create_proxy
async def parse_deck_group_type(*args, **kwargs):
    await parse_deck_grouping_key(key=SPELL_ID)


@create_proxy
async def parse_deck_group_type_extended(*args, **kwargs):
    await parse_deck_grouping_key(key=TYPE_ID)


@create_proxy
async def parse_deck_select_group(*args, **kwargs):
    for key, button in FILTER_BUTTONS.items():
        if button.classList.contains("active"):
            await parse_deck_grouping_key(key=key)
            break


init_cards_db = create_proxy(init_db)

document.getElementById("card_list_entry").addEventListener("focus", init_cards_db)
document.getElementById("card_list_entry").addEventListener("keypress", parse_deck_select_group)
document.getElementById("card_list_entry").addEventListener("change", parse_deck_select_group)
document.getElementById("optimise_cardlist").addEventListener("change", parse_deck_select_group)

# Deck Organiser Buttons
document.getElementById("nogroup").addEventListener("click", parse_deck_no_group)
document.getElementById("color").addEventListener("click", parse_deck_group_colour)
document.getElementById("rarity").addEventListener("click", parse_deck_group_rarity)
document.getElementById("cmc").addEventListener("click", parse_deck_group_cmc)
document.getElementById("spell").addEventListener("click", parse_deck_group_type)
document.getElementById("card_type").addEventListener("click",
                                                      parse_deck_group_type_extended)
init_cards_db()
