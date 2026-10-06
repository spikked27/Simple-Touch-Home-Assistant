#include <cassert>
#include <cstdio>
#include <cstring>
#include <initializer_list>
#include "../firmware/simple_touch/protocol.h"
int main() {
  // Synthetic, unpaired identities. No captured household packets or pairing vectors.
  const uint8_t stop[]={0x12,0x12,0xc1,0x45,0xad,0x55,0x47,0x99,0xa0,0xda,0x4b,0x82,0x8d,0xe2,0x9e,0x0a,0xbc,0x5a,0xb6,0xb9,0x6c};
  const uint8_t up[]={0x12,0x12,0xc1,0x94,0x52,0xb4,0x38,0x80,0xa9,0x5f,0xe0,0xba,0x00,0x04,0xc8,0xa4,0x4e,0xca,0xab,0x46,0x44};
  uint8_t packet[21];protocol::encode(0x12345600,23,3,packet);assert(!memcmp(packet,stop,21));
  protocol::encode(0xabcdef00,512,1,packet);assert(!memcmp(packet,up,21));
  for(unsigned counter: {0u,1u,255u,256u,65534u}) {
    for(unsigned action: {1u,2u,3u,19u}) {
      protocol::encode(0xabcdef00,counter,action,packet);
      protocol::Received decoded{};
      assert(protocol::decode(packet,decoded));
      assert(decoded.address==0xabcdef00 && decoded.counter==counter);
      assert(decoded.groups==1 && decoded.action==action);
      for(unsigned bit=0;bit<168;bit++) {
        packet[bit/8]^=1u<<(bit%8);
        assert(!protocol::decode(packet,decoded));
        packet[bit/8]^=1u<<(bit%8);
      }
    }
  }
  puts("Protocol vectors passed");
}
