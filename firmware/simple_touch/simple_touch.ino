#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <ArduinoJson.h>
#include <Update.h>
#include <ImprovWiFiLibrary.h>
#include <esp_mac.h>
#include <mbedtls/sha256.h>
#include "radio.h"
#include "motion.h"
#include "web_ui.h"

constexpr char VERSION[]="1.0.0";
constexpr unsigned MAX_REMOTES=32;
struct Remote {
  uint32_t address=0,next=0,ceiling=0;
  String name,last="unknown";
  bool paired=false,pairSent=false;
  uint32_t sentAt=0;
  uint16_t travelSeconds=60;
  motion::Tracker motion;
  uint32_t physical[8]={};
  uint16_t physicalGroups[8]={};
  String source="unknown";
};
Remote remotes[MAX_REMOTES];
Preferences prefs;
WebServer server(80);
String deviceId,hostname,apiKey,apPassword,bootId;
bool radioReady=false,apActive=false,otaAllowed=false;
bool otaFinished=false;
String otaError,otaExpectedHash;
size_t otaBytes=0,otaExpectedSize=0;
mbedtls_sha256_context otaHash;
uint32_t apConnectedAt=0,rebootAt=0,frequency=433925000;
uint32_t lastWifiAttempt=0;
volatile uint8_t lastWifiDisconnect=0;
uint32_t pairAddress=0,pairDeadline=0;
String pairTicket;
uint32_t learnAddress=0,learnDeadline=0,learnCandidate=0,rxPackets=0;
uint16_t learnGroups=0;
struct Seen {uint32_t address=0;uint16_t counter=0;uint32_t at=0;};
Seen seen[16];unsigned seenIndex=0;
struct RadioPacket {uint8_t bytes[21];uint32_t at;};
QueueHandle_t radioQueue=nullptr;
uint32_t rxInvalid=0,rxDuplicates=0,rxMatched=0,lastRxAt=0,maxDispatchMs=0;
uint32_t rxQueueDrops=0;
struct RadioTrace {protocol::Received packet{};uint32_t at=0;};
RadioTrace rxTrace[32];unsigned rxTraceIndex=0;
void listenRadio();
// Only this task drains the FIFO. HTTP, OTA and slow clients cannot block it.
// All SPI users take the same mutex; shade state remains owned by loop().
void receiveTask(void*){
  for(;;){
    {radio::Lock lock;
      for(int i=0;i<8;i++){
        RadioPacket packet{};if(!radio::readPacket(packet.bytes))break;
        packet.at=millis();
        if(xQueueSend(radioQueue,&packet,0)!=pdTRUE)rxQueueDrops++;
      }
    }
    vTaskDelay(1);
  }
}
void serialCommand(const String &line);
class ConsoleStream : public Stream {
  String line;
 public:
  int available() override{return Serial.available();}
  int peek() override{return Serial.peek();}
  void flush() override{Serial.flush();}
  size_t write(uint8_t b) override{return Serial.write(b);}
  int read() override{
    int c=Serial.read();
    if(c=='\n'){serialCommand(line);line="";}
    else if(c>=32&&c<127&&line.length()<100)line+=char(c);
    else if(c!='\r')line="";
    return c;
  }
};
ConsoleStream console;
ImprovWiFi improv(&console);

String hexId(uint32_t n){char s[9];snprintf(s,sizeof(s),"%08lx",(unsigned long)n);return s;}
String randomSecret(){String s;for(int i=0;i<4;i++)s+=hexId(esp_random());return s;}
Remote* findRemote(uint32_t id){for(auto &r:remotes)if(r.address==id)return &r;return nullptr;}
bool parseId(String value,uint32_t &id){
  if(value.length()!=8)return false;
  for(char c:value)if(!isxdigit(c))return false;
  id=strtoul(value.c_str(),nullptr,16);return id!=0;
}
void reply(JsonDocument &doc,int status=200){String s;serializeJson(doc,s);server.sendHeader("Cache-Control","no-store");server.send(status,"application/json",s);}
void error(int status,const char* message){JsonDocument d;d["error"]=message;reply(d,status);}
bool auth(){
  if(server.header("Authorization")!="Bearer "+apiKey){error(401,"Invalid bridge key");return false;}
  return true;
}
bool readBody(JsonDocument &doc){
  if(server.arg("plain").length()>16384){error(413,"Request too large");return false;}
  if(deserializeJson(doc,server.arg("plain"))){error(400,"Invalid JSON");return false;}return true;
}
bool saveRemotes(){
  JsonDocument d;JsonArray list=d["remotes"].to<JsonArray>();
  for(auto &r:remotes)if(r.address){JsonObject o=list.add<JsonObject>();o["id"]=hexId(r.address);o["name"]=r.name;o["paired"]=r.paired;o["pair_sent"]=r.pairSent;o["travel_time_s"]=r.travelSeconds;JsonArray links=o["physical"].to<JsonArray>();for(int i=0;i<8;i++)if(r.physical[i]){JsonObject p=links.add<JsonObject>();p["id"]=hexId(r.physical[i]);p["groups"]=r.physicalGroups[i];}}
  String s;serializeJson(d,s);return prefs.putString("remotes",s)==s.length();
}
void remoteJson(JsonObject o,Remote &r){
  r.motion.tick(millis());
  o["id"]=hexId(r.address);o["name"]=r.name;o["paired"]=r.paired;o["pair_sent"]=r.pairSent;o["travel_time_s"]=r.travelSeconds;
  o["last_command"]=r.last;o["position"]=nullptr;o["next_counter"]=r.next;
  o["state_source"]=r.source;o["assumed_state"]=r.motion.label();
  JsonArray links=o["physical"].to<JsonArray>();for(int i=0;i<8;i++)if(r.physical[i]){JsonObject p=links.add<JsonObject>();p["id"]=hexId(r.physical[i]);p["groups"]=r.physicalGroups[i];}
}
void stateReply(){
  listenRadio();
  JsonDocument d;d["device_id"]=deviceId;d["name"]="Simple Touch Bridge";d["version"]=VERSION;d["api_version"]=1;
  d["radio_ready"]=radioReady;d["frequency_hz"]=frequency;d["uptime_s"]=millis()/1000;
  d["ip"]=WiFi.status()==WL_CONNECTED?WiFi.localIP().toString():WiFi.softAPIP().toString();
  d["wifi_connected"]=WiFi.status()==WL_CONNECTED;d["max_remotes"]=MAX_REMOTES;
  d["received_packets"]=rxPackets;d["favorite_supported"]=true;
  d["received_commands"]=rxMatched;d["invalid_packets"]=rxInvalid;
  d["last_received_ms"]=lastRxAt;d["max_receive_dispatch_ms"]=maxDispatchMs;
  {radio::Lock lock;d["rx_overflows"]=radio::overflows;d["rx_queue_drops"]=rxQueueDrops;}
  JsonArray list=d["remotes"].to<JsonArray>();for(auto &r:remotes)if(r.address)remoteJson(list.add<JsonObject>(),r);
  reply(d);
}
bool reserveCounters(Remote &r,unsigned count,uint16_t &first){
  // Reserve ahead in NVS, before RF. A reboot skips unused counters instead of reusing them.
  if(r.next+count>65535)return false;
  if(r.next+count>r.ceiling){
    uint32_t ceiling=min(uint32_t(65535),r.next+32);
    String k="c"+hexId(r.address);
    if(prefs.putUInt(k.c_str(),ceiling)!=sizeof(uint32_t))return false;
    r.ceiling=ceiling;
  }
  first=r.next;r.next+=count;return true;
}
void recordCommand(Remote &r,const String &action,const char* source,uint32_t at){
  if(action=="up")r.motion.command(motion::Command::Up,at,r.travelSeconds*1000u);
  else if(action=="down")r.motion.command(motion::Command::Down,at,r.travelSeconds*1000u);
  else if(action=="stop")r.motion.command(motion::Command::Stop,at,r.travelSeconds*1000u);
  else if(action=="favorite")r.motion.command(motion::Command::Favorite,at,r.travelSeconds*1000u);
  r.last=action;r.sentAt=at;r.source=source;
}
bool transmit(Remote &r,const String &action){
  // Finish processing older received commands before recording this transmission.
  radio::Lock lock;
  listenRadio();
  const Envelope* frames;size_t count;unsigned counters=1;
  if(action=="up"){frames=up_envelopes;count=6;counters=2;}
  else if(action=="down"){frames=down_envelopes;count=6;counters=2;}
  else if(action=="stop"){frames=stop_envelopes;count=3;}
  else if(action=="p2"){frames=p2_envelopes;count=3;}
  else if(action=="favorite"){frames=p2_envelopes;count=3;}
  else return false;
  uint16_t counter;
  if(!radioReady||!reserveCounters(r,counters,counter))return false;
  uint32_t started=millis();
  if(!radio::build(frames,count,r.address,counter,action=="favorite"?0x13:0)||!radio::sendWave()){radio::receiveMode();return false;}
  recordCommand(r,action,"bridge",started);return true;
}
void processRadioPacket(const RadioPacket &raw){
  protocol::Received p;if(!protocol::decode(raw.bytes,p)){rxInvalid++;return;}rxPackets++;
  lastRxAt=raw.at;maxDispatchMs=max(maxDispatchMs,uint32_t(millis()-raw.at));
  rxTrace[rxTraceIndex++%32]={p,raw.at};
  // Repeated packets of a held STOP must not replace its later favorite action.
  for(const auto &s:seen)if(s.address==p.address&&s.counter==p.counter&&raw.at-s.at<30000){rxDuplicates++;return;}
  seen[seenIndex++%16]={p.address,p.counter,raw.at};
  if(findRemote(p.address))return; // Ignore our own virtual identities.
  if(learnAddress&&int32_t(millis()-learnDeadline)<0&&p.action==3&&!learnCandidate){learnCandidate=p.address;learnGroups=p.groups;}
  String action=p.action==1?"up":p.action==2?"down":p.action==3?"stop":p.action==0x13?"favorite":"";
  if(action.isEmpty())return;
  for(auto &r:remotes)if(r.address)for(int i=0;i<8;i++)if(r.physical[i]==p.address&&(r.physicalGroups[i]&p.groups)){
      recordCommand(r,action,"physical_remote",raw.at);rxMatched++;break;
  }
}
void listenRadio(){
  if(!radioReady||!radioQueue)return;
  RadioPacket packet;
  for(int i=0;i<128&&xQueueReceive(radioQueue,&packet,0)==pdTRUE;i++)processRadioPacket(packet);
}
void startAP(){
  WiFi.mode(WIFI_AP_STA);WiFi.softAP(("SimpleTouch-"+deviceId.substring(deviceId.length()-6)).c_str(),apPassword.c_str());
  apActive=true;apConnectedAt=0;
  Serial.printf("SETUP_AP SimpleTouch-%s password=%s URL=http://192.168.4.1\n",deviceId.substring(deviceId.length()-6).c_str(),apPassword.c_str());
}
void routes(){
  const char* headers[]={"Authorization","X-Firmware-SHA256","X-Firmware-Size"};server.collectHeaders(headers,3);
  server.on("/",HTTP_GET,[]{server.sendHeader("X-Content-Type-Options","nosniff");server.send_P(200,"text/html",WEB_UI);});
  server.on("/api/status",HTTP_GET,[]{JsonDocument d;d["device_id"]=deviceId;d["version"]=VERSION;d["api_version"]=1;d["boot_id"]=bootId;reply(d);});
  server.on("/api/setup-key",HTTP_GET,[]{
    IPAddress ip=server.client().remoteIP();
    if(!apActive||ip[0]!=192||ip[1]!=168||ip[2]!=4){error(403,"Join the bridge setup Wi-Fi first");return;}
    JsonDocument d;d["key"]=apiKey;reply(d);
  });
  server.on("/api/state",HTTP_GET,[]{if(auth())stateReply();});
  server.on("/api/diagnostics",HTTP_GET,[]{
    if(!auth())return;listenRadio();JsonDocument d;
    d["received_packets"]=rxPackets;d["invalid_packets"]=rxInvalid;d["duplicates"]=rxDuplicates;
    d["matched_commands"]=rxMatched;d["max_dispatch_ms"]=maxDispatchMs;
    {radio::Lock lock;d["overflows"]=radio::overflows;d["queue_drops"]=rxQueueDrops;
      d["unstable_reads"]=radio::unstableReads;d["radio_state"]=radio::readReg(0x35)&31;}
    auto packets=d["recent_packets"].to<JsonArray>();unsigned n=min(rxTraceIndex,32u);
    for(unsigned i=0;i<n;i++){const auto &t=rxTrace[(rxTraceIndex-n+i)%32];auto p=packets.add<JsonObject>();
      p["at_ms"]=t.at;p["address"]=hexId(t.packet.address);p["counter"]=t.packet.counter;
      p["action"]=t.packet.action;p["groups"]=t.packet.groups;}
    reply(d);
  });
  server.on("/api/wifi",HTTP_POST,[]{
    if(!auth())return;JsonDocument d;if(!readBody(d))return;
    String ssid=d["ssid"]|"",pass=d["password"]|"";
    if(ssid.isEmpty()||ssid.length()>32||pass.length()>63){error(400,"Check Wi-Fi name and password");return;}
    if(prefs.putString("ssid",ssid)!=ssid.length()||prefs.putString("wifiPass",pass)!=pass.length()){error(500,"Could not save Wi-Fi");return;}
    WiFi.begin(ssid.c_str(),pass.c_str());JsonDocument out;out["connecting"]=true;reply(out);
  });
  server.on("/api/remotes",HTTP_POST,[]{
    if(!auth())return;JsonDocument d;if(!readBody(d))return;String name=d["name"]|"";name.trim();
    if(name.isEmpty()||name.length()>48){error(400,"Name must be 1 to 48 characters");return;}
    Remote* slot=nullptr;for(auto &r:remotes)if(!r.address){slot=&r;break;}
    if(!slot){error(409,"This bridge already has 32 remotes");return;}
    uint32_t id=0;
    do{id=esp_random()&0xffffff00;}while(!id||findRemote(id)||prefs.isKey(("c"+hexId(id)).c_str()));
    // Import is for an existing paired identity, without P2. Require an explicit counter.
    if(d["id"].is<String>()){
      if(!parseId(d["id"].as<String>(),id)||findRemote(id)||prefs.isKey(("c"+hexId(id)).c_str())||!d["next_counter"].is<uint32_t>()||d["next_counter"].as<uint32_t>()>=65535){error(400,"Invalid or previously used import identity");return;}
    }
    if(d.containsKey("next_counter")&&(!d["next_counter"].is<uint32_t>()||d["next_counter"].as<uint32_t>()>=65535)){error(400,"Invalid counter");return;}
    if(d.containsKey("travel_time_s")&&(!d["travel_time_s"].is<unsigned>()||d["travel_time_s"].as<unsigned>()<5||d["travel_time_s"].as<unsigned>()>300)){error(400,"Travel time must be 5 to 300 seconds");return;}
    slot->travelSeconds=d["travel_time_s"]|uint16_t(60);
    slot->address=id;slot->name=name;slot->next=d["next_counter"]|uint32_t(1);slot->paired=d["paired"]|false;
    unsigned linked=0;for(JsonObject p:d["physical"].as<JsonArray>()){if(linked>=8)break;uint32_t physicalId;if(parseId(p["id"]|"",physicalId)){slot->physical[linked]=physicalId;slot->physicalGroups[linked]=p["groups"]|uint16_t(1);linked++;}}
    if(prefs.putUInt(("c"+hexId(id)).c_str(),slot->next)!=4||!saveRemotes()){*slot=Remote();error(500,"Could not save remote");return;}
    JsonDocument out;remoteJson(out.to<JsonObject>(),*slot);reply(out,201);
  });
  server.on("/api/radio",HTTP_POST,[]{
    if(!auth())return;JsonDocument d;if(!readBody(d))return;uint32_t hz=d["frequency_hz"]|uint32_t(0);
    if(hz<433000000||hz>434790000){error(400,"Frequency outside supported range");return;}
    if(prefs.putUInt("frequency",hz)!=4){error(500,"Could not save radio setting");return;}
    frequency=hz;{radio::Lock lock;radio::idle();radio::setFrequency(hz);radio::strobe(0x33);radio::state(1,20000);radio::receiveMode();}stateReply();
  });
  server.on("/api/backup",HTTP_GET,[]{
    if(!auth())return;JsonDocument d;d["format"]=1;d["frequency_hz"]=frequency;
    JsonArray list=d["remotes"].to<JsonArray>();
    for(auto &r:remotes)if(r.address){JsonObject o=list.add<JsonObject>();remoteJson(o,r);o["next_counter"]=max(r.ceiling,r.next);}
    server.sendHeader("Content-Disposition","attachment; filename=simple-touch-backup.json");reply(d);
  });
  server.on("/api/restart",HTTP_POST,[]{if(!auth())return;JsonDocument d;d["restarting"]=true;reply(d);rebootAt=millis()+500;});
  server.on("/api/update",HTTP_POST,[]{
    if(!auth())return;
    const bool success=otaAllowed&&otaFinished&&otaError.isEmpty()&&!Update.hasError();
    otaAllowed=false;otaFinished=false;
    if(!success){error(400,otaError.isEmpty()?"No complete firmware upload received":otaError.c_str());return;}
    JsonDocument d;d["restarting"]=true;reply(d);rebootAt=millis()+1000;
  },[]{
    HTTPUpload &u=server.upload();
    if(u.status==UPLOAD_FILE_START){
      otaAllowed=server.header("Authorization")=="Bearer "+apiKey;
      otaFinished=false;otaError="";otaBytes=0;otaExpectedSize=0;
      if(!otaAllowed)return;
      otaExpectedHash=server.header("X-Firmware-SHA256");otaExpectedHash.toLowerCase();
      String sizeText=server.header("X-Firmware-Size");
      if(!otaExpectedHash.isEmpty()){
        if(otaExpectedHash.length()!=64)otaError="Invalid firmware checksum";
        for(char c:otaExpectedHash)if(!isxdigit(c))otaError="Invalid firmware checksum";
        if(sizeText.isEmpty())otaError="Firmware size required";
      }
      if(!sizeText.isEmpty()){
        for(char c:sizeText)if(!isdigit(c))otaError="Invalid firmware size";
        if(sizeText.length()>7)otaError="Invalid firmware size";
        otaExpectedSize=sizeText.toInt();
        if(otaExpectedSize<65536||otaExpectedSize>3342336)otaError="Firmware does not fit this board";
      }
      if(!otaError.isEmpty())return;
      mbedtls_sha256_init(&otaHash);
      if(mbedtls_sha256_starts(&otaHash,0)!=0)otaError="Could not initialize firmware verification";
      if(otaError.isEmpty()&&!Update.begin(otaExpectedSize?otaExpectedSize:UPDATE_SIZE_UNKNOWN))otaError="Could not start firmware update";
    }else if(otaAllowed&&u.status==UPLOAD_FILE_WRITE&&otaError.isEmpty()){
      otaBytes+=u.currentSize;
      if((otaExpectedSize&&otaBytes>otaExpectedSize)||mbedtls_sha256_update(&otaHash,u.buf,u.currentSize)!=0||Update.write(u.buf,u.currentSize)!=u.currentSize){
        otaError="Firmware upload failed";Update.abort();
      }
    }else if(otaAllowed&&u.status==UPLOAD_FILE_END){
      if(otaError.isEmpty()){
        uint8_t digest[32];char hex[65];
        if(mbedtls_sha256_finish(&otaHash,digest)!=0)otaError="Firmware verification failed";
        else {
          for(unsigned i=0;i<32;i++)snprintf(hex+i*2,3,"%02x",digest[i]);
          if((otaExpectedSize&&otaBytes!=otaExpectedSize)||(!otaExpectedHash.isEmpty()&&otaExpectedHash!=hex))otaError="Firmware checksum or size did not match";
        }
        if(!otaError.isEmpty())Update.abort();
        else if(!Update.end(true))otaError="Firmware image was not accepted";
        else otaFinished=true;
      }
      mbedtls_sha256_free(&otaHash);
    }else if(u.status==UPLOAD_FILE_ABORTED&&otaAllowed){
      Update.abort();mbedtls_sha256_free(&otaHash);otaAllowed=false;otaFinished=false;otaError="Upload interrupted";
    }
  });
  server.onNotFound([]{
    if(!auth())return;
    String path=server.uri();String prefix="/api/remotes/";
    if(!path.startsWith(prefix)){error(404,"Not found");return;}
    String rest=path.substring(prefix.length());int slash=rest.indexOf('/');String idtext=slash<0?rest:rest.substring(0,slash);uint32_t id;
    if(!parseId(idtext,id)){error(404,"Remote not found");return;}Remote* r=findRemote(id);if(!r){error(404,"Remote not found");return;}
    String operation=slash<0?"":rest.substring(slash+1);
    if(server.method()==HTTP_DELETE&&operation.isEmpty()){
      if(pairAddress==id){pairTicket="";pairAddress=0;}
      Remote old=*r;*r=Remote();if(!saveRemotes()){*r=old;error(500,"Could not save deletion");return;}
      // Keep the counter tombstone so deleted identities cannot be accidentally reused.
      JsonDocument d;d["deleted"]=true;reply(d);return;
    }
    if(server.method()!=HTTP_POST){error(405,"Method not allowed");return;}
    JsonDocument d;if(!readBody(d))return;
    if(operation=="travel"){
      if(!d["travel_time_s"].is<unsigned>()||d["travel_time_s"].as<unsigned>()<5||d["travel_time_s"].as<unsigned>()>300){error(400,"Travel time must be 5 to 300 seconds");return;}
      uint16_t previous=r->travelSeconds;r->travelSeconds=d["travel_time_s"].as<uint16_t>();
      if(!saveRemotes()){r->travelSeconds=previous;error(500,"Could not save travel time");return;}
      stateReply();return;
    }
    if(operation=="learn/start"){
      learnAddress=id;learnDeadline=millis()+60000;learnCandidate=0;learnGroups=0;
      JsonDocument o;o["listening"]=true;reply(o);return;
    }
    if(operation=="learn/remove"){
      uint32_t address;if(!parseId(d["id"]|"",address)){error(400,"Invalid physical remote");return;}
      Remote previous=*r;
      for(int i=0;i<8;i++)if(r->physical[i]==address){r->physical[i]=0;r->physicalGroups[i]=0;}
      if(!saveRemotes()){*r=previous;error(500,"Could not save links");return;}stateReply();return;
    }
    if(operation=="learn/status"){
      JsonDocument o;o["listening"]=learnAddress==id&&int32_t(millis()-learnDeadline)<0;
      if(learnAddress==id&&learnCandidate){o["candidate"]=hexId(learnCandidate);o["groups"]=learnGroups;}
      reply(o);return;
    }
    if(operation=="learn/confirm"){
      if(learnAddress!=id||!learnCandidate||int32_t(millis()-learnDeadline)>=0){error(409,"Remote link session expired");return;}
      int slot=-1;for(int i=0;i<8;i++)if(r->physical[i]==learnCandidate&&r->physicalGroups[i]==learnGroups){learnAddress=0;stateReply();return;}
      for(int i=0;i<8;i++)if(!r->physical[i]){slot=i;break;}
      if(slot<0){error(409,"Maximum of eight physical remote links reached");return;}
      r->physical[slot]=learnCandidate;r->physicalGroups[slot]=learnGroups;
      if(!saveRemotes()){r->physical[slot]=0;r->physicalGroups[slot]=0;error(500,"Could not save link");return;}
      learnAddress=0;stateReply();return;
    }
    if(operation=="rename"){
      String name=d["name"]|"";name.trim();if(name.isEmpty()||name.length()>48){error(400,"Invalid name");return;}
      String old=r->name;r->name=name;if(!saveRemotes()){r->name=old;error(500,"Could not save name");return;}stateReply();return;
    }
    if(operation=="pair/arm"){
      if(r->paired||r->pairSent){error(409,"Already paired or awaiting confirmation; do not repeat P2");return;}
      pairAddress=id;pairTicket=randomSecret();pairDeadline=millis()+120000;
      JsonDocument o;o["ticket"]=pairTicket;o["expires_in"]=120;reply(o);return;
    }
    if(operation=="pair/send"){
      if(pairAddress!=id||pairTicket.isEmpty()||int32_t(millis()-pairDeadline)>=0||d["ticket"].as<String>()!=pairTicket){error(409,"Pairing session expired; start again");return;}
      pairTicket="";pairAddress=0;
      // Persist pending state before transmission so a timeout/reboot cannot offer a blind retry.
      r->pairSent=true;if(!saveRemotes()){r->pairSent=false;error(500,"Could not save pairing state");return;}
      if(!transmit(*r,"p2")){error(503,"Radio failed; check the shade before trying again");return;}
      r->pairSent=true;JsonDocument o;o["sent"]=true;reply(o);return;
    }
    if(operation=="pair/confirm"){
      if(!r->pairSent||!(d["two_jogs"]|false)){error(409,"Confirm two jogs first");return;}
      r->paired=true;r->pairSent=false;if(!saveRemotes()){r->paired=false;r->pairSent=true;error(500,"Could not save paired state");return;}stateReply();return;
    }
    if(operation=="command"){
      String action=d["action"]|"";
      if(action!="up"&&action!="down"&&action!="stop"&&action!="favorite"){error(400,"Unsupported command");return;}
      if(!r->paired&&!r->pairSent){error(409,"Pair this remote first");return;}
      uint32_t start=millis();
      if(!transmit(*r,action)){error(503,"Transmission failed or counter exhausted");return;}
      JsonDocument o;o["sent"]=true;o["duration_ms"]=millis()-start;o["id"]=hexId(id);o["action"]=action;remoteJson(o["remote"].to<JsonObject>(),*r);reply(o);return;
    }
    error(404,"Not found");
  });
}
void setup(){
  Serial.begin(115200);bootId=randomSecret();prefs.begin("simpletouch",false);
  uint8_t mac[6];esp_read_mac(mac,ESP_MAC_WIFI_STA);char identity[13];
  snprintf(identity,sizeof(identity),"%02x%02x%02x%02x%02x%02x",mac[0],mac[1],mac[2],mac[3],mac[4],mac[5]);deviceId=identity;
  hostname="simpletouch-"+deviceId.substring(deviceId.length()-6);
  apiKey=prefs.getString("apiKey","");if(apiKey.isEmpty()){apiKey=randomSecret();prefs.putString("apiKey",apiKey);}
  apPassword=prefs.getString("apPass","");if(apPassword.isEmpty()){apPassword=randomSecret().substring(0,12);prefs.putString("apPass",apPassword);}
  frequency=prefs.getUInt("frequency",433925000);
  JsonDocument d;deserializeJson(d,prefs.getString("remotes","{}"));unsigned i=0;
  for(JsonObject o:d["remotes"].as<JsonArray>()){
    if(i>=MAX_REMOTES)break;Remote &r=remotes[i];if(!parseId(o["id"]|"",r.address))continue;
    r.travelSeconds=o["travel_time_s"]|uint16_t(60);if(r.travelSeconds<5||r.travelSeconds>300)r.travelSeconds=60;
    r.name=o["name"]|"Shade";r.paired=o["paired"]|false;r.pairSent=o["pair_sent"]|false;r.next=r.ceiling=prefs.getUInt(("c"+hexId(r.address)).c_str(),65535);i++;
    unsigned j=0;for(JsonObject p:o["physical"].as<JsonArray>()){if(j>=8)break;uint32_t id;if(parseId(p["id"]|"",id)){r.physical[j]=id;r.physicalGroups[j]=p["groups"]|uint16_t(1);j++;}}
  }
  WiFi.onEvent([](WiFiEvent_t event,WiFiEventInfo_t info){if(event==ARDUINO_EVENT_WIFI_STA_DISCONNECTED)lastWifiDisconnect=info.wifi_sta_disconnected.reason;});
  WiFi.setHostname(hostname.c_str());WiFi.setAutoReconnect(true);
  String ssid=prefs.getString("ssid","");if(ssid.isEmpty())startAP();else{WiFi.mode(WIFI_STA);WiFi.begin(ssid.c_str(),prefs.getString("wifiPass","").c_str());}
  WiFi.setSleep(false);
  lastWifiAttempt=millis();
  radioReady=radio::begin(frequency);
  if(radioReady)radioReady=radio::receiveMode();
  if(radioReady){
    radioQueue=xQueueCreate(128,sizeof(RadioPacket));
    radioReady=radioQueue&&xTaskCreate(receiveTask,"radio-rx",4096,nullptr,2,nullptr)==pdPASS;
  }
  routes();server.begin();
  String deviceUrl="http://{LOCAL_IPV4}/#key="+apiKey;
  improv.setDeviceInfo(ImprovTypes::ChipFamily::CF_ESP32_S3,"Simple Touch",VERSION,"Simple Touch Bridge",deviceUrl.c_str());
  improv.onImprovConnected([](const char* ssid,const char* pass){prefs.putString("ssid",ssid);prefs.putString("wifiPass",pass);});
  Serial.printf("SIMPLE_TOUCH %s radio=%d host=%s.local\n",VERSION,radioReady,hostname.c_str());
}
void loop(){
  listenRadio();
  server.handleClient();
  if(WiFi.status()==WL_CONNECTED)lastWifiAttempt=millis();
  else if(millis()-lastWifiAttempt>=20000){
    lastWifiAttempt=millis();String ssid=prefs.getString("ssid","");
    if(!ssid.isEmpty()){String password=prefs.getString("wifiPass","");WiFi.disconnect(false,false);WiFi.begin(ssid.c_str(),password.c_str());}
  }
  static bool mdns=false;
  if(WiFi.status()==WL_CONNECTED&&!mdns){mdns=MDNS.begin(hostname.c_str());if(mdns){MDNS.addService("simpletouch","tcp",80);MDNS.addServiceTxt("simpletouch","tcp","id",deviceId);}}
  if(apActive&&WiFi.status()==WL_CONNECTED){if(!apConnectedAt)apConnectedAt=millis();if(millis()-apConnectedAt>120000){WiFi.softAPdisconnect(true);apActive=false;}}
  while(Serial.available())improv.handleSerial();
  if(rebootAt&&int32_t(millis()-rebootAt)>=0)ESP.restart();
  delay(1);
}
void serialCommand(const String &line){
  if(line=="SETUP")startAP();
  if(line=="INFO")Serial.printf("IP=%s HOST=%s.local KEY=%s RADIO=%d\n",WiFi.localIP().toString().c_str(),hostname.c_str(),apiKey.c_str(),radioReady);
  if(line=="SELFTEST"){
    uint8_t p[21];protocol::encode(0x12345600,23,3,p);Serial.print("PACKET=");for(auto b:p)Serial.printf("%02x",b);Serial.println();
    protocol::Received decoded{};bool ok=protocol::decode(p,decoded)&&decoded.address==0x12345600&&decoded.counter==23&&decoded.action==3;
    p[5]^=1;ok=ok&&!protocol::decode(p,decoded);Serial.printf("DECODE_TEST=%s\n",ok?"PASS":"FAIL");
  }
  if(line=="RXSTATUS"){radio::Lock lock;Serial.printf("RADIO=%d RX=%lu INVALID=%lu MATCHED=%lu OVERFLOW=%lu DROPS=%lu STATE=%02x FIFO=%02x\n",radioReady,(unsigned long)rxPackets,(unsigned long)rxInvalid,(unsigned long)rxMatched,(unsigned long)radio::overflows,(unsigned long)rxQueueDrops,radio::readReg(0x35),radio::readReg(0x3b));}
  if(line=="NETSTATUS")Serial.printf("WIFI=%d MODE=%d IP=%s GATEWAY=%s RSSI=%d UPTIME=%lu HEAP=%lu REASON=%u\n",WiFi.status(),WiFi.getMode(),WiFi.localIP().toString().c_str(),WiFi.gatewayIP().toString().c_str(),WiFi.RSSI(),(unsigned long)(millis()/1000),(unsigned long)ESP.getFreeHeap(),lastWifiDisconnect);
}
