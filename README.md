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
                   [-s SYSTEM_METRIC] [--syslog_address SYSLOG_ADDRESS]
                   [--syslog_facility {auth,authpriv,cron,daemon,ftp,kern,lpr,mail,news,security,syslog,user,uucp,local0,local1,local2,local3,local4,local5,local6,local7}]
                   [--request_pool_connections REQUEST_POOL_CONNECTIONS]
                   [--request_pool_maxsize REQUEST_POOL_MAXSIZE]
                   [--request_max_retries REQUEST_MAX_RETRIES]
                   [--request_pool_block REQUEST_POOL_BLOCK]
                   [--request_timeout REQUEST_TIMEOUT]

optional arguments:
  -h, --help            show this help message and exit
  -i IP, --ip IP        graphite web ip. eg: 127.0.0.1 or 127.0.0.1,127.0.0.2
                        _!_If -i is set parameter 'ip' in config file will be ignored
  -c CONFIG, --config CONFIG
                        Metric config path
  -p PORT, --port PORT  graphite web port
                        _!_If -p is set parameter 'port' in config file will be ignored
  -P LISTEN_PORT, --listen_port LISTEN_PORT
                        graphite exporter listen port
                        _!_If -P is set parameter 'listen_port' in config file will be ignored
  -l LOG_LEVEL, --log_level LOG_LEVEL
                        log level
  -L APSCHEDULER_LOG_LEVEL, --apscheduler_log_level APSCHEDULER_LOG_LEVEL
                        apscheduler log level, default warning
  -s SYSTEM_METRIC, --system_metric SYSTEM_METRIC
                        Select the system metric to use. System Metric: carbon
                        _update_operations,carbon_metrics_received,carbon_comm
                        itted_points,carbon_points_per_update,carbon_cpu_usage
                        ,carbon_creates.The default is Select All
  --syslog_address SYSLOG_ADDRESS
                        syslog address, enable syslog handle when value is not
                        empty, If you want to send to the local, the value is
                        '/dev/log'
  --syslog_facility {auth,authpriv,cron,daemon,ftp,kern,lpr,mail,news,security,syslog,user,uucp,local0,local1,local2,local3,local4,local5,local6,local7}
                        syslog facility, can only be used when syslog is
                        enabled
  --request_pool_connections REQUEST_POOL_CONNECTIONS
                        init connections for the requests pool, default is 10
  --request_pool_maxsize REQUEST_POOL_MAXSIZE
                        max size for the requests pool, default is 10
  --request_max_retries REQUEST_MAX_RETRIES
                        max retries for the request, default is 3
  --request_pool_block REQUEST_POOL_BLOCK
                        whether to block the request when pool is full,
                        default is False
  --request_timeout REQUEST_TIMEOUT
                        timeout of request in seconds, default is 9
```
### Custom Metric and Config
The `graphite_exporter` can be configured to translate specific dot-separated graphite metrics into labeled Prometheus metrics via YAML configuration file.

An example configuration:
```yaml
# base param
global:
  prefix: graphite      # prometheus metric prefix
  interval: 1m          # collection data interval
  from: -90s            # graphite web requests param. learn more: https://graphite.readthedocs.io/en/latest/render_api.html#from-until
  until: now            # graphite web requests param. learn more: https://graphite.readthedocs.io/en/latest/render_api.html#from-until
  timeout: 10           # requests timeout
  ip: 192.168.215.170   # graphite web ip
  port: 5000            # graphite web port
  listen_port: 9108     # graphite exporter listen port

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
