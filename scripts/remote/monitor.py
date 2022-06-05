import asyncio, aiohttp, json
from typing import List

class Monitor:
    def __init__(self, backend : str) -> None:
        self.backend = backend
        self.session = aiohttp.ClientSession()
        
        self.stats = {}

    async def calculate_percenteage(self, stats):
        system_cpu_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
        cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
        cpus = stats['cpu_stats']['online_cpus']

        cpu_usage = (cpu_delta / system_cpu_delta) * cpus * 100
        return cpu_usage

    async def delete_container(self, container_id):
        async with self.session.delete(f'http://localhost:2375/containes{container_id}') as resp:
            if resp.status == 204:
                await self.session.delete(f'http://{self.backend}/container?id={container_id}')

    async def get_containers(self):
        async with self.session.get('http://localhost:2375/containers/json') as resp:
            data = await resp.json()
            for container in data:

                if container.get('State') in ['paused', 'exited', 'dead']:
                    self.delete_container(container.get('Id'))

                    if container.get('Id') in self.stats:
                        self.stats.pop(container.get('Id'))
                else:
                    yield container

    async def fetch_stats(self, container_id):
        resp = await self.session.get(f'http://localhost:2375/containers/{container_id}/stats?stream=false')
        return await resp.json()

    async def gather_stats(self, delay=10):
        tasks = []
        async for container in self.get_containers():
            tasks.append(self.fetch_stats(container.get('Id')))

        stats = await asyncio.gather(*tasks, return_exceptions=True)

        for stat in stats:
            if self.stats.get(stat['id']) == None:
                self.stats[stat['id']] = []

            self.stats[stat['id']].append(await self.calculate_percenteage(stat))


async def load_report(stats):
    for container in stats:
        total_percentage = 0
        for percentage in stats[container]:
            total_percentage += percentage

        average_cpu_usage = total_percentage / len(stats[container])
        print(average_cpu_usage)

async def main():
    monitor = Monitor('10.114.0.2')
    i = 0

    while 1:
        await monitor.gather_stats()
        if i % 60 == 0:
            await load_report(monitor.stats)
            monitor.stats = {}
        i += 1

if __name__ == '__main__':
    asyncio.run(main())