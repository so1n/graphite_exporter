import random
import socket
import time

sock: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.connect(("127.0.0.1", 8125))


# https://aws.amazon.com/about-aws/global-infrastructure/regional-product-services/?nc1=h_ls
region_list = ["US_East", "Asia_Pacific", "Europe_Frankfurt", "South_America_Sao_Paulo"]
service_list = ["app", "app1", "app2", "app3", "app4"]

while True:
    for column in ["dau", "user"]:
        metric: str = f"example.{random.choice(service_list)}.{random.choice(region_list)}.{column}"
        sock.sendall(bytes(f"{metric}:{random.randint(1, 99)}|c", encoding="utf-8"))
    time.sleep(1)
