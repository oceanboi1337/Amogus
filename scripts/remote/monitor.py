import asyncio, aiohttp, json
from audioop import avg
from enum import Enum

class BadParameter(Exception): pass
class ServerError(Exception): pass
class ContainerNotFound(Exception): pass
class ContainerNotRunning(Exception): pass
class ContainerConflict(Exception): pass

class Container:
    class State(str, Enum):
        created = 'created'
        restarting = 'restarting'
        running = 'running'
        removing = 'paused'
        exited = 'exited'
        dead = 'dead'

    def __init__(self, id : str, state : str) -> None:
        self.id = id
        self.state = Container.State(state)

    async def delete(self) -> bool:
        async with aiohttp.ClientSession() as session:
            async with session.delete(f'http://localhost:2375/container/{self.id}?force=true') as resp:
                if resp.status == 204:
                    return True
                elif resp.status == 400: raise BadParameter
                elif resp.status == 404: raise ContainerNotFound
                elif resp.status == 409: raise ContainerConflict
                elif resp.status == 500: raise ServerError

        raise Exception(f'Unknown error while deleting {self.id}')

    async def stats(self):
        async with aiohttp.ClientSession() as session:
            async with self.session.get(f'http://localhost:2375/containers/{self.id}/stats?stream=false') as resp:
                if resp.status == 200:
                    return self, await resp.json()
                elif resp.status == 404: raise ContainerNotFound
                elif resp.status == 500: raise ServerError

        raise Exception(f'Unknown error while fetching stats for {self.id}')

async def get_containers():
    async with aiohttp.ClientSession() as session:
        async with session.get('http://localhost:2375/containers/json?all=true') as resp:
            if resp.status == 200:

                # Convert the JSON responses to Python objects
                for container in [Container(x['Id'], x['State']) for x in await resp.json()]:
                    if container.state == Container.State.running:
                        yield container

                    elif container.state == Container.State.dead: await container.delete()
                    elif container.state == Container.State.exited:
                        await container.delete()
                    
            elif resp.status == 400: raise BadParameter
            elif resp.status == 500: raise ServerError

    raise Exception('Unknown error while fetching containers')

async def calculate_percentage(stats):
    cur_stats = stats['cpu_stats'] # Previous CPU stats from last query
    pre_stats = stats['precpu_stats'] # Current CPU stats

    system_cpu_delta = cur_stats['system_cpu_usage']    - pre_stats['system_cpu_usage']
    cpu_delta = cur_stats['cpu_usage']['total_usage']   - pre_stats['cpu_usage']['total_usage']

    return (cpu_delta / system_cpu_delta) * cur_stats['online_cpus'] * 100

async def average_load(containers, time):
    results = {}
    for x in range(time):

        # Creates a task for ecah container so they can be queried in parallel
        tasks = [container.stats() for container in containers]

        for container, stats in await asyncio.gather(*tasks, return_exceptions=True):

            if container.id not in results:
                results[container.id] = []

            results[container.id].append(await calculate_percentage(stats))

        await asyncio.sleep(1)

    # Calculates the average CPU usage from all the different times it was queried
    for container_id, load in results.items():
        total = 0

        for cpu_usage in load:
            total += cpu_usage

        avg_load = total / len(results[container_id])
        yield container_id, avg_load

async def main():
    cpu_limit = 25 # CPU usage limit each container can use is 25%

    while 1:

        # Gets the average CPU usage of a container over 5 seconds
        async for container, load in average_load([container async for container in get_containers()], time=5):
            
            if load > cpu_limit:
                pass


if __name__ == '__main__':
    asyncio.run(main())