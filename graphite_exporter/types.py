from typing import List, Tuple, Union

from typing_extensions import TypedDict


class GraphiteResponseItemTagTypedDict(TypedDict):
    name: str


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


class MetricTypedDict(TypedDict):
    doc: str
    name: str
    metric: str
    value: Union[int, float]


GlobalConfigTypedDict = TypedDict(
    "GlobalConfigTypedDict",
    {
        "prefix": str,
        "interval": str,
        "from": str,
        "until": str,
        "timeout": int,
    },
)

MetricConfigTypedDict = TypedDict(
    "MetricConfigTypedDict",
    {
        "prefix": str,
        "interval": str,
        "from": str,
        "until": str,
        "timeout": int,
        "metric": str,
        "doc": str,
        "name": str,
        "labels": dict,
    },
)

ConfigTypedDict = TypedDict(
    "ConfigTypedDict", {"global": GlobalConfigTypedDict, "metrics": List[MetricConfigTypedDict]}
)
