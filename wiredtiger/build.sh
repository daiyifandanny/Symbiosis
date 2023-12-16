#!/bin/sh

./autogen.sh
./configure -enable-zstd -enable-snappy -enable-zlib -enable-lz4
make -j
sudo make install
