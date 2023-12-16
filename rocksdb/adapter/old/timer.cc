//
// Created by daiyi on 2020/02/02.
//

#include "timer.h"
#include <x86intrin.h>
#include <cassert>
#include "stats.h"


Timer::Timer() : time_accumulated(0), started(false) {}

void Timer::Start() {
  if (started) assert(false);
  unsigned int dummy = 0;
  time_started = __rdtscp(&dummy);
  started = true;
}

std::pair<uint64_t, uint64_t> Timer::Pause(bool record) {
  if (!started) assert(false);
  unsigned int dummy = 0;
  uint64_t time_elapse = __rdtscp(&dummy) - time_started;
  time_accumulated += time_elapse / Statistic::frequency;
  started = false;

  if (record) {
    Statistic* instance = Statistic::GetInstance();
    uint64_t start_absolute = time_started - instance->initial_time;
    uint64_t end_absolute = start_absolute + time_elapse;
    return {start_absolute / Statistic::frequency,
            end_absolute / Statistic::frequency};
  } else {
    return {0, 0};
  }
}

void Timer::Reset() {
  time_accumulated = 0;
  started = false;
}

uint64_t Timer::Time() {
  // assert(!started);
  return time_accumulated;
}