CXX=g++
CXXFLAGS=-g -std=c++11


simple_read	:	simple_read.cpp /usr/local/lib/libsqlite3.a
	$(CXX) -o $@ $^ $(CXXFLAGS) -lpthread -ldl

all	:	simple_read

clean:
	rm simple_read
