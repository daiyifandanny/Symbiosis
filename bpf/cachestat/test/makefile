CXX=g++
C=gcc
CXXFLAGS=-g -std=c++11

all	:	btree_sim simple_read linear

simple_read	:	simple_read.cpp
	$(CXX) -o $@ $^ $(CXXFLAGS) -lpthread

btree_sim	:	btree_sim.cpp
	$(CXX) -o $@ $^ $(CXXFLAGS) -lpthread

linear	:	linear.c
	$(C) -o $@ $^

clean:
	rm simple_read btree_sim linear
