#pragma once
#include <stdint.h>
#include <stddef.h>

// Dooya-family FSK variant confirmed against independent Simple Touch captures.
// Explicit byte loads avoid alignment and host-endianness assumptions.
namespace protocol {
inline uint32_t le32(const uint8_t* p) {
  return uint32_t(p[0]) | uint32_t(p[1])<<8 | uint32_t(p[2])<<16 | uint32_t(p[3])<<24;
}
inline uint16_t crc(const uint8_t* data, size_t size) {
  uint16_t c=0xffff;
  for(size_t i=0;i<size;i++) {
    c^=uint16_t(data[i])<<8;
    for(int bit=0;bit<8;bit++) c=(c&0x8000)?(c<<1)^0x8005:c<<1;
  }
  return c;
}
inline void encrypt(uint8_t* data) {
  const uint8_t keyBytes[16]={'D','O','O','Y','A',' ','2','0','1','4','1','6','2','5',0,0};
  uint32_t v[4],key[4];
  for(int i=0;i<4;i++){v[i]=le32(data+4*i);key[i]=le32(keyBytes+4*i);}
  uint32_t sum=0,z=v[3];
  for(int round=0;round<14;round++) {
    sum+=0x9e3779b9u;
    unsigned e=(sum>>2)&3;
    for(unsigned i=0;i<4;i++) {
      uint32_t y=v[(i+1)&3];
      uint32_t mix=((z>>5 ^ y<<2)+(y>>3 ^ z<<4)) ^ ((sum^y)+(key[(i&3)^e]^z));
      v[i]+=mix;z=v[i];
    }
  }
  for(int i=0;i<16;i++)data[i]=v[i/4]>>(8*(i%4));
}
inline void decrypt(uint8_t* data) {
  const uint8_t keyBytes[16]={'D','O','O','Y','A',' ','2','0','1','4','1','6','2','5',0,0};
  uint32_t v[4],key[4];for(int i=0;i<4;i++){v[i]=le32(data+4*i);key[i]=le32(keyBytes+4*i);}
  uint32_t sum=uint32_t(14u*0x9e3779b9u),y=v[0];
  for(int round=0;round<14;round++){
    unsigned e=(sum>>2)&3;
    for(int i=3;i>=0;i--){
      uint32_t z=v[(i+3)&3];
      uint32_t mix=((z>>5 ^ y<<2)+(y>>3 ^ z<<4)) ^ ((sum^y)+(key[(i&3)^e]^z));
      v[i]-=mix;y=v[i];
    }
    sum-=0x9e3779b9u;
  }
  for(int i=0;i<16;i++)data[i]=v[i/4]>>(8*(i%4));
}
inline uint32_t be32(const uint8_t* p){return uint32_t(p[0])<<24|uint32_t(p[1])<<16|uint32_t(p[2])<<8|p[3];}
struct Received {uint32_t address;uint16_t counter,groups;uint8_t action;};
inline bool decode(const uint8_t p[21],Received &out){
  if(p[0]!=18||p[1]!=0x12||p[2]!=0xc1||crc(p+1,18)!=(uint16_t(p[19])<<8|p[20]))return false;
  uint8_t body[16];for(int i=0;i<16;i++)body[i]=p[i+3];decrypt(body);
  if(body[12]!=2||body[13]!=2||body[15]!=0||be32(body+2)!=be32(body+6))return false;
  out.address=be32(body+2);out.counter=uint16_t(body[0])<<8|body[1];out.groups=uint16_t(body[10])<<8|body[11];out.action=body[14];
  return out.address&&out.groups;
}
inline void encode(uint32_t address,uint16_t counter,uint8_t action,uint8_t out[21]) {
  out[0]=0x12;out[1]=0x12;out[2]=0xc1;
  out[3]=counter>>8;out[4]=counter;
  for(int i=0;i<4;i++)out[5+i]=out[9+i]=address>>(24-8*i);
  out[13]=0;out[14]=1;out[15]=2;out[16]=2;out[17]=action;out[18]=0;
  encrypt(out+3);
  uint16_t c=crc(out+1,18);out[19]=c>>8;out[20]=c;
}
}
