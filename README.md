## graphite_exporter
Prometheus Graphite Exporter
## Installation
```Bash
pip install graphite_exporter
```
## Usage
### How to run
can use `python -m` after install graphite_exporter
```bash
>> python3 -m graphite_exporter -h

usage: __main__.py [-h] [-i IP] [-c CONFIG] [-p PORT] [-P LISTEN_PORT]
                   [-l LOG_LEVEL] [-L APSCHEDULER_LOG_LEVEL]
                   [--system_metric SYSTEM_METRIC]

optional arguments:
  -h, --help            show this help message and exit
  -i IP, --ip IP        graphite web ip
  -c CONFIG, --config CONFIG
                        Metric config path
  -p PORT, --port PORT  graphite web port
  -P LISTEN_PORT, --listen_port LISTEN_PORT
                        graphite exporter listen port
  -l LOG_LEVEL, --log_level LOG_LEVEL
                        log level
  -L APSCHEDULER_LOG_LEVEL, --apscheduler_log_level APSCHEDULER_LOG_LEVEL
                        apscheduler log level, default warning
  --system_metric SYSTEM_METRIC
                        Select the system metric to use. System Metric: carbon
                        _update_operations,carbon_metrics_received,carbon_comm
                        itted_points,carbon_points_per_update,carbon_cpu_usage
                        ,carbon_creates
```
### Custom Metric and Config
The `graphite_exporter` can be configured to translate specific dot-separated graphite metrics into labeled Prometheus metrics via YAML configuration file. 

An example configuration:
```yaml
# base param
global:
  prefix: graphite      # prometheus metric prefix
  interval: 1m          # collection data interval
  from: -1min           # graphite web requests param. learn more: https://graphite.readthedocs.io/en/latest/render_api.html#from-until
  until: now            # graphite web requests param. learn more: https://graphite.readthedocs.io/en/latest/render_api.html#from-until
  timeout: 10           # requests timeout

metrics:
  - metric: example.*.*.user    # graphite metric
    name: user_cnt              # prometheus metric name
    doc: user cnt               # prometheus metric doc 
    prefix: gaphite1
    interval: 2m
    from: -10min
    until: now
    timeout: 20
    labels:                     # prometheus metric tag info:
      service: ${0}             #   service: ${0}  -> {service='example'}
      app: ${1}
      project: ${2}

  - metric: example.*.app1.dau
    name: dau
    doc: dau
    # No base parameters are set, 
    # this metric base param will auto set from global base param
    labels:
      service_project: ${0}-${2}  # service_project: ${0}-${2} -> {service_project='example-app1'}    
      app: ${1}
      project: ${2}

  - metric: aliasByMetric(example.*.*.dau)  # graphite return metric name: dau
    name: dau
    doc: dau
    labels:
      metric: dau    # metric only be one value: dau

```