#include <cassert>
#include "../firmware/simple_touch/motion.h"
using namespace motion;
int main() {
  Tracker t;assert(t.duration==60000);
  t.command(Command::Down,0,60000);
  t.tick(59999);assert(t.state==State::Closing);
  t.command(Command::Stop,60000,60000);assert(t.state==State::Closed);
  t=Tracker{};
  t.command(Command::Stop,0,30000);assert(t.state==State::Unknown);
  t.command(Command::Down,100,30000);assert(t.state==State::Closing);
  t.command(Command::Stop,30099,30000);assert(t.state==State::Partial);
  t.command(Command::Up,40000,30000);
  t.command(Command::Up,50000,30000);
  t.tick(70000);assert(t.state==State::Open);
  t.command(Command::Stop,80000,30000);assert(t.state==State::Open);
  t.command(Command::Down,90000,30000);
  t.command(Command::Stop,120000,30000);assert(t.state==State::Closed);
  t.command(Command::Up,130000,30000);
  t.command(Command::Down,135000,30000);
  t.tick(160000);assert(t.state==State::Closing);
  t.tick(165000);assert(t.state==State::Closed);
  t.command(Command::Favorite,166000,30000);t.tick(200000);
  assert(t.state==State::Favorite);
  t.command(Command::Stop,200000,30000);assert(t.state==State::Favorite);
  t.command(Command::Up,0xfffffff0,10000);
  t.tick(uint32_t(0xfffffff0+9999u));assert(t.state==State::Opening);
  t.tick(uint32_t(0xfffffff0+10000u));assert(t.state==State::Open);
  t=Tracker{};assert(t.state==State::Unknown); // Restart does not restore stale position.
}
