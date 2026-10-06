#pragma once
#include <stdint.h>

// Time-based assumptions only. No RF command is sent when a timer expires.
namespace motion {
enum class State { Unknown, Opening, Closing, Open, Closed, Partial, Favorite };
enum class Command { Up, Down, Stop, Favorite };
struct Tracker {
  State state=State::Unknown;
  uint32_t started=0;
  uint32_t duration=60000;
  bool moving() const { return state==State::Opening || state==State::Closing; }
  void tick(uint32_t now) {
    if(moving() && uint32_t(now-started)>=duration)
      state=state==State::Opening ? State::Open : State::Closed;
  }
  void command(Command action,uint32_t now,uint32_t travelMs) {
    tick(now);
    if(action==Command::Stop) { if(moving())state=State::Partial; return; }
    if(action==Command::Favorite) { state=State::Favorite; return; }
    const bool up=action==Command::Up;
    const State movingState=up ? State::Opening : State::Closing;
    const State endpoint=up ? State::Open : State::Closed;
    // Repeated presses must not extend an existing journey or unset its endpoint.
    if(state==movingState || state==endpoint)return;
    state=movingState;started=now;duration=travelMs;
  }
  const char* label() const {
    switch(state) {
      case State::Opening:return "opening";
      case State::Closing:return "closing";
      case State::Open:return "open";
      case State::Closed:return "closed";
      case State::Partial:return "partial";
      case State::Favorite:return "favorite";
      default:return "unknown";
    }
  }
};
}
