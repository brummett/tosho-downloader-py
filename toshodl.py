import asyncio
import httpx
import logging
import logging.handlers
import queue

from toshodl.ToshoSearch import ToshoSearch
from toshodl import AsyncConsole

num_workers = 5

async def worker(name, work_queue):
    while True:
        #print(f'worker {name} waiting for a task...')
        task = await work_queue.get()
        #print(f'worker {name} got a task: { task }')
        further_tasks = task.run()
        if further_tasks:
            for t in further_tasks:
                work_queue.put_nowait(t)
        work_queue.task_done()

def setup_logging():
    #logging.basicConfig(level=logging.INFO)

    # Setup for asyncio
    log_queue = queue.Queue()
    queue_handler = logging.handlers.QueueHandler(log_queue)
    log_listener = logging.handlers.QueueListener(log_queue)
    root_logger = logging.getLogger()
    root_logger.addHandler(queue_handler)
    log_listener.start()

async def main():
    setup_logging()

    work_queue = asyncio.Queue()
    reader, writer = await AsyncConsole.init()

    workers = []
    for i in range(num_workers):
        w = asyncio.create_task(worker(f'worker-{i}', work_queue))
        workers.append(w)

    tosho = ToshoSearch()

    while True:
        writer.write('waiting for input: '.encode())
        line = await reader.readline()
        if not line:
            print("Done reading input!")
            break
        trimmed = line.decode().strip()
        if len(trimmed) > 0:
            id = await tosho.search(trimmed)
            if id is not None:
                writer.write(f'{trimmed} is id {id}\n'.encode())
                #task = ToshoResolver(id, trimmed)
                #work_queue.put_nowait(task)

    print("Out of the main loop")


if __name__ == '__main__':
    asyncio.run(main())
