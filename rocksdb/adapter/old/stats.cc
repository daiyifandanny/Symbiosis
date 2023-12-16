//
// Created by daiyi on 2019/09/30.
//

#include "stats.h"
#include <x86intrin.h>
#include <cassert>
#include <cmath>
#include <iostream>
#include <fstream>

using std::stoull;

Statistic* Statistic::singleton = nullptr;
bool report_switch = true;
FILE* stats_output = fopen("stats.txt", "w");

Statistic::Statistic()
    : timers(5, Timer{}), counters(5, 0), initial_time(__rdtsc()) {}

Statistic* Statistic::GetInstance() {
  if (!singleton) singleton = new Statistic();
  return singleton;
}

void Statistic::StartTimer(uint32_t id) {
  Timer& timer = timers[id];
  timer.Start();
}

std::pair<uint64_t, uint64_t> Statistic::PauseTimer(uint32_t id, bool record) {
  Timer& timer = timers[id];
  IncrementCounter(id);
  return timer.Pause(record);
}

void Statistic::ResetTimer(uint32_t id) {
  Timer& timer = timers[id];
  timer.Reset();
}

uint64_t Statistic::ReportTime(uint32_t id) {
  Timer& timer = timers[id];
  return timer.Time();
}

void Statistic::ReportTime() {
  if (!report_switch) return;

  for (size_t i = 0; i < timers.size(); ++i) {
    printf("Timer %lu: %lu avgUs:%f\n", i, timers[i].Time(),
           float(timers[i].Time()) / counters[i]);
  }

  for (size_t i = 0; i < counters.size(); ++i) {
    printf("Counter %lu: %lu\n", i, counters[i]);
  }
}

void Statistic::IncrementCounter(uint32_t id, uint64_t value) {
  counters[id] += value;
}

void Statistic::ResetCounter(uint32_t id) { counters[id] = 0; }

uint64_t Statistic::GetTime() {
  unsigned int dummy = 0;
  uint64_t time_elapse = __rdtscp(&dummy) - initial_time;
  return time_elapse / frequency;
}

void Statistic::ResetAll() {
  for (Timer& t : timers) t.Reset();
  for (uint64_t& c : counters) c = 0;
  initial_time = __rdtsc();
  app_hit = 0;
  app_num = 0;
  kernel_hit = 0;
  kernel_num = 0;
}

void Statistic::PrintStats() {
    fprintf(stats_output, "Time: %.0f kernel_ratio: %.2f kernel_num: %ld app_ratio: %.2f app_num: %lu\n",
      float(timers[1].Time()) / counters[1], float(kernel_hit) / kernel_num, kernel_num, float(app_hit) / app_num, app_num);
}

Statistic::~Statistic() { ReportTime(); }