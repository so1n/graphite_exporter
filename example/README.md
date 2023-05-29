# Example
This is an example of a 'graphite_exporter' usage

First you need a 'Graphite' environment, if not, clone from https://github.com/graphite-project/docker-graphite-statsd to local and run via 'docker-compose'.
e.g:
```basn
cd ~/my_example

git clone https://github.com/graphite-project/docker-graphite-statsd
docker-compose up -f
```
Step tow, Then go to this directory(./graphite_exporter/example),And generate the data with the following command:
```bash
python feeding_carbon
```

Step 3, open a new terminal (or tab) and go back to the project directory(./graphite_exporter),and invoke the command to run`graphite_exporter`:
```bash
python -m graphite_exporter -c example/example_config.yaml
```
At last，open a new terminal (or tab) view the output via the 'curl' command:
```bash
curl http://127.0.0.1:9108
```
