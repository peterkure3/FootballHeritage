"""Stable requested bookmaker columns, independent of fixture pagination."""
import json

from config import BASE_DIR

INVENTORY = BASE_DIR.parent / '_config' / 'bookmakers.json'


def bookmaker_catalog():
    inventory = json.loads(INVENTORY.read_text(encoding='utf-8'))
    books = []
    for entry in inventory['sportsbooks']:
        region = entry.get('region')
        name = entry.get('current_name') or entry['requested_name']
        key = entry['bookmaker'] + (':' + region if region else '')
        books.append({'bookmaker': key, 'name': name + (' · ' + region if region else ''),
                      'source_url': entry.get('source_url'),
                      'collector_status': entry.get('collector_status', 'not_verified')})
    return sorted(books, key=lambda book: book['name'].casefold())
