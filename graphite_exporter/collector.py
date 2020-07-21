import logging
import random
import re
from functools import partial

import requests

from prometheus_client.core import GaugeMetricFamily

from .utils import graphite_config_dict


class Graphite(object):
    def __init__(self, ip, port):
        self._ip = ip
        self._port = port
        self._url_dict = {}
        self.custom_metric_dict = {}
        self.session = requests.session()
        self.graphite_metric_url_path = None

    def gen_host(self):
        return f'http://{random.choice(self._ip)}:{self._port}'

    def init_monitor_graphite_metric(self, allowed_metric_set):
        global_config = graphite_config_dict['global']
        base_url = (
            f"/render?format=json&from={global_config['from']}"
            f"&until={global_config['until']}"
        )
        for name, metric_dict in graphite_config_dict['metrics'].items():
            if name not in allowed_metric_set:
                continue
            base_url += f'&target={metric_dict["metric"]}'
        self.graphite_metric_url_path = base_url

    def init_custom_metric(self, config):
        global_config = config['global']
        base_url_path = f"/render?format=json"
        for metric_dict in config['metrics']:
            name = metric_dict['name']
            metric = metric_dict["metric"]
            _from = metric_dict.get('from', global_config['from'])
            until = metric_dict.get('until', global_config['until'])
            url_path = base_url_path + f'&from={_from}&until={until}&target={metric}'
            logging.info(f'gen custom metric. name:{name} url:{url_path}')
            self._url_dict[name] = url_path
            self.custom_metric_dict[name] = {}

    @staticmethod
    def label_handle(name, target, metric_label_dict):
        label_dict = {}
        target_info_list = target.split('.')
        for label_key, label_value in metric_label_dict.items():
            if '${' in label_value:
                label_match = re.findall('\${\d*}', label_value)
                if not label_match:
                    logging.error(f'name:{name} key:{label_key}'
                                  f' match {label_value} fail')
                    continue

                for label in label_match:
                    index = int(label[2:-1])
                    label_value = label_value.replace(
                        label, target_info_list[index]
                    )
                label_dict[label_key] = label_value
            else:
                label_dict[label_key] = label_value
        return label_dict

    def gen_job(self, config):
        for metric_config_dict in config['metrics']:
            _interval = metric_config_dict.get(
                'interval',
                config['global']['interval']
            )
            try:
                interval = int(_interval)
            except Exception:
                interval = int(_interval[:-1])
                unit = _interval[-1]
                if unit == 's':
                    pass
                elif unit == 'm':
                    interval = interval * 60
                elif unit == 'h':
                    interval = interval * 60 * 60
            yield (
                partial(self.get_metric, metric_config_dict),
                interval,
                metric_config_dict['name']
            )

    def get_graphite_metric(self):
        i = 0
        while True:
            i += 1
            resp = self.session.get(
                self.gen_host() + self.graphite_metric_url_path
            )
            if resp.ok:
                break
            elif resp.ok and i > 3:
                logging.error(
                    f"can't access graphite, status:{resp.status_code}"
                    f" content:{resp.text}"
                )
                return
        for target_dict in resp.json():
            target = target_dict['target']
            last_datapoint = target_dict['datapoints'][-1]
            value, timestamp = last_datapoint
            metric_dict = graphite_config_dict['metrics'][target]
            metric_dict['value'] = value
            metric_dict['name'] = target
            yield metric_dict

    def get_metric(self, metric_config_dict):
        name = metric_config_dict['name']
        url = self.gen_host() + self._url_dict[name]
        resp = self.session.get(url)
        if not resp.ok:
            logging.error(
                f"can't access graphite, status:{resp.status_code}"
            )
            return
        for target_dict in resp.json():
            target = target_dict['target']
            last_datapoint = target_dict['datapoints'][-1]
            value, timestamp = last_datapoint
            # TODO value为空的处理
            if value is None:
                continue
            if target in self.custom_metric_dict[name]:
                self.custom_metric_dict[name][target][value] = value
            else:
                key_list = []
                value_list = []
                for label_key, label_value in self.label_handle(
                        name,
                        target,
                        metric_config_dict['labels']
                ).items():
                    key_list.append(label_key)
                    value_list.append(label_value)
                self.custom_metric_dict[name][target] = {
                    'value': value,
                    'label_key_list': key_list,
                    'label_value_list': value_list,
                    'doc': metric_config_dict['doc']
                }


class GraphiteMetricCollector(object):

    def __init__(self, graphite):
        self.prefix = graphite_config_dict['global'].get('prefix', 'graphite')
        self.graphite = graphite

    def collect(self):
        for metric_dict in self.graphite.get_graphite_metric():
            g = GaugeMetricFamily(
                self.prefix + '_' + metric_dict['name'],
                metric_dict['doc'],
                value=metric_dict['value']
            )
            yield g


class CustomMetricCollector(object):

    def __init__(self, config, graphite):
        self.prefix = config['global'].get('prefix', 'graphite')
        self.custom_metric_dict = graphite.custom_metric_dict

    def collect(self):
        query_metrics = self.custom_metric_dict.copy()
        for name, metric_dict in query_metrics.items():
            g = None
            for target, target_dict in metric_dict.items():
                if not g:
                    g = GaugeMetricFamily(
                        self.prefix + '_' + name,
                        target_dict['doc'],
                        labels=target_dict['label_key_list']
                    )
                g.add_metric(
                    target_dict['label_value_list'],
                    target_dict['value']
                )
            if g:
                yield g
