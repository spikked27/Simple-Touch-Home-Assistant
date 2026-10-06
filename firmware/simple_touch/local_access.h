#pragma once
#include <cstdint>
#include <string>
namespace local_access {
inline bool subnet(uint32_t peer,uint32_t local,uint32_t mask){
  return local!=0 && mask!=0 && peer!=0 && (peer&mask)==(local&mask);
}
inline bool allowed(bool nearby,std::string host,const std::string &ip,
                    const std::string &ap,const std::string &hostname,
                    const std::string &origin,const std::string &ui,bool forwarded){
  if(!nearby || ui!="1" || forwarded)return false;
  const std::string authority=host;
  if(host.size()>3 && host.substr(host.size()-3)==":80")host.resize(host.size()-3);
  if(host!=ip && host!=ap && host!=hostname && host!=hostname+".local")return false;
  return origin.empty() || origin=="http://"+authority;
}
}
