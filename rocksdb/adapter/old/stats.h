//
// Created by daiyi on 2019/09/30.
//

#ifndef LEVELDB_STATS_H
#define LEVELDB_STATS_H

#include <cstdint>
#include <cstring>
#include <map>
#include <string>
#include <vector>
#include "timer.h"

using std::string;
using std::to_string;

class Timer;
class Statistic {
 private:
  static Statistic* singleton;
  Statistic();

  std::vector<Timer> timers;
  std::vector<uint64_t> counters;

  

 public:
  static const uint64_t frequency = 3700;

  uint64_t initial_time;
  
  uint64_t app_hit = 0;
  uint64_t app_num = 0;
  uint64_t kernel_hit = 0;
  uint64_t kernel_num = 0;

  static Statistic* GetInstance();

  void StartTimer(uint32_t id);
  std::pair<uint64_t, uint64_t> PauseTimer(uint32_t id, bool record = false);
  void ResetTimer(uint32_t id);
  uint64_t ReportTime(uint32_t id);
  void ReportTime();

  void IncrementCounter(uint32_t id, uint64_t value = 1);
  void ResetCounter(uint32_t id);

  uint64_t GetTime();
  void ResetAll();
  
  void PrintStats();

  ~Statistic();
};

#endif  // LEVELDB_STATS_H