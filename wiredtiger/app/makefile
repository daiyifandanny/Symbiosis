CXX=g++
CXXFLAGS=-g -std=c++11 -O3


simple_read	:	simple_read.cpp adapter.h adapter.cc LRUcache.h LRUcache.cc /usr/local/lib/libwiredtiger.a
	$(CXX) -o $@ $^ $(CXXFLAGS) -lpthread -ldl -march=native

all	:	simple_read

clean:
	rm simple_read
