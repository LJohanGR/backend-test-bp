"""
catalog_service.py
------------------
Loads all catalog ``.txt`` files from the configured directory and exposes
lookup helpers used during column profiling.

Catalog file format
~~~~~~~~~~~~~~~~~~~
- First line: catalog name (ignored, used for documentation only)
- Subsequent lines: ``<code><separator><label>``
  - Tab-separated: ``1\tLabel text``
  - Space-separated: ``1 Label text``

Column → catalog matching (``find_catalog_for_column``)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Three-pass strategy, returning on the first hit:

1. **Direct key match** — normalised column name equals a catalog key.
2. **Core substring match** — strip common prefixes (``ID_``, ``CVE_``,
   ``CAT_``, ``REF_``) from both sides iteratively, then check containment.
3. **Word-scoring** — tokenise both by ``_`` / spaces; count shared words
   (length > 3); return the catalog key with the highest score.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, Optional

from app.core.config import settings

# Prefixes stripped during matching to improve recall
_STRIP_PREFIXES = ("CVE_", "CAT_", "ID_", "REF_")


def _strip_common_prefixes(name: str) -> str:
    """Iteratively remove known prefixes until none remain."""
    changed = True
    while changed:
        changed = False
        for prefix in _STRIP_PREFIXES:
            if name.startswith(prefix):
                name = name[len(prefix):]
                changed = True
    return name


class CatalogService:
    def __init__(self) -> None:
        self._catalogs: Dict[str, Dict[str, str]] = {}

    def load(self) -> None:
        """Parse all .txt files in ``settings.CATALOGOS_PATH`` into memory."""
        path = settings.CATALOGOS_PATH
        if not os.path.isdir(path):
            return
        for fname in os.listdir(path):
            if not fname.lower().endswith(".txt"):
                continue
            fpath = os.path.join(path, fname)
            try:
                catalog = self._parse_file(fpath)
                if catalog:
                    key = self._normalize_key(os.path.splitext(fname)[0])
                    self._catalogs[key] = catalog
            except Exception:
                pass

    # ── Parsing ──────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_file(fpath: str) -> Dict[str, str]:
        # Try common encodings; Latin-1 is a safe final fallback (never raises)
        content = ""
        for encoding in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                with open(fpath, encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue

        result: Dict[str, str] = {}
        for line in content.splitlines()[1:]:   # skip first line (catalog name)
            line = line.strip()
            if not line:
                continue
            # Tab-separated first
            parts = line.split("\t")
            if len(parts) >= 2 and parts[0].strip() and parts[1].strip():
                result[parts[0].strip()] = parts[1].strip()
                continue
            # Space-separated fallback
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[0].strip() and parts[1].strip():
                result[parts[0].strip()] = parts[1].strip()
        return result

    @staticmethod
    def _normalize_key(name: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_]", "_", name).upper()

    # ── Public helpers ────────────────────────────────────────────────────────

    def get_all(self) -> Dict[str, Dict[str, str]]:
        return self._catalogs

    def get(self, key: str) -> Optional[Dict[str, str]]:
        return self._catalogs.get(key.upper())

    def decode_value(self, catalog_key: str, code: Any) -> str:
        """Decode a single coded value using the named catalog."""
        catalog = self.get(catalog_key)
        if catalog is None or code is None:
            return str(code)
        raw = str(code).strip()
        try:
            raw = str(int(float(raw)))
        except (ValueError, TypeError):
            pass
        return catalog.get(raw, str(code))

    def find_catalog_for_column(self, column_name: str) -> Optional[str]:
        """
        Best-effort match between a CSV column name and a loaded catalog key.

        Matching is performed in three passes (returns on first hit):

        1. Direct normalised-key match.
        2. Core-substring match after stripping common prefixes from both sides.
        3. Word-scoring: pick the catalog key that shares the most tokens
           (words longer than 3 characters) with the column name.
        """
        normalized_col = self._normalize_key(column_name)

        # Pass 1 – direct
        if normalized_col in self._catalogs:
            return normalized_col

        # Pass 2 – core substring
        col_core = _strip_common_prefixes(normalized_col)
        for key in self._catalogs:
            key_core = _strip_common_prefixes(key)
            if col_core and key_core and (
                col_core == key_core
                or col_core in key_core
                or key_core in col_core
            ):
                return key

        # Pass 3 – word scoring
        col_words = [
            w for w in re.split(r"[_\s]+", normalized_col) if len(w) > 3
        ]
        if not col_words:
            return None

        best_key: Optional[str] = None
        best_score = 0
        for key in self._catalogs:
            score = sum(1 for w in col_words if w in key)
            if score > best_score:
                best_score = score
                best_key = key

        return best_key if best_score > 0 else None


catalog_service = CatalogService()

