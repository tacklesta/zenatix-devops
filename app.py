import psutil
from datetime import datetime
import pandas as pd
import time
import numpy as np
import pandas as pd
from elasticsearch import Elasticsearch
from espandas import Espandas
from elasticsearch import helpers


def get_size(bytes):
    for unit in ['', 'K', 'M', 'G', 'T', 'P']:
        if bytes < 1024:
            return f"{bytes:.2f}{unit}B"
        bytes /= 1024
        
        #bytes /= 1024
        #return bytes/100


def get_processes_info():
    processes = []
    for process in psutil.process_iter():
        with process.oneshot():
            pid = process.pid
            if pid == 0:
                continue
            name = process.name()
            try:
                create_time = datetime.fromtimestamp(process.create_time())
            except OSError:
                create_time = datetime.fromtimestamp(psutil.boot_time())
            try:
                cores = len(process.cpu_affinity())
            except psutil.AccessDenied:
                cores = 0
            cpu_usage = process.cpu_percent()
            status = process.status()
            try:
                nice = int(process.nice())
            except psutil.AccessDenied:
                nice = 0
            try:
                memory_usage = process.memory_full_info().uss
            except psutil.AccessDenied:
                memory_usage = 0
            io_counters = process.io_counters()
            read_bytes = io_counters.read_bytes
            write_bytes = io_counters.write_bytes
            n_threads = process.num_threads()

        processes.append({
            'pid': pid, 'name': name, 'create_time': create_time,
            'cores': cores, 'cpu_usage': cpu_usage, 'status': status, 'nice': nice,
            'memory_usage': memory_usage, 'read_bytes': read_bytes, 'write_bytes': write_bytes,
            'n_threads': n_threads
        })

    return processes


def construct_dataframe(processes):
    df = pd.DataFrame(processes)
    df.set_index('pid', inplace=True)
    df['memory_usage'] = df['memory_usage'].apply(get_size)
    df['write_bytes'] = df['write_bytes'].apply(get_size)
    df['read_bytes'] = df['read_bytes'].apply(get_size)
    df['create_time'] = df['create_time'].apply(
        datetime.strftime, args=("%Y-%m-%d %H:%M:%S",))
    return df


result = get_processes_info()

df = construct_dataframe(result).head(20)

df.reset_index(inplace = True)

es = Elasticsearch(http_compress=True)

df['indexId'] = "ind" + df.index.astype(str)

INDEX = 'pid'
TYPE = '_doc'
esp = Espandas()
esp.es_write(df, INDEX, TYPE)
