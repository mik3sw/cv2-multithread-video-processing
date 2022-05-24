import logging
from rich.logging import RichHandler
from pathlib import Path
import time
import cv2
#from cartoon import makecartoon as frame_processor
from rich.progress import Progress
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
)

import threading
import time
import queue
import multiprocessing as mp


def get_video_details(filename):
    cap = cv2.VideoCapture(filename)
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    fps = cap.get(cv2.CAP_PROP_FPS)
    return int(width), int(height), int(fps), int(count)


# == Global variables ==
q = queue.Queue()
final = queue.Queue()


bar = Progress(
        SpinnerColumn("dots"),
        "[progress.description]{task.description}",
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeRemainingColumn(),
    )

FORMAT = "%(message)s"
logging.basicConfig(
    level="NOTSET", format=FORMAT, datefmt="[%X]", handlers=[RichHandler()]
)

task = None

def worker():
    while True:
        frame = q.get()
        if frame is None:
            break
        do_sth(frame)
        q.task_done()


def do_sth(frame):
    # here put your function
    new_frame = cv2.flip(frame[0], 0)
    
    final.put((new_frame, frame[1]))
    bar.update(task, advance=1)
    time.sleep(0.1)


def get_ordered_frame(j):
    for item in final.queue:
        if item[1] == j:
            return item[0]


def init(filename):
    global task
    t1 = time.perf_counter()
    threads = []
    thread_count = mp.cpu_count()
    
    # File path
    suffix = Path(filename).suffix
    no_suffix = filename.split(suffix)[0]
    out_filename = f'{no_suffix}_processed{suffix}'

    # Video source, video out, video info
    width, height, fps, count = get_video_details(filename)
    cap = cv2.VideoCapture(filename)
    fourcc = cv2.VideoWriter_fourcc('m', 'p', '4', 'v')
    out = cv2.VideoWriter(out_filename, fourcc, fps, (width, height))

    # == Task Information ==
    log = logging.getLogger('rich')
    log.info("Video source: {}\n"
             "Frame count: {}\n"
             "Resolution: {} x {}".format(filename, count, height, width))
    #log.info("Frame da processare: {}".format(count))


    # == Threads ==
    # note: Threads names (name = ...)
    log.debug("Starting {} Threads".format(thread_count))
    for x in range(0, thread_count):
        t = threading.Thread(target=worker)
        threads.append(t)
        t.start()
        #log.debug('Started: %s' % t)
    #log.debug("Threads creati!")

    # == Queue ==
    with bar as progress:
        #log.debug("Metto ogni frame nella Queue (frame, index)")
        task2 = progress.add_task("[bold blue]Getting frames", total=count)
        task = progress.add_task("[bold green]Processing...", total=count)
        
        cap = cv2.VideoCapture(filename)
        i = 0
        while True:
            ret, frame = cap.read()
            if ret:
                q.put((frame, i))
                i+=1 
                progress.update(task2, advance=1)
            else:
             break
        # block until all tasks are done
        q.join()

        # stop workers
        for _ in threads:
            q.put(None)

        for t in threads:
            t.join()
    

        # == video output ==
        j = 0
        #log.debug("Writing frames: {}".format(out_filename))
    
        task3 = progress.add_task("[bold yellow]Writing...", total=count)
        while j!= count:
            fr = get_ordered_frame(j)
            out.write(fr)
            progress.update(task3, advance=1)
            j+=1

    # == Finish ==
    t2 = time.perf_counter()
    log.info(f'Finished in {t2-t1} seconds')
