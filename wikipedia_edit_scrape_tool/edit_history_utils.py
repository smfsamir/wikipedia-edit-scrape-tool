"""Utility functions for manipulating the edit history object
(for a given person)
"""
from typing import Any, Dict, List, Tuple
from .scrape_edit_history import WikipageSnapshot

def get_last_snapshot(edit_history_obj: Dict[str, Any], 
                      lang_wiki: str) -> WikipageSnapshot:
    """_summary_

    Args:
        edit_history_obj (_type_): Get the current page content from the edit history object.
    """
    final_snapshot = edit_history_obj['edit_history_snapshots_all_languages'][lang_wiki][-1]
    return final_snapshot

def get_categories(snapshot: WikipageSnapshot) -> List[str]:
    # -1 since the 0 index is the link to the snapshot
    return snapshot.content[-1]['categories'] # NOTE will return an empty list unless you it's an English snapshot