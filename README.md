# Contributors
Chan Y. Park, Farhan Samir

# Features
## Retrieving edit histories for multiple languages
```
def get_edit_history(en_wiki_id: str, target_languages=TARGET_LANGUAGES) -> Dict[str, Any]:
    """_summary_

    Args:
        en_wiki_id (str): Wikipedia ID.

    Returns:
        Dict[str, Any]: A dictionary containing the edit history metadata and snapshots for each language.
    
    Examples:
    >>> get_edit_history("Tim_Cook", ["enwiki", "frwiki", "eswiki", "ruwiki", "kowiki"]])
    """
```
Currently, only `["enwiki", "frwiki", "eswiki", "ruwiki", "kowiki"]` are supported. But it's not too difficult to add another language. 
