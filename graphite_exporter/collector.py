import logging
import random
import re
from functools import partial
from typing import Any, Dict, Generator, List, Optional, Set, Tuple

import requests
from prometheus_client.core import GaugeMetricFamily

from .utils import graphite_config_dict


class Graphite(object):
    def __init__(self, ip_list: List[str], port: int) -> None:
        self._ip_list: List[str] = ip_list
        self._port: int = port
        self._url_dict: Dict[str, str] = {}
        self.custom_metric_dict: dict = {}
        self.session: requests.Session = requests.session()
        self.graphite_metric_url_path: str = ""

    def gen_host(self) -> str:
        return f"http://{random.choice(self._ip_list)}:{self._port}"

    def init_monitor_graphite_metric(self, allowed_metric_set: Set[str]) -> None:
        global_config: Dict[str, Any] = graphite_config_dict["global"]
        base_url: str = f"/render?format=json&from={global_config['from']}&until={global_config['until']}"
        for name, metric_dict in graphite_config_dict["metrics"].items():
            if name not in allowed_metric_set:
                continue
            base_url += f'&target={metric_dict["metric"]}'
        self.graphite_metric_url_path = base_url

    def init_custom_metric(self, config: dict) -> None:
        global_config: dict = config["global"]
        base_url_path: str = f"/render?format=json"
        for metric_dict in config["metrics"]:
            name: str = metric_dict["name"]
            metric: str = metric_dict["metric"]
            _from: str = metric_dict.get("from", global_config["from"])
            until: str = metric_dict.get("until", global_config["until"])
            url_path: str = (
                base_url_path + f"&from={_from}&until={until}&target={metric}"
            )
            logging.info(f"gen custom metric. name:{name} url:{url_path}")
            self._url_dict[name] = url_path
            self.custom_metric_dict[name] = {}

    @staticmethod
    def label_handle(name: str, target: str, metric_label_dict: dict) -> dict:
        label_dict: dict = {}
        target_info_list: List[str] = target.split(".")
        for label_key, label_value in metric_label_dict.items():
            if "${" in label_value:
                label_match: List[str] = re.findall("\${\d*}", label_value)
                if not label_match:
                    logging.error(
                        f"name:{name} key:{label_key} match {label_value} fail"
                    )
                    continue

                for label in label_match:
                    index: int = int(label[2:-1])
                    label_value = label_value.replace(label, target_info_list[index])
                label_dict[label_key] = label_value
            else:
                label_dict[label_key] = label_value
        return label_dict

    def gen_job(self, config: Dict[str, Any]) -> Generator[Tuple, Any, Any]:
        for metric_config_dict in config["metrics"]:
            _interval: str = metric_config_dict.get(
                "interval", config["global"]["interval"]
            )
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
            yield (
                partial(self.get_metric, metric_config_dict),
                interval,
                metric_config_dict["name"],
            )

    def get_graphite_metric(self) -> Generator[dict, Any, Any]:
        i: int = 0
        while True:
            i += 1
            resp: requests.Response = self.session.get(
                self.gen_host() + self.graphite_metric_url_path
            )
            if resp.ok:
                break
            elif resp.ok and i > 3:
                logging.error(
                    f"can't access graphite, status:{resp.status_code} content:{resp.text}"
                )
                raise StopIteration()
        for target_dict in resp.json():
            target: str = target_dict["target"]
            last_datapoint: Tuple[int, int] = target_dict["datapoints"][-1]
            value, timestamp = last_datapoint
            metric_dict: dict = graphite_config_dict["metrics"][target]
            metric_dict["value"] = value
            metric_dict["name"] = target
            yield metric_dict

    def get_metric(self, metric_config_dict: dict) -> None:
        name: str = metric_config_dict["name"]
        url: str = self.gen_host() + self._url_dict[name]
        resp: requests.Response = self.session.get(url)
        if not resp.ok:
            logging.error(f"can't access graphite, status:{resp.status_code}")
            return
        for target_dict in resp.json():
            target: str = target_dict["target"]
            last_datapoint: Tuple[int, int] = target_dict["datapoints"][-1]
            value, timestamp = last_datapoint
            # TODO value为空的处理
            if value is None:
                continue

            self.custom_metric_dict[name] = {}
            key_list: List[str] = []
            value_list: List[int] = []
            for label_key, label_value in self.label_handle(
                name, target, metric_config_dict["labels"]
            ).items():
                key_list.append(label_key)
                value_list.append(label_value)
            self.custom_metric_dict[name][target] = {
                "value": value,
                "label_key_list": key_list,
                "label_value_list": value_list,
                "doc": metric_config_dict["doc"],
            }


class GraphiteMetricCollector(object):
    def __init__(self, graphite: Graphite):
        self.prefix: str = graphite_config_dict["global"].get("prefix", "graphite")
        self.graphite: Graphite = graphite

    def collect(self) -> GaugeMetricFamily:
        for metric_dict in self.graphite.get_graphite_metric():
            g: GaugeMetricFamily = GaugeMetricFamily(
                self.prefix + "_" + metric_dict["name"],
                metric_dict["doc"],
                value=metric_dict["value"],
            )
            yield g


class CustomMetricCollector(object):
    def __init__(self, config: Dict[str, Any], graphite: Graphite) -> None:
        self.prefix: str = config["global"].get("prefix", "graphite")
        self.custom_metric_dict: Dict[str, Any] = graphite.custom_metric_dict

    def collect(self) -> GaugeMetricFamily:
        query_metrics = self.custom_metric_dict.copy()
        for name, metric_dict in query_metrics.items():
            g: Optional[GaugeMetricFamily] = None
            for target, target_dict in metric_dict.items():
                if not g:
                    g = GaugeMetricFamily(
                        self.prefix + "_" + name,
                        target_dict["doc"],
                        labels=target_dict["label_key_list"],
                    )
                g.add_metric(target_dict["label_value_list"], target_dict["value"])
            if g:
                yield g
