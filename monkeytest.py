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

from random import shuffle
from time import perf_counter as time
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
import json
import os
import sys

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
                        type=int,
                        default=128,
                        help='Total MB to write',
                        **common_params)
    parser.add_argument('-w', '--write-block-size',
                        type=int,
                        default=1024,
                        help='The block size for writing in bytes',
                        **common_params)
    parser.add_argument('-r', '--read-block-size',
                        type=int,
                        default=512,
                        help='The block size for reading in bytes',
                        **common_params)
    parser.add_argument('-j', '--json',
                        help='Output to json file',
                        **common_params)
    args = parser.parse_args()
    return args


class Benchmark:

    def __init__(self, file, write_mb, write_block_kb, read_block_b):
        self.file = file
        self.write_mb = write_mb
        self.write_block_kb = write_block_kb
        self.read_block_b = read_block_b
        wr_blocks = int(self.write_mb * 1024 / self.write_block_kb)
        rd_blocks = int(self.write_mb * 1024 * 1024 / self.read_block_b)
        self.write_results = self.write_test(
            1024 * self.write_block_kb, wr_blocks)
        self.read_results = self.read_test(self.read_block_b, rd_blocks)

    @staticmethod
    def clear_line():
        print('\033[2K', end='')

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
                      end='\r')
            buff = os.urandom(block_size)
            start = time()
            os.write(f, buff)
            t = time() - start
            took.append(t)

        os.close(f)
        self.clear_line()
        return took

    def read_test(self, block_size, blocks_count, show_progress=True):
        '''
        Performs read speed test by reading random offset blocks from
        file, at maximum of blocks_count, each at size of block_size
        bytes until the End Of File reached.
        Returns a list of read times in sec of each block.
        '''
        f = os.open(self.file, flags=os.O_RDONLY | os.O_DIRECT)  # low-level I/O
        # generate random read positions
        offsets = list(range(0, blocks_count * block_size, block_size))
        shuffle(offsets)

        took = []
        for i, offset in enumerate(offsets, 1):
            if show_progress and i % int(
                    self.write_block_kb * 1024 / self.read_block_b) == 0:
                # read is faster than write, so try to equalize print period
                print('Reading: {:.2f} %'.format((i + 1) * 100 / blocks_count),
                      end='\r')
            start = time()
            os.lseek(f, offset, os.SEEK_SET)  # set position
            buff = os.read(f, block_size)  # read from position
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
            'written_mb': self.write_mb,
            'write_time': round(sum(self.write_results), 4),
            'write_speed': round(self.write_mb / sum(self.write_results), 2),
            'write_speed_min': round(self.write_block_kb / (1024 * max(self.write_results)), 2),
            'write_speed_max': round(self.write_block_kb / (1024 * min(self.write_results)), 2),
            'read_blocks': len(self.read_results),
            'block_size': self.read_block_b,
            'read_time': round(sum(self.read_results), 4),
            'read_speed': round(self.write_mb / sum(self.read_results), 2),
            'read_speed_min': round(self.read_block_b / (1024 * 1024 * max(self.read_results)), 2),
            'read_speed_max': round(self.read_block_b / (1024 * 1024 * min(self.read_results)), 2),
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
    args = get_args()
    benchmark = Benchmark(file=args.file,
                          write_mb=args.size,
                          write_block_kb=args.write_block_size,
                          read_block_b=args.read_block_size)
    if args.json is not None:
        benchmark.get_json_result(args.json)
    else:
        benchmark.print_result()
    os.remove(args.file)


if __name__ == '__main__':
    main()
