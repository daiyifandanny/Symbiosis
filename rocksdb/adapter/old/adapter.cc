#include "adapter.h"


void DeleteNullptr(const Slice& key, void* value) {};

Adapter* Adapter::instance = nullptr;
