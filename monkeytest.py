#!/usr/bin/env python
'''
MonkeyTest -- test your hard drive read-write speed in Python
A simplistic script to show that such system programming
tasks are possible and convenient to be solved in Python

The file is being created, then written with random data, randomly read
and deleted, so the script doesn't waste your drive

(!) Be sure, that the file you point to is not something
    you need, cause it'll be overwritten during test
'''

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from random import shuffle
from time import perf_counter as time
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import json
import os
import re
import shutil
import sys
import tempfile

ASCIIART = r'''Brought to you by coding monkeys.
Eat bananas, drink coffee & enjoy!
                 _
               ,//)
               ) /
              / /
        _,^^,/ /
       (G,66<_/
       _/\_,_)    _
      / _    \  ,' )
     / /"\    \/  ,_\
  __(,/   >  e ) / (_\.oO
  \_ /   (   -,_/    \_/
    U     \_, _)
           (  /
            >/
           (.oO
'''
# ASCII-art: used part of text-image @ http://www.ascii-art.de/ascii/mno/monkey.txt
# it seems that its original author is Mic Barendsz (mic aka miK)
# text-image is a bit old (1999) so I couldn't find a way to communicate with author
# if You're reading this and You're an author -- feel free to write me


def str_to_bytes(size):
    units = {'B': 1, 'KB': 2**10, 'MB': 2**20, 'GB': 2**30, 'TB': 2**40}
    try:
        number, unit = re.match(r'^(\d+(?:\.\d+)?)\s?([KMGT]?B)?',
                                size.upper()).groups()
        return int(float(number) * units.get(unit, 'B'))
    except AttributeError:
        return None


def get_args():
    common_params = {
        'required': False,
        'action': 'store'
    }
    parser = ArgumentParser(description='Arguments',
                            formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('-f', '--file',
                        default='/tmp/monkeytest',
                        help='The file to read/write to',
                        **common_params)
    parser.add_argument('-s', '--size',
                        type=str_to_bytes,
                        default='128MB',
                        help='Total size to write',
                        **common_params)
    parser.add_argument('-w', '--write-block-size',
                        type=str_to_bytes,
                        default='1MB',
                        help='The block size for writing',
                        **common_params)
    parser.add_argument('-r', '--read-block-size',
                        type=str_to_bytes,
                        default='512B',
                        help='The block size for reading',
                        **common_params)
    parser.add_argument('-j', '--json',
                        help='Output to json file',
                        **common_params)
    args = parser.parse_args()
    return args


class Benchmark:

    def __init__(self, file, write, write_block, read_block):
        self.file = file
        self.write = write
        self.write_block, self.read_block = map(lambda x: min(x, self.write),
                                                (write_block, read_block))
        wr_blocks, rd_blocks = map(lambda x: int(self.write / x),
                                   (self.write_block, self.read_block))
        self.write_results = self.write_test(self.write_block, wr_blocks)
        self.read_results = self.read_test(self.read_block, rd_blocks)

    @staticmethod
    def clear_line():
        print('\033[2K', end='', file=sys.stderr)

    @property
    def is_tmpfs(self):
        tmpfs = tempfile.gettempdir()
        return os.path.commonpath([os.path.abspath(self.file), tmpfs]) == tmpfs

    @staticmethod
    def convert_results(result, ndigits=2):
        return round(result / 1024 ** 2, ndigits)

    @staticmethod
    def force_cache_drop():
        with open('/proc/sys/vm/drop_caches', 'w') as c:
            c.write('1')

    def write_test(self, block_size, blocks_count, show_progress=True):
        '''
        Tests write speed by writing random blocks, at total quantity
        of blocks_count, each at size of block_size bytes to disk.
        Function returns a list of write times in sec of each block.
        '''
        f = os.open(self.file, flags=os.O_CREAT | os.O_WRONLY | os.O_SYNC)  # low-level I/O

        took = []
        for i in range(blocks_count):
            if show_progress:
                print('Writing: {:.2f} %'.format((i + 1) * 100 / blocks_count),
                      end='\r', file=sys.stderr)
            buff = bytearray(block_size)
            start = time()
            os.write(f, buff)
            t = time() - start
            took.append(t)

        os.close(f)
        self.clear_line()
        return took

    def read_test(self, block_size, blocks_count, show_progress=True, randomize=True):
        '''
        Performs read speed test by reading random offset blocks from
        file, at maximum of blocks_count, each at size of block_size
        bytes until the End Of File reached.
        Returns a list of read times in sec of each block.
        '''
        flags = os.O_RDONLY;
        if not self.is_tmpfs:
            flags |= os.O_DIRECT
        f = os.open(self.file, flags=flags)  # low-level I/O
        offsets = list(range(0, blocks_count * block_size, block_size))

        # generate random read positions
        if randomize:
            shuffle(offsets)

        self.force_cache_drop()

        took = []
        for i, offset in enumerate(offsets, 1):
            if show_progress:
                print('Reading: {:.2f} %'.format((i + 1) * 100 / blocks_count),
                      end='\r')
                      end='\r', file=sys.stderr)
            start = time()
            buff = os.pread(f, block_size, offset)  # read from position
            t = time() - start
            if not buff:
                break  # if EOF reached
            took.append(t)

        os.close(f)
        self.clear_line()
        return took

    @property
    def results(self):
        return {
            'written_mb': self.convert_results(self.write, 0),
            'write_time': round(sum(self.write_results), 4),
            'write_speed': self.convert_results(self.write / sum(self.write_results)),
            'write_speed_min': self.convert_results(self.write_block / max(self.write_results)),
            'write_speed_max': self.convert_results(self.write_block / min(self.write_results)),
            'read_blocks': len(self.read_results),
            'block_size': self.read_block,
            'read_time': round(sum(self.read_results), 4),
            'read_speed': self.convert_results(self.write / sum(self.read_results)),
            'read_speed_max': self.convert_results(self.read_block / min(self.read_results)),
            'read_speed_min': self.convert_results(self.read_block / max(self.read_results))
        }

    def print_result(self):
        result = ['Written {written_mb} MB in {write_time} s',
                  'Write speed is  {write_speed} MB/s',
                  '  max: {write_speed_max}, min: {write_speed_min}',
                  '\t',
                  'Read {read_blocks} x {block_size} B blocks in {read_time} s',
                  'Read speed is {read_speed} MB/s',
                  '  max: {read_speed_max}, min: {read_speed_min}']
        result = '\n'.join(result).format(**self.results)
        print(result, end='\n\n')
        print(ASCIIART)

    def get_json_result(self, output_file):
        with open(output_file, 'w') as f:
            json.dump(self.results, f)


def main():
    if os.geteuid() != 0:
        sudo_path = shutil.which('sudo')
        print(f'Script must run as root. Relaunching with {sudo_path}',
              file=sys.stderr)
        os.execl(sudo_path,
                 sys.executable,
                 os.path.abspath(sys.argv[0]),
                 *sys.argv[1:])

    args = get_args()
    benchmark = Benchmark(file=args.file,
                          write=args.size,
                          write_block=args.write_block_size,
                          read_block=args.read_block_size)

    if args.json is not None:
        benchmark.get_json_result(args.json)
    else:
        benchmark.print_result()
    os.remove(args.file)


if __name__ == '__main__':
    main()
