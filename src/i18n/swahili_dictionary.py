"""Swahili language dictionary for product names, quantities, and units."""

from typing import Optional, Tuple

# Swahili to English product name mappings
SWAHILI_TO_ENGLISH = {
    # Staples / Vyakula vya msingi
    "mchele": "rice",
    "wali": "rice",
    "mchele wa basmati": "basmati rice",
    "sukari": "sugar",
    "sukari nyeupe": "white sugar",
    "sukari ya kahawia": "brown sugar",
    "unga": "flour",
    "unga wa ngano": "wheat flour",
    "unga wa mahindi": "maize flour",
    "posho": "maize flour",
    "sembe": "maize flour",
    "ugali": "maize flour",
    "mkate": "bread",
    "chapati": "chapati",
    "mandazi": "mandazi",

    # Oils / Mafuta
    "mafuta": "oil",
    "mafuta ya kupika": "cooking oil",
    "mafuta ya alizeti": "sunflower oil",
    "mafuta ya nazi": "coconut oil",
    "mafuta ya mzeituni": "olive oil",
    "siagi": "butter",
    "margarine": "margarine",

    # Dairy / Maziwa
    "maziwa": "milk",
    "maziwa fresh": "fresh milk",
    "maziwa ya muda mrefu": "long life milk",
    "mtindi": "yogurt",
    "jibini": "cheese",
    "cream": "cream",

    # Eggs / Mayai
    "mayai": "eggs",
    "yai": "egg",
    "treyi ya mayai": "egg tray",

    # Proteins / Protini
    "nyama": "meat",
    "nyama ya ng'ombe": "beef",
    "nyama ya mbuzi": "goat meat",
    "nyama ya kondoo": "mutton",
    "nyama ya nguruwe": "pork",
    "kuku": "chicken",
    "kuku mzima": "whole chicken",
    "bata": "duck",
    "samaki": "fish",
    "tilapia": "tilapia",
    "dagaa": "sardines",
    "soseji": "sausages",
    "bacon": "bacon",

    # Vegetables / Mboga
    "mboga": "vegetables",
    "nyanya": "tomatoes",
    "vitunguu": "onions",
    "vitunguu maji": "spring onions",
    "vitunguu saumu": "garlic",
    "viazi": "potatoes",
    "viazi vitamu": "sweet potatoes",
    "karoti": "carrots",
    "kabeji": "cabbage",
    "spinachi": "spinach",
    "sukumawiki": "kale",
    "pilipili": "peppers",
    "pilipili hoho": "bell peppers",
    "tikiti maji": "watermelon",
    "nanasi": "pineapple",
    "parachichi": "avocado",
    "ndizi": "bananas",
    "machungwa": "oranges",
    "maembe": "mangoes",
    "papai": "papaya",
    "limau": "lemon",
    "ndimu": "lime",

    # Beverages / Vinywaji
    "maji": "water",
    "maji ya kunywa": "drinking water",
    "chai": "tea",
    "kahawa": "coffee",
    "juisi": "juice",
    "soda": "soda",
    "bia": "beer",
    "mvinyo": "wine",

    # Dry goods / Vyakula vikavu
    "maharage": "beans",
    "dengu": "lentils",
    "mbaazi": "pigeon peas",
    "kunde": "cowpeas",
    "choroko": "green grams",
    "njugu": "peanuts",
    "korosho": "cashew nuts",

    # Cleaning / Usafi
    "sabuni": "soap",
    "sabuni ya kuosha": "washing soap",
    "sabuni ya kuoga": "bathing soap",
    "sabuni ya maji": "liquid soap",
    "dettol": "disinfectant",
    "jik": "bleach",
    "omo": "detergent",
    "powder ya kuosha": "washing powder",
    "karatasi ya choo": "toilet paper",
    "tissue": "tissue",
    "mswaki": "toothbrush",
    "dawa ya meno": "toothpaste",

    # Condiments / Viungo
    "chumvi": "salt",
    "pilipili kali": "chili",
    "bizari": "spices",
    "mchuzi": "sauce",
    "tomato paste": "tomato paste",
    "soya": "soy sauce",
    "asali": "honey",
    "jam": "jam",

    # Other common items
    "mfuko": "bag",
    "kisanduku": "box",
    "chupa": "bottle",
    "tray": "tray",
    "debe": "tin/container",
    "karatasi": "paper",
}

# English to Swahili (reverse mapping)
ENGLISH_TO_SWAHILI = {v: k for k, v in SWAHILI_TO_ENGLISH.items()}

# Swahili number words
SWAHILI_QUANTITIES = {
    "moja": 1,
    "mbili": 2,
    "tatu": 3,
    "nne": 4,
    "tano": 5,
    "sita": 6,
    "saba": 7,
    "nane": 8,
    "tisa": 9,
    "kumi": 10,
    "kumi na moja": 11,
    "kumi na mbili": 12,
    "kumi na tano": 15,
    "ishirini": 20,
    "ishirini na tano": 25,
    "thelathini": 30,
    "arobaini": 40,
    "hamsini": 50,
    "sitini": 60,
    "sabini": 70,
    "themanini": 80,
    "tisini": 90,
    "mia": 100,
    "mia mbili": 200,
    "mia tano": 500,
    "elfu": 1000,
    # Common quantity phrases
    "nusu": 0.5,
    "robo": 0.25,
    "dazeni": 12,
    "dozen": 12,
}

# Swahili unit words
SWAHILI_UNITS = {
    "kilo": "kg",
    "kilogramu": "kg",
    "gramu": "g",
    "lita": "L",
    "mililita": "ml",
    "kipande": "pieces",
    "vipande": "pieces",
    "treyi": "tray",
    "mfuko": "bag",
    "mifuko": "bags",
    "chupa": "bottle",
    "chupa": "bottles",
    "kisanduku": "box",
    "visanduku": "boxes",
    "pakiti": "packet",
    "paketi": "packet",
    "kartoni": "carton",
    "krete": "crate",
    "debe": "tin",
    "roli": "roll",
    "dazeni": "dozen",
}


def translate_product_name(name: str, to_english: bool = True) -> Tuple[str, bool]:
    """
    Translate a product name between English and Swahili.

    Args:
        name: Product name to translate
        to_english: If True, translate Swahili to English; else English to Swahili

    Returns:
        Tuple of (translated_name, was_translated)
    """
    name_lower = name.lower().strip()

    if to_english:
        # Try direct lookup
        if name_lower in SWAHILI_TO_ENGLISH:
            return SWAHILI_TO_ENGLISH[name_lower], True

        # Try partial matches
        for sw, en in SWAHILI_TO_ENGLISH.items():
            if sw in name_lower or name_lower in sw:
                return en, True

        return name, False
    else:
        # English to Swahili
        if name_lower in ENGLISH_TO_SWAHILI:
            return ENGLISH_TO_SWAHILI[name_lower], True

        for en, sw in ENGLISH_TO_SWAHILI.items():
            if en in name_lower or name_lower in en:
                return sw, True

        return name, False


def parse_swahili_quantity(text: str) -> Optional[float]:
    """
    Parse a Swahili quantity expression.

    Args:
        text: Text containing Swahili number words

    Returns:
        Numeric quantity or None if not recognized
    """
    text_lower = text.lower().strip()

    # Direct lookup
    if text_lower in SWAHILI_QUANTITIES:
        return SWAHILI_QUANTITIES[text_lower]

    # Try to find quantity words in text
    for sw, num in sorted(SWAHILI_QUANTITIES.items(), key=lambda x: -len(x[0])):
        if sw in text_lower:
            return num

    return None


def get_swahili_unit(unit: str) -> str:
    """
    Get the standardized unit from a Swahili unit word.

    Args:
        unit: Swahili unit word

    Returns:
        Standardized English unit abbreviation
    """
    unit_lower = unit.lower().strip()
    return SWAHILI_UNITS.get(unit_lower, unit)
