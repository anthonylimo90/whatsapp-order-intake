"""Enhanced product matching service with aliases, Levenshtein, and caching."""

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Optional, List, Tuple, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

# Import Swahili dictionary for multi-language support
try:
    from ..i18n.swahili_dictionary import SWAHILI_TO_ENGLISH
except ImportError:
    SWAHILI_TO_ENGLISH = {}


@dataclass
class MatchResult:
    """Result of a product match."""
    matched_name: str
    canonical_name: str
    confidence: float
    match_type: str  # 'exact', 'alias', 'fuzzy', 'levenshtein', 'cached'


# Common product aliases - English variations
PRODUCT_ALIASES: Dict[str, List[str]] = {
    # Rice
    "rice": ["basmati rice", "white rice", "brown rice", "pishori rice", "mchele"],
    "rice basmati": ["basmati", "basmati rice", "premium rice"],

    # Sugar
    "sugar": ["white sugar", "granulated sugar", "sukari"],
    "sugar brown": ["brown sugar", "demerara sugar", "raw sugar"],

    # Oils
    "cooking oil": ["oil", "vegetable oil", "frying oil", "mafuta ya kupika", "mafuta"],
    "sunflower oil": ["sunflower", "sun oil"],
    "olive oil": ["olive", "extra virgin olive oil"],

    # Dairy
    "milk": ["fresh milk", "whole milk", "maziwa"],
    "milk uht": ["uht milk", "long life milk", "processed milk"],
    "butter": ["cooking butter", "baking butter", "siagi"],
    "cheese": ["cheddar", "cheddar cheese", "yellow cheese"],

    # Eggs
    "eggs": ["chicken eggs", "mayai", "egg tray", "tray eggs"],

    # Flour
    "flour": ["wheat flour", "all purpose flour", "baking flour", "unga"],
    "maize flour": ["maize meal", "ugali flour", "unga wa mahindi", "posho"],

    # Bread
    "bread": ["white bread", "sliced bread", "mkate"],
    "bread brown": ["brown bread", "wholemeal bread", "wheat bread"],

    # Beverages
    "water": ["drinking water", "mineral water", "bottled water", "maji"],
    "juice": ["fruit juice", "orange juice", "mango juice"],
    "soda": ["soft drinks", "carbonated drinks", "sodas"],
    "tea": ["tea leaves", "chai"],
    "coffee": ["instant coffee", "ground coffee", "kahawa"],

    # Proteins
    "chicken": ["whole chicken", "frozen chicken", "kuku"],
    "beef": ["fresh beef", "beef meat", "nyama ya ng'ombe"],
    "fish": ["tilapia", "fresh fish", "samaki"],

    # Vegetables
    "tomatoes": ["fresh tomatoes", "nyanya"],
    "onions": ["red onions", "white onions", "vitunguu"],
    "potatoes": ["irish potatoes", "viazi"],
    "cabbage": ["green cabbage", "kabeji"],
    "carrots": ["fresh carrots", "karoti"],

    # Cleaning
    "soap": ["bar soap", "bathing soap", "sabuni"],
    "detergent": ["washing powder", "laundry detergent", "omo", "ariel"],
    "bleach": ["jik", "household bleach"],

    # Toiletries
    "tissue": ["toilet paper", "tissue paper", "toilet tissue", "toilet roll"],
    "toothpaste": ["dental cream", "colgate"],
}

# Build reverse lookup: alias -> canonical name
ALIAS_TO_CANONICAL: Dict[str, str] = {}
for canonical, aliases in PRODUCT_ALIASES.items():
    for alias in aliases:
        ALIAS_TO_CANONICAL[alias.lower()] = canonical
    # Also add the canonical name itself
    ALIAS_TO_CANONICAL[canonical.lower()] = canonical

# Add Swahili aliases from the i18n dictionary
for swahili, english in SWAHILI_TO_ENGLISH.items():
    ALIAS_TO_CANONICAL[swahili.lower()] = english.lower()


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein (edit) distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def levenshtein_similarity(s1: str, s2: str) -> float:
    """Calculate similarity score based on Levenshtein distance (0-1)."""
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    distance = levenshtein_distance(s1, s2)
    return 1 - (distance / max_len)


class ProductMatchingService:
    """Enhanced product matching with multiple strategies."""

    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session
        self._cache: Dict[str, MatchResult] = {}

    def normalize(self, name: str) -> str:
        """Normalize product name for matching."""
        if not name:
            return ""

        # Lowercase and strip
        normalized = name.lower().strip()

        # Remove common units that might be in name
        units_to_remove = [
            'kg', 'kgs', 'g', 'grams', 'l', 'ltr', 'litre', 'liters', 'litres',
            'ml', 'pieces', 'pcs', 'pc', 'trays', 'tray', 'crates', 'crate',
            'bags', 'bag', 'bottles', 'bottle', 'packets', 'packet', 'pkt',
            'cartons', 'carton', 'boxes', 'box', 'rolls', 'roll', 'dozen', 'doz'
        ]
        for unit in units_to_remove:
            normalized = normalized.replace(f' {unit}', '')
            normalized = normalized.replace(f'{unit} ', '')

        # Remove numbers at the end
        words = normalized.split()
        words = [w for w in words if not w.isdigit()]
        normalized = ' '.join(words)

        return normalized.strip()

    def find_alias(self, name: str) -> Optional[str]:
        """Look up canonical name from alias dictionary."""
        normalized = self.normalize(name)
        return ALIAS_TO_CANONICAL.get(normalized)

    async def find_db_alias(self, name: str) -> Optional[str]:
        """Look up alias from database (if available)."""
        if not self.session:
            return None

        try:
            from ..db.models import ProductAlias

            normalized = self.normalize(name)
            query = select(ProductAlias).where(
                func.lower(ProductAlias.alias) == normalized
            )
            result = await self.session.execute(query)
            alias_record = result.scalar_one_or_none()

            if alias_record:
                return alias_record.canonical_name
        except Exception:
            # Table may not exist yet
            pass

        return None

    async def get_cached_match(self, name: str) -> Optional[MatchResult]:
        """Get cached match from memory or database."""
        normalized = self.normalize(name)

        # Check memory cache first
        if normalized in self._cache:
            return self._cache[normalized]

        # Check database cache
        if self.session:
            try:
                from ..db.models import ProductMappingCache

                query = select(ProductMappingCache).where(
                    ProductMappingCache.input_text == normalized
                )
                result = await self.session.execute(query)
                cache_record = result.scalar_one_or_none()

                if cache_record:
                    match_result = MatchResult(
                        matched_name=normalized,
                        canonical_name=cache_record.matched_product_name,
                        confidence=cache_record.confidence,
                        match_type='cached'
                    )
                    self._cache[normalized] = match_result

                    # Update hit count
                    cache_record.hit_count += 1

                    return match_result
            except Exception:
                pass

        return None

    async def cache_match(self, input_name: str, result: MatchResult):
        """Cache a successful match for future lookups."""
        normalized = self.normalize(input_name)
        self._cache[normalized] = result

        if self.session:
            try:
                from ..db.models import ProductMappingCache

                # Upsert cache record
                cache_record = ProductMappingCache(
                    input_text=normalized,
                    matched_product_name=result.canonical_name,
                    confidence=result.confidence,
                    hit_count=1
                )
                self.session.add(cache_record)
                await self.session.flush()
            except Exception:
                pass  # Table may not exist

    def fuzzy_match(self, name: str, candidates: List[str]) -> Optional[Tuple[str, float]]:
        """Find best match using multiple fuzzy strategies."""
        normalized = self.normalize(name)

        if not normalized or not candidates:
            return None

        best_match = None
        best_score = 0.0

        for candidate in candidates:
            candidate_normalized = self.normalize(candidate)

            # Strategy 1: SequenceMatcher (difflib)
            seq_score = SequenceMatcher(None, normalized, candidate_normalized).ratio()

            # Strategy 2: Levenshtein similarity
            lev_score = levenshtein_similarity(normalized, candidate_normalized)

            # Strategy 3: Word overlap (Jaccard)
            input_words = set(normalized.split())
            candidate_words = set(candidate_normalized.split())
            if input_words and candidate_words:
                intersection = len(input_words & candidate_words)
                union = len(input_words | candidate_words)
                jaccard_score = intersection / union if union > 0 else 0
            else:
                jaccard_score = 0

            # Combine scores (weighted average)
            combined_score = (seq_score * 0.4) + (lev_score * 0.3) + (jaccard_score * 0.3)

            if combined_score > best_score:
                best_score = combined_score
                best_match = candidate

        if best_match and best_score >= 0.5:
            return best_match, best_score

        return None

    async def match(
        self,
        name: str,
        candidates: Optional[List[str]] = None,
        use_cache: bool = True,
        min_confidence: float = 0.5
    ) -> Optional[MatchResult]:
        """
        Match a product name using multiple strategies:
        1. Exact match
        2. Alias lookup (memory + database)
        3. Cache lookup
        4. Fuzzy matching
        """
        normalized = self.normalize(name)
        if not normalized:
            return None

        # Strategy 1: Check cache first
        if use_cache:
            cached = await self.get_cached_match(name)
            if cached and cached.confidence >= min_confidence:
                return cached

        # Strategy 2: Alias lookup (in-memory)
        alias_match = self.find_alias(name)
        if alias_match:
            result = MatchResult(
                matched_name=normalized,
                canonical_name=alias_match,
                confidence=0.95,
                match_type='alias'
            )
            if use_cache:
                await self.cache_match(name, result)
            return result

        # Strategy 3: Database alias lookup
        db_alias = await self.find_db_alias(name)
        if db_alias:
            result = MatchResult(
                matched_name=normalized,
                canonical_name=db_alias,
                confidence=0.95,
                match_type='alias'
            )
            if use_cache:
                await self.cache_match(name, result)
            return result

        # Strategy 4: Fuzzy match against candidates
        if candidates:
            fuzzy_result = self.fuzzy_match(name, candidates)
            if fuzzy_result:
                matched_name, score = fuzzy_result
                if score >= min_confidence:
                    result = MatchResult(
                        matched_name=normalized,
                        canonical_name=self.normalize(matched_name),
                        confidence=score,
                        match_type='fuzzy'
                    )
                    if use_cache and score >= 0.8:
                        await self.cache_match(name, result)
                    return result

        # Strategy 5: Fuzzy match against known aliases
        all_known_names = list(ALIAS_TO_CANONICAL.keys())
        fuzzy_result = self.fuzzy_match(name, all_known_names)
        if fuzzy_result:
            matched_name, score = fuzzy_result
            if score >= min_confidence:
                canonical = ALIAS_TO_CANONICAL.get(matched_name, matched_name)
                result = MatchResult(
                    matched_name=normalized,
                    canonical_name=canonical,
                    confidence=score,
                    match_type='fuzzy'
                )
                if use_cache and score >= 0.8:
                    await self.cache_match(name, result)
                return result

        # No match found
        return None

    def match_sync(
        self,
        name: str,
        candidates: Optional[List[str]] = None,
        min_confidence: float = 0.5
    ) -> Optional[MatchResult]:
        """
        Synchronous version of match() for use without database.
        Uses only in-memory aliases and fuzzy matching.
        """
        normalized = self.normalize(name)
        if not normalized:
            return None

        # Check memory cache
        if normalized in self._cache:
            cached = self._cache[normalized]
            if cached.confidence >= min_confidence:
                return cached

        # Alias lookup
        alias_match = self.find_alias(name)
        if alias_match:
            result = MatchResult(
                matched_name=normalized,
                canonical_name=alias_match,
                confidence=0.95,
                match_type='alias'
            )
            self._cache[normalized] = result
            return result

        # Fuzzy match against candidates
        if candidates:
            fuzzy_result = self.fuzzy_match(name, candidates)
            if fuzzy_result:
                matched_name, score = fuzzy_result
                if score >= min_confidence:
                    result = MatchResult(
                        matched_name=normalized,
                        canonical_name=self.normalize(matched_name),
                        confidence=score,
                        match_type='fuzzy'
                    )
                    if score >= 0.8:
                        self._cache[normalized] = result
                    return result

        # Fuzzy match against known aliases
        all_known_names = list(ALIAS_TO_CANONICAL.keys())
        fuzzy_result = self.fuzzy_match(name, all_known_names)
        if fuzzy_result:
            matched_name, score = fuzzy_result
            if score >= min_confidence:
                canonical = ALIAS_TO_CANONICAL.get(matched_name, matched_name)
                result = MatchResult(
                    matched_name=normalized,
                    canonical_name=canonical,
                    confidence=score,
                    match_type='fuzzy'
                )
                if score >= 0.8:
                    self._cache[normalized] = result
                return result

        return None
