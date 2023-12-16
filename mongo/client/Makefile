CXX=g++
CXXFLAGS:=-g -std=c++11 `pkg-config --cflags --libs libmongocxx` -O2 -Wno-unused-result


simple_read	:	simple_read.cpp
	$(CXX) -o $@ $^  $(CXXFLAGS) 

all	:	simple_read

clean:
	rm simple_read
