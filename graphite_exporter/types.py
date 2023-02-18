from typing import List, Tuple

from typing_extensions import TypedDict


class GraphiteResponseItemTagTypedDict(TypedDict):
    name: str
    aggregatedBy: str


class GraphiteResponseItemTypedDict(TypedDict):
    target: str
    tags: GraphiteResponseItemTagTypedDict
    datapoints: List[Tuple[float, int]]  # [[ 45.0, 1676738680],]


# [
#     {
#         "target": "carbon_update_operations",
#         "tags": {
#             "name": "carbon.agents.6292684d5aaa-a.updateOperations",
#             "aggregatedBy": "sum"
#         },
#         "datapoints": [
#             [
#                 45.0,
#                 1676738680
#             ],
#         ]
#     },
# ]
GraphiteResponseType = List[GraphiteResponseItemTypedDict]
