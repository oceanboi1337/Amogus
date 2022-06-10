import asyncio, aiohttp, random
import json
from digitalocean import Droplet
from extensions import database, digitalocean, docker, loadbalancer
from typing import List

from models import CloudImage, CloudRegion, CloudSize

def parse(stats : dict):
    cur_stats = stats['cpu_stats'] # Previous CPU stats from last query
    pre_stats = stats['precpu_stats'] # Current CPU stats

    system_cpu_delta = cur_stats['system_cpu_usage']    - pre_stats['system_cpu_usage']
    cpu_delta = cur_stats['cpu_usage']['total_usage']   - pre_stats['cpu_usage']['total_usage']

    return (cpu_delta / system_cpu_delta) * cur_stats['online_cpus'] * 100

async def fetch_containers(droplet : dict):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'http://{droplet.get("private_ip")}:2375/containers/json') as resp:
            if resp.status == 200:
                return [x.get('Id') for x in await resp.json()]

async def stats(droplet : dict, container : dict):
    async with aiohttp.ClientSession() as session:
        async with session.get(f'http://{droplet.get("private_ip")}:2375/containers/{container}/stats?stream=false') as resp:
            if resp.status == 200:
                return [droplet, container, parse(await resp.json())]

async def collector(droplets : List[str]):
    tasks = [fetch_containers(x) for x in droplets] # Change to private later when database updates
    results = await asyncio.gather(*tasks, return_exceptions=True)
    tasks.clear()

    for index, containers in enumerate(results):
        droplet = droplets[index]

        for container in containers:
            tasks.append(stats(droplet, container))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    def average(l): return (sum(l) / (len(l) if len(l) > 0 else 1))

    data = {}

    for droplet, container, load in results:

        webapp = database.container_app(container)
        domain = webapp.get('domain')

        if domain not in data:
            data[domain] = []

        data[domain].append(load)

    data = {domain: average(load) for domain, load in data.items()}

    return data.items()

async def expand(domain : str, droplets : list) -> bool:
    for db_droplet in droplets:
        if (droplet := digitalocean.fetch_droplet(db_droplet.get('id'))) and droplet.available_slots() > 0:
            if container := docker.create(domain, droplet):
                database.new_container(domain, container.id, droplet.id)
                loadbalancer.add(domain, container)
                loadbalancer.add(domain, droplet)
                return True

    db_droplets_inactive = database.droplets(active=False)
    if len(db_droplets_inactive) <= 0:
        if droplet := digitalocean.create_droplet(f'app-node-{(len(droplets)+len(db_droplets_inactive))+1}', CloudSize.Cpu2Gb2, CloudImage.Ubuntu_22_04_LTS_x64, CloudRegion.Frankfurt1, ['app-node']):
            database.new_droplet(droplet.id, droplet.hostname)
            return True

async def shrink(domain : str) -> bool:
    if (containers := database.webapp_containers(domain)) and len(containers) > 1:
        container = random.choice(containers)
        if droplet := database.container_to_droplet(container.get('container')):
            if droplet := digitalocean.fetch_droplet(droplet.get('droplet')):
                if container := docker.container(container.get('container'), droplet):
                    container.delete()
                    loadbalancer.remove(domain, container)
                    database.delete_container(container.id)
            else:
                print('Failed to fetch droplet', droplet)
        else:
            print('Failed to convert container to droplet', droplet, containers)


async def main():
    while 1:
        if droplets := database.droplets(active=True):
            for domain, load in await collector(droplets):
                cpu_limit = (90 / (2 * 4))
                if load >= cpu_limit * 0.6:
                    print(f'Domain ({domain}) needs expansion, average load is: {load} / {cpu_limit}')
                    if await expand(domain, droplets):
                        print(f'Expanded domain ({domain})')
                elif load <= cpu_limit * 0.2:
                    print(f'Domain ({domain}) should shrink, average load is {load} / {cpu_limit}')
                    await shrink(domain)
                else:
                    print(f'Domain ({domain}) average load is {load} / {cpu_limit}, its in a good spot, keep it here')

        await asyncio.sleep(1)

if __name__ == '__main__':
    asyncio.run(main())
