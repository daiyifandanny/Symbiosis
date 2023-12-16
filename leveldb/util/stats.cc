//
// Created by daiyi on 2019/09/30.
//

#include "util/stats.h"
#include <x86intrin.h>
#include <cassert>
#include <cmath>
#include <iostream>
#include <fstream>

using std::stoull;

Statistics* Statistics::singleton = nullptr;
bool report_switch = true;
FILE* stats_output = fopen("stats.txt", "w");

Statistics::Statistics()
    : timers(5, Timer{}), counters(5, 0), initial_time(__rdtsc()) {}

Statistics* Statistics::GetInstance() {
  if (!singleton) singleton = new Statistics();
  return singleton;
}

void Statistics::StartTimer(uint32_t id) {
  Timer& timer = timers[id];
  timer.Start();
}

std::pair<uint64_t, uint64_t> Statistics::PauseTimer(uint32_t id, bool record) {
  Timer& timer = timers[id];
  IncrementCounter(id);
  return timer.Pause(record);
}

void Statistics::ResetTimer(uint32_t id) {
  Timer& timer = timers[id];
  timer.Reset();
}

uint64_t Statistics::ReportTime(uint32_t id) {
  Timer& timer = timers[id];
  return timer.Time();
}

void Statistics::ReportTime() {
  if (!report_switch) return;

  for (size_t i = 0; i < timers.size(); ++i) {
    printf("Timer %lu: %lu avgUs:%f\n", i, timers[i].Time(),
           float(timers[i].Time()) / counters[i]);
  }

  for (size_t i = 0; i < counters.size(); ++i) {
    printf("Counter %lu: %lu\n", i, counters[i]);
  }
}

void Statistics::IncrementCounter(uint32_t id, uint64_t value) {
  counters[id] += value;
}

void Statistics::ResetCounter(uint32_t id) { counters[id] = 0; }

uint64_t Statistics::GetTime() {
  unsigned int dummy = 0;
  uint64_t time_elapse = __rdtscp(&dummy) - initial_time;
  return time_elapse / frequency;
}

void Statistics::ResetAll() {
  for (Timer& t : timers) t.Reset();
  for (uint64_t& c : counters) c = 0;
  initial_time = __rdtsc();
  app_hit = 0;
  app_num = 0;
  kernel_hit = 0;
  kernel_num = 0;
}

void Statistics::PrintStats() {
    fprintf(stats_output, "Time: %.0f kernel_ratio: %.2f kernel_num: %ld app_ratio: %.2f app_num: %lu\n",
      float(timers[1].Time()) / counters[1], float(kernel_hit) / kernel_num, kernel_num, float(app_hit) / app_num, app_num);
}

Statistics::~Statistics() { ReportTime(); }