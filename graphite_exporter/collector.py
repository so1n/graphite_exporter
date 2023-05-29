import logging
import random
from copy import deepcopy
from functools import partial
from typing import Any, Dict, Generator, List, Optional, Set, Tuple

import requests  # type: ignore
from prometheus_client.core import GaugeMetricFamily
from requests.adapters import HTTPAdapter  # type: ignore

from .types import ConfigTypedDict, GlobalConfigTypedDict, GraphiteResponseType, MetricConfigTypedDict, MetricTypedDict
from .utils import graphite_config_dict, label_handle


class Graphite(object):
    def __init__(
        self,
        *,
        ip_list: List[str],
        port: int,
        pool_connections: int,
        pool_maxsize: int,
        max_retries: int,
        pool_block: bool,
        timeout: int,
    ) -> None:
        self._ip_list: List[str] = ip_list
        self._port: int = port
        self._url_dict: Dict[str, str] = {}
        self.custom_metric_dict: dict = {}
        http_adapter: HTTPAdapter = HTTPAdapter(
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
            max_retries=max_retries,
            pool_block=pool_block,
        )
        self.session: requests.Session = requests.session()
        self.session.mount("http://", http_adapter)
        self.session.mount("https://", http_adapter)
        setattr(self.session, "request", partial(self.session.request, timeout=timeout))

    def gen_host(self) -> str:
        return f"http://{random.choice(self._ip_list)}:{self._port}"

    def request(self, metric_url_path: str, timeout: Optional[int] = None) -> GraphiteResponseType:
        resp: requests.Response = self.session.get(self.gen_host() + metric_url_path, timeout=timeout)
        if not resp.ok:
            logging.error(f"can't access graphite:{metric_url_path}, status:{resp.status_code} content:{resp.text}")
            raise StopIteration()
        resp_result_1 = resp.json()
        for i in range(len(resp_result_1)):
            is_none = True
            for j in range(len(resp_result_1[i]['datapoints'])):
                if resp_result_1[i]['datapoints'][j][0] != None:
                    is_none = False
            if is_none:
                resp_result_1[i]['datapoints'][-1][0] = -1 # If value if Null set it to '-1'
        resp_result: GraphiteResponseType = resp_result_1
        return resp_result


class GraphiteMetricCollector(object):
    """Collect graphite system metrics"""

    def __init__(self, graphite: Graphite, allowed_metric_set: Set[str]):
        self.prefix: str = graphite_config_dict["global"].get("prefix", "graphite")
        self.graphite: Graphite = graphite

        global_config: Dict[str, Any] = graphite_config_dict["global"]
        base_url: str = f"/render?format=json&from={global_config['from']}&until={global_config['until']}"
        for name, metric_dict in graphite_config_dict["metrics"].items():
            if name not in allowed_metric_set:
                continue
            base_url += f'&target={metric_dict["metric"]}'
        self.graphite_metric_url_path = base_url

    def get_graphite_metric(self) -> Generator[MetricTypedDict, Any, Any]:
        for target_dict in self.graphite.request(self.graphite_metric_url_path):
            target: str = target_dict["target"]
            metric_dict: MetricTypedDict = deepcopy(graphite_config_dict["metrics"][target])
            metric_dict["value"] = target_dict["datapoints"][-1][0]  # Only the last one is needed
            metric_dict["name"] = target
            yield metric_dict

    def collect(self) -> GaugeMetricFamily:
        for metric_dict in self.get_graphite_metric():
            yield GaugeMetricFamily(
                self.prefix + "_" + metric_dict["name"],
                metric_dict["doc"],
                value=metric_dict["value"],
            )


class CustomMetricCollector(object):
    def __init__(self, config: ConfigTypedDict, graphite: Graphite) -> None:
        self.prefix: str = config["global"].get("prefix", "graphite")
        self.graphite: Graphite = graphite
        self.custom_metric_dict: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def gen_job(self, config: ConfigTypedDict) -> Generator[Tuple, Any, Any]:
        base_url_path: str = "/render?format=json"
        global_config: GlobalConfigTypedDict = config["global"]
        for metric_config_dict in config["metrics"]:
            _interval: str = metric_config_dict.get("interval", config["global"]["interval"])
            try:
                interval: int = int(_interval)
            except Exception:
                interval = int(_interval[:-1])
                unit = _interval[-1]
                if unit == "s":
                    pass
                elif unit == "m":
                    interval = interval * 60
                elif unit == "h":
                    interval = interval * 60 * 60
            metric: str = metric_config_dict["metric"]
            _from: str = metric_config_dict.get("from", global_config["from"])
            until: str = metric_config_dict.get("until", global_config["until"])
            url_path: str = base_url_path + f"&from={_from}&until={until}&target={metric}"

            name: str = metric_config_dict["name"]
            if "timeout" not in metric_config_dict:
                metric_config_dict["timeout"] = global_config.get("timeout", None)
            logging.info(f"gen custom metric. name:{name} url:{url_path}")
            yield (
                partial(self.get_metric, metric_config_dict, url_path),
                interval,
                metric_config_dict["name"],
            )

    def get_metric(self, metric_config_dict: MetricConfigTypedDict, url_path: str) -> None:
        name: str = metric_config_dict["name"]
        self.custom_metric_dict[name] = {}

        for target_dict in self.graphite.request(url_path):
            target: str = target_dict["target"]
            value: Optional[float] = None
            for value, timestamp in reversed(target_dict["datapoints"]):
                if value:
                    break

            key_list: List[str] = []
            value_list: List[int] = []
            for label_key, label_value in label_handle(name, target, metric_config_dict["labels"]).items():
                key_list.append(label_key)
                value_list.append(label_value)
            self.custom_metric_dict[name][target] = {
                "value": value,
                "label_key_list": key_list,
                "label_value_list": value_list,
                "doc": metric_config_dict["doc"],
            }

    def collect(self) -> GaugeMetricFamily:
        query_metrics = deepcopy(self.custom_metric_dict)
        for name, metric_dict in query_metrics.items():
            g: Optional[GaugeMetricFamily] = None
            for target, target_dict in metric_dict.items():
                if not g:
                    g = GaugeMetricFamily(
                        self.prefix + "_" + name.replace("-", "_"),
                        target_dict["doc"],
                        labels=target_dict["label_key_list"],
                    )
                g.add_metric(target_dict["label_value_list"], target_dict["value"])
            if g:
                yield g
