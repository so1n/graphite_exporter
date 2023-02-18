import argparse
import logging
import os
from logging.handlers import SysLogHandler
from typing import Any, Dict, List

import yaml  # type: ignore
from apscheduler.schedulers.background import BackgroundScheduler
from prometheus_client.core import REGISTRY
from prometheus_client.exposition import start_http_server
from requests.adapters import DEFAULT_POOL_TIMEOUT, DEFAULT_POOLBLOCK, DEFAULT_POOLSIZE  # type: ignore

from .collector import CustomMetricCollector, Graphite, GraphiteMetricCollector
from .utils import graphite_config_dict, shutdown


@shutdown()
def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser()
    parser.add_argument(
        "-i",
        "--ip",
        default="127.0.0.1",
        help="graphite web ip. eg: 127.0.0.1 or 127.0.0.1,127.0.0.2",
    )
    parser.add_argument("-c", "--config", default="", help="Metric config path")
    parser.add_argument("-p", "--port", default=5000, help="graphite web port")
    parser.add_argument("-P", "--listen_port", default=9108, help="graphite exporter listen port")
    parser.add_argument("-l", "--log_level", default="INFO", help="log level")
    parser.add_argument(
        "-L",
        "--apscheduler_log_level",
        default="WARNING",
        help="apscheduler log level, default warning",
    )
    parser.add_argument(
        "-s",
        "--system_metric",
        default=",".join(graphite_config_dict["metrics"].keys()),
        help=(
            f"Select the system metric to use. System Metric: {','.join(graphite_config_dict['metrics'].keys())}."
            "The default is Select All"
        ),
    )
    parser.add_argument(
        "--syslog_address",
        help="syslog address, enable syslog handle when value is not empty, "
        "If you want to send to the local, the value is '/dev/log'",
    )
    parser.add_argument(
        "--syslog_facility",
        help="syslog facility, can only be used when syslog is enabled",
        choices=SysLogHandler.facility_names.keys(),
    )
    parser.add_argument(
        "--request_pool_connections",
        default=DEFAULT_POOLSIZE,
        help=f"init connections for the requests pool, default is {DEFAULT_POOLSIZE}",
    )
    parser.add_argument(
        "--request_pool_maxsize",
        default=DEFAULT_POOLSIZE,
        help=f"max size for the requests pool, default is {DEFAULT_POOLSIZE}",
    )
    parser.add_argument(
        "--request_max_retries",
        default=3,
        help="max retries for the request, default is 3",
    )
    parser.add_argument(
        "--request_pool_block",
        default=DEFAULT_POOLBLOCK,
        help=f"whether to block the request when pool is full, default is {DEFAULT_POOLBLOCK}",
    )
    parser.add_argument(
        "--request_timeout",
        default=9,
        help="timeout of request in seconds, default is 9",
    )

    args, unknown = parser.parse_known_args()
    ip_list: List[str] = args.ip.split(",")
    port: int = int(args.port)
    listen_port: int = int(args.listen_port)
    config_filename_path: str = args.config
    log_level: str = args.log_level
    apscheduler_log_level: str = args.apscheduler_log_level
    system_metric: List[str] = args.system_metric.split(",")
    syslog_address: str = args.syslog_address
    request_pool_connections: int = int(args.request_pool_connections)
    request_pool_maxsize: int = int(args.request_pool_maxsize)
    request_pool_block: bool = bool(args.request_pool_block)
    request_timeout: int = int(args.request_timeout)
    request_max_retries: int = int(args.request_max_retries)

    basic_config: Dict[str, Any] = dict(
        format="[%(asctime)s %(levelname)s %(process)d] %(message)s",
        datefmt="%y-%m-%d %H:%M:%S",
        level=getattr(logging, log_level.upper(), "INFO"),
    )

    if syslog_address:
        syslog_facility: int = SysLogHandler.facility_names.get(args.syslog_facility, SysLogHandler.LOG_USER)
        basic_config.update(
            dict(
                handlers=[SysLogHandler(address=syslog_address, facility=syslog_facility)],
                format="%(levelname)s elasticsearch_exporter %(message)s",
            )
        )
        del basic_config["datefmt"]
    logging.basicConfig(**basic_config)

    graphite: Graphite = Graphite(
        ip_list=ip_list,
        port=port,
        pool_block=request_pool_block,
        pool_maxsize=request_pool_maxsize,
        pool_connections=request_pool_connections,
        timeout=request_timeout,
        max_retries=request_max_retries,
    )

    if system_metric:
        logging.info(f"init system metric:{system_metric}")
        REGISTRY.register(GraphiteMetricCollector(graphite, set(system_metric)))
        logging.info(f"registry system metric:{system_metric} success")

    if config_filename_path:
        # Don't need to think about Windows
        if not config_filename_path.startswith("/"):
            config_filename_path = "./" + config_filename_path
        if os.path.exists(config_filename_path):
            logging.info(f"reading custom metric from {config_filename_path}")
            with open(config_filename_path, "r") as config_file:
                custom_metric_config: dict = yaml.load(config_file, Loader=yaml.FullLoader)
            graphite.init_custom_metric(custom_metric_config)
            REGISTRY.register(CustomMetricCollector(custom_metric_config, graphite))

            scheduler: BackgroundScheduler = BackgroundScheduler()
            for job, interval, name in graphite.gen_job(custom_metric_config):
                scheduler.add_job(job, "interval", seconds=interval, name=name)
            logging.getLogger("apscheduler.executors.default").setLevel(getattr(logging, apscheduler_log_level))
            scheduler.start()
        else:
            logging.error(f"reading custom metric from {config_filename_path}")

    logging.info("Starting server...")
    start_http_server(listen_port)
    logging.info(f"Server started on port {listen_port}")
