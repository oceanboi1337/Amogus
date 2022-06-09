import aiohttp, asyncio, os, time

private = os.popen("ip addr show eth1 | grep -o -P '(?<=inet ).*(?=/)'").read().replace('\n', '')

async def get_stats(id):
    async with aiohttp.ClientSession() as s:
        async with s.get(f'http://{private}:2375/containers/{id}/stats?stream=false') as resp:
            if resp.status == 200:
                return await resp.json()

async def get_containers():
    async with aiohttp.ClientSession() as s:
        async with s.get(f'http://{private}:2375/containers/json') as resp:
            if resp.status == 200:
                containers = await resp.json()
                containers = [x for x in containers if time.time() - x.get('Created') > 30]
                return containers

# https://docs.docker.com/engine/api/v1.41/#operation/ContainerStats
async def calculate_percentage(stats : dict):
    cur_stats = stats['cpu_stats'] # Previous CPU stats from last query
    pre_stats = stats['precpu_stats'] # Current CPU stats

    system_cpu_delta = cur_stats['system_cpu_usage']    - pre_stats['system_cpu_usage']
    cpu_delta = cur_stats['cpu_usage']['total_usage']   - pre_stats['cpu_usage']['total_usage']

    return (cpu_delta / system_cpu_delta) * cur_stats['online_cpus'] * 100

async def main():
    while 1:
        if containers := await get_containers():
            for container in containers:
                id = container.get('Id')
                if stats := await get_stats(id):
                    stats = await calculate_percentage(stats)
                    async with aiohttp.ClientSession() as s:
                        async with s.post('http://10.114.0.2/api/monitor', data={'container': id, 'load': stats}) as resp:
                            if resp.status == 200:
                                print(await resp.text())

        await asyncio.sleep(1)

if __name__ == '__main__':
    asyncio.run(main())