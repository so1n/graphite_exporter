import functools
import logging
import time
import signal
import sys
import os


graphite_config_dict = {
    'global': {'from': '-2min', 'prefix': 'graphite', 'until': '-1min'},
    'metrics': {
        'carbon_update_operations': {
            'doc': 'all carbon agents update operations',
            'metric': "alias(sumSeries(carbon.agents.*.updateOperations)%2C'carbon_update_operations')",  # noqa
        },
        'carbon_metrics_received': {
            'doc': 'all carbon agents metrics recevied',
            'metric': "alias(sumSeries(carbon.agents.*.metricsReceived)%2C'carbon_metrics_received')",  # noqa
        },
        'carbon_committed_points': {
            'doc': 'all carbon agents committed points',
            'metric': "alias(sumSeries(carbon.agents.*.committedPoints)%2C'carbon_committed_points')",  # noqa
        },
        'carbon_points_per_update': {
            'doc': 'all carbon agents carbon points per update',
            'metric': "alias(sumSeries(carbon.agents.*.pointsPerUpdate)%2C'carbon_points_per_update')",  # noqa
        },
        'carbon_cpu_usage': {
            'doc': 'all carbon agents cpu usage',
            'metric': "alias(averageSeries(carbon.agents.*.cpuUsage)%2C'carbon_cpu_usage')",  # noqa
        },
        'carbon_creates': {
            'doc': 'all carbon agents creates',
            'metric': "alias(sumSeries(carbon.agents.*.creates)%2C'carbon_creates')",  # noqa
        }
    }
}


def shutdown(shutdown_signals=(signal.SIGINT, signal.SIGTERM)):

    def sig_handler(signum, _):
        logging.info(f'Received signal:{signal.Signals(signum).name}')
        sys.exit()

    def decorator(func):

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            old_handlers = {}
            for sig in shutdown_signals:
                old_handlers[sig] = signal.signal(sig, sig_handler)

            try:
                _func = func(*args, **kwargs)
                while True:
                    try:
                        time.sleep(5)
                    except KeyboardInterrupt:
                        sig_name = '/'.join(
                            [sig.name for sig in shutdown_signals]
                        )
                        logging.warning(
                            f"You can use kill -{sig_name} {os.getpid()}"
                        )
                    except Exception:
                        return _func
            finally:
                for sig, old_handler in old_handlers.items():
                    signal.signal(sig, old_handler)
        return wrapper
    return decorator
