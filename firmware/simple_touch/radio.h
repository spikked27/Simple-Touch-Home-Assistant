#pragma once
#include "protocol.h"
#include "envelopes.h"
#include <SPI.h>
#include "esp32-hal-rmt.h"

constexpr int SCK_PIN=D8, MISO_PIN=D9, MOSI_PIN=D10, CS_PIN=D5, DATA_PIN=D2;
constexpr uint32_t MAX_US=3000000, MAX_ITEMS=10000, MAX_BURSTS=32;
namespace radio {
SPISettings spiSettings(1000000, MSBFIRST, SPI_MODE0);
rmt_data_t wave[MAX_ITEMS];
struct Burst { uint32_t start, count, duration, gap; };
Burst bursts[MAX_BURSTS];
uint32_t items=0, segmentStart=0, segmentUs=0, totalUs=0, nBursts=0;
bool halfPending=false, badWave=false, spiGood=true, rmtGood=false;
uint8_t lastLevel=0;
char line[1801]; size_t lineLength=0; bool lineOverflow=false;

bool selectRadio() {
  SPI.beginTransaction(spiSettings); digitalWrite(CS_PIN,LOW);
  uint32_t start=micros();
  while(digitalRead(MISO_PIN)) {
    if((uint32_t)(micros()-start)>5000) {
      digitalWrite(CS_PIN,HIGH); SPI.endTransaction(); spiGood=false; return false;
    }
  }
  return true;
}
void deselectRadio(){digitalWrite(CS_PIN,HIGH);SPI.endTransaction();}
uint8_t readReg(uint8_t reg){if(!selectRadio())return 0xff;SPI.transfer(reg|0xc0);uint8_t v=SPI.transfer(0);deselectRadio();return v;}
void writeReg(uint8_t reg,uint8_t value){if(!selectRadio())return;SPI.transfer(reg);SPI.transfer(value);deselectRadio();}
void strobe(uint8_t cmd){if(!selectRadio())return;SPI.transfer(cmd);deselectRadio();}
bool state(uint8_t wanted,uint32_t timeout=10000){uint32_t t=micros();do{if((readReg(0x35)&31)==wanted)return spiGood;delayMicroseconds(20);}while((uint32_t)(micros()-t)<timeout);return false;}
bool idle(){strobe(0x36);return state(1);}
bool receiveMode(){
  if(!idle())return false;
  writeReg(0x02,0x2e); // High impedance GDO0; RX uses the FIFO, not the RMT pin.
  writeReg(0x04,0x2d);writeReg(0x05,0xd4);
  writeReg(0x06,21);writeReg(0x07,0x04);writeReg(0x08,0x00);
  writeReg(0x12,0x03);writeReg(0x17,0x0c); // 30/32 sync, return to RX after a packet
  strobe(0x3a);strobe(0x34);return state(0x0d,10000);
}
bool readPacket(uint8_t packet[21]){
  uint8_t count=readReg(0x3b);
  if(count&0x80){receiveMode();return false;}
  if((count&0x7f)<23)return false;
  if(!selectRadio())return false;
  SPI.transfer(0xff);for(int i=0;i<23;i++){uint8_t b=SPI.transfer(0);if(i<21)packet[i]=b;}deselectRadio();
  return spiGood;
}
void clearWave(){items=segmentStart=segmentUs=totalUs=nBursts=0;halfPending=badWave=false;lastLevel=0;}
bool addPulse(uint8_t level,uint32_t us){
  if(badWave||level>1||us==0||us>MAX_US||totalUs>MAX_US-us){badWave=true;return false;}
  uint32_t halves=(us+32766)/32767;
  uint32_t available=(MAX_ITEMS-items)*2+(halfPending?1:0);
  if(halves>available){badWave=true;return false;}
  totalUs+=us;segmentUs+=us;lastLevel=level;
  while(us){uint32_t part=min(us,32767UL);us-=part;
    if(halfPending){wave[items-1].duration1=part;wave[items-1].level1=level;halfPending=false;}
    else{wave[items].val=0;wave[items].duration0=part;wave[items].level0=level;items++;halfPending=true;}
  }return true;
}
bool endBurst(uint32_t gap){
  if(badWave||items==segmentStart||nBursts>=MAX_BURSTS||gap>1000000){badWave=true;return false;}
  if(halfPending&&!addPulse(lastLevel,1))return false;
  if(totalUs>MAX_US-gap){badWave=true;return false;}
  bursts[nBursts++]={segmentStart,items-segmentStart,segmentUs,gap};
  totalUs+=gap;segmentStart=items;segmentUs=0;return true;
}
void setFrequency(uint32_t hz){uint32_t f=((uint64_t)hz*65536+13000000)/26000000;writeReg(0x0d,f>>16);writeReg(0x0e,f>>8);writeReg(0x0f,f);}
void configure(){
  spiGood=true;idle();strobe(0x30);delay(5);
  writeReg(0x00,0x2e);writeReg(0x01,0x2e);writeReg(0x02,0x0d);
  writeReg(0x08,0x32); // async serial; no packet engine
  writeReg(0x0b,0x06);writeReg(0x0c,0x00);setFrequency(433920000);
  writeReg(0x10,0x8a);writeReg(0x11,0x93); // ~40 kbit/s, ~203 kHz RX BW
  writeReg(0x12,0x00);writeReg(0x15,0x35); // 2-FSK, deviation ~20.63 kHz
  writeReg(0x17,0x00);writeReg(0x18,0x08); // manual calibration, no CCA
  writeReg(0x21,0x56);writeReg(0x22,0x10); // FSK single PA entry
  writeReg(0x3e,0x60); // nominal 0 dBm at 433 MHz, not maximum power
  idle();clearWave();
}
bool sendWave(){
  if(badWave||!spiGood||!rmtGood||!nBursts||segmentStart!=items)return false;
  if(readReg(0x30)!=0||readReg(0x31)==0||readReg(0x31)==0xff)return false;
  if(!idle())return false;
  writeReg(0x02,0x0d);writeReg(0x08,0x32);writeReg(0x12,0x00);writeReg(0x17,0x00);
  strobe(0x33);if(!state(1,20000))return false;
  for(uint32_t i=0;i<nBursts;i++){
    strobe(0x35);
    if(!state(0x13,10000)){idle();return false;}
    bool ok=rmtWrite(DATA_PIN,wave+bursts[i].start,bursts[i].count,bursts[i].duration/1000+100);
    idle();
    if(!ok)return false;
    uint32_t gap=bursts[i].gap;
    if(gap>=1000)delay(gap/1000);
    if(gap%1000)delayMicroseconds(gap%1000);
  }
  return receiveMode();
}

bool begin(uint32_t frequency) {
  pinMode(CS_PIN,OUTPUT);digitalWrite(CS_PIN,HIGH);
  SPI.begin(SCK_PIN,MISO_PIN,MOSI_PIN,CS_PIN);
  pinMode(DATA_PIN,OUTPUT);digitalWrite(DATA_PIN,LOW);
  configure();setFrequency(frequency);
  strobe(0x33);if(!state(1,20000))return false;
  rmtGood=rmtInit(DATA_PIN,RMT_TX_MODE,RMT_MEM_NUM_BLOCKS_2,1000000);
  if(rmtGood)rmtSetEOT(DATA_PIN,0);
  return spiGood && rmtGood && readReg(0x30)==0 && readReg(0x31)==0x14;
}
bool hexBits(const char* text,uint16_t bits) {
  for(uint16_t i=0;i<bits;i++) {
    char c=text[i/4];unsigned n=c<='9'?c-'0':c-'a'+10;
    if(!addPulse((n>>(3-i%4))&1,25))return false;
  }
  return true;
}
bool build(const Envelope* frames,size_t n,uint32_t address,uint16_t counter,uint8_t overrideAction=0) {
  clearWave();
  for(size_t i=0;i<n;i++) {
    uint8_t packet[21];protocol::encode(address,counter+i/3,overrideAction?overrideAction:frames[i].action,packet);
    if(!hexBits(frames[i].before,frames[i].beforeBits))return false;
    for(auto b:packet)for(int bit=7;bit>=0;bit--)if(!addPulse((b>>bit)&1,25))return false;
    if(!hexBits(frames[i].after,frames[i].afterBits))return false;
    if(!endBurst(i+1<n?frames[i].gap:0))return false;
  }
  return true;
}
} // namespace radio
