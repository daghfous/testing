"""
index_utils.py
"""
import json
from pymongo import IndexModel


def son_to_indexmodels(son_indexes: dict):
    """ Convert SON list into IndexModel list
    """
    index_models: list[IndexModel] = []
    for son_index in son_indexes:
        if son_index["name"] == "_id_":
            # skip the default `_id` index
            continue
        kwargs = {k: v for k, v in son_index.items() if k not in ["v", "key"]}
        index = IndexModel(
            list(son_index["key"].items()),
            **kwargs
        )
        index_models.append(index)
    return index_models


def compare_indexmodels_unordered(list_a: list[IndexModel], list_b: list[IndexModel]):
    """ Compare 2 IndexModel lists.
    """
    def _normalize(im: IndexModel) -> str:
        # Convert `IndexModel` into `JSON` to avoid order issue
        return json.dumps(im.document, sort_keys=True)

    set_a = {_normalize(im) for im in list_a}
    set_b = {_normalize(im) for im in list_b}
    return set_a == set_b
